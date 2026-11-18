import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

import sentry_sdk

from sauron_reporter.reporter import PROJECT_ROOT, SauronClient


def load_env(path: Path = PROJECT_ROOT / ".env") -> None:
    """python-dotenv 없이 KEY=VALUE 형식의 .env를 읽는다. 이미 설정된 환경변수가 우선."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _base_url() -> str:
    return os.environ.get("SAURON_BASE_URL", "http://127.0.0.1:8002").rstrip("/")


def client_from_env() -> SauronClient:
    load_env()
    return SauronClient(base_url=_base_url())


def build_dsn(base_url: str, repository_key: str) -> str:
    # project id(/1)는 DSN 형식상 필요할 뿐 Sauron은 쓰지 않는다
    url = urlsplit(base_url)
    return f"{url.scheme}://{repository_key}@{url.netloc}/1"


def _print_event(event: dict) -> None:
    """--dry-run: 전송 대신 Sauron이 쓰는 필드만 출력한다."""
    summary = {
        "level": event.get("level"),
        "exception": [
            {
                "type": e.get("type"),
                "value": e.get("value"),
                "frames": [
                    f"{f.get('filename')}:{f.get('lineno')} in {f.get('function')}"
                    for f in (e.get("stacktrace") or {}).get("frames", [])
                ],
            }
            for e in (event.get("exception") or {}).get("values", [])
        ],
        "message": (event.get("logentry") or {}).get("formatted"),
        "release": event.get("release"),
        "tags": event.get("tags"),
        "breadcrumbs": [c.get("message") for c in (event.get("breadcrumbs") or {}).get("values", [])],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def init_sentry_from_env(dry_run: bool = False) -> SauronClient:
    """.env 설정으로 sentry-sdk가 Sauron에 에러를 보내도록 초기화한다.

    - SAURON_REPOSITORY_KEY: DSN의 public key
    - GIT_COMMIT_SHA: release 및 git_commit_sha 태그 → Sauron이 이 커밋 기준으로 소스를 읽는다
    - SAURON_REPOSITORY_URL: repository_url 태그 (GitLab 저장소만)
    """
    load_env()
    key = os.environ.get("SAURON_REPOSITORY_KEY", "")
    if not key and not dry_run:
        raise SystemExit(
            "SAURON_REPOSITORY_KEY가 비어 있습니다. register_repo.py로 저장소를 등록하고 .env에 public_key를 넣으세요."
        )

    def before_send(event: dict, hint: dict) -> dict | None:
        _print_event(event)
        return None

    git_commit_sha = os.environ.get("GIT_COMMIT_SHA") or None
    # breadcrumbs로 쓸 INFO 로그가 root logger에서 걸러지지 않도록 한다
    logging.getLogger().setLevel(logging.INFO)
    sentry_sdk.init(
        dsn=build_dsn(_base_url(), key or "dry-run"),
        release=git_commit_sha,
        before_send=before_send if dry_run else None,
    )
    if git_commit_sha:
        sentry_sdk.set_tag("git_commit_sha", git_commit_sha)
    repository_url = os.environ.get("SAURON_REPOSITORY_URL")
    if repository_url:
        sentry_sdk.set_tag("repository_url", repository_url)
    return SauronClient(base_url=_base_url())
