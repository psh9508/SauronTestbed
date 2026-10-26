import os
from pathlib import Path

from sauron_python import sauron_sdk

from sauron_reporter.reporter import PROJECT_ROOT, SauronReporter


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


def reporter_from_env(require_key: bool = True) -> SauronReporter:
    load_env()
    key = os.environ.get("SAURON_REPOSITORY_KEY", "")
    if require_key and not key:
        raise SystemExit(
            "SAURON_REPOSITORY_KEY가 비어 있습니다. register_repo.py로 저장소를 등록하고 .env에 public_key를 넣으세요."
        )
    return SauronReporter(
        base_url=os.environ.get("SAURON_BASE_URL", "http://127.0.0.1:8002"),
        repository_key=key,
        repository_url=os.environ.get("SAURON_REPOSITORY_URL") or None,
    )


def init_sdk_from_env() -> None:
    """같은 .env 설정으로 sauron-python SDK를 초기화한다."""
    load_env()
    key = os.environ.get("SAURON_REPOSITORY_KEY", "")
    if not key:
        raise SystemExit(
            "SAURON_REPOSITORY_KEY가 비어 있습니다. register_repo.py로 저장소를 등록하고 .env에 public_key를 넣으세요."
        )
    sauron_sdk.init(
        repository_key=key,
        endpoint=os.environ.get("SAURON_BASE_URL", "http://127.0.0.1:8002").rstrip("/") + "/analyze",
        repository_url=os.environ.get("SAURON_REPOSITORY_URL") or None,
    )
