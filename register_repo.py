"""Sauron에 코드 저장소를 등록하고 발급된 public_key(repository_key)를 출력한다.

  # GitHub App
  uv run python register_repo.py github --repo owner/sauron-testbed \
      --app-id 123 --installation-id 456 --pem path/to/app.pem

  # GitLab PAT
  uv run python register_repo.py gitlab --base-url https://gitlab.example.com --token glpat-xxx

  # 등록된 저장소 목록
  uv run python register_repo.py list
"""
import argparse
import json
import sys
from pathlib import Path

from sauron_reporter.config import reporter_from_env


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    gh = sub.add_parser("github")
    gh.add_argument("--repo", required=True, help="owner/repo")
    gh.add_argument("--app-id", required=True)
    gh.add_argument("--installation-id", required=True)
    gh.add_argument("--pem", required=True, type=Path, help="GitHub App private key 파일")

    gl = sub.add_parser("gitlab")
    gl.add_argument("--base-url", required=True)
    gl.add_argument("--token", required=True, help="GitLab Personal Access Token")

    sub.add_parser("list")
    args = parser.parse_args()

    client = reporter_from_env(require_key=False)

    if args.cmd == "list":
        status, body = client.request("GET", "/source_control/repositories")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0 if status == 200 else 1

    if args.cmd == "github":
        payload = {
            "provider": "github",
            "repo_info": {
                "repository_name": args.repo,
                "auth_config": {
                    "app_id": args.app_id,
                    "installation_id": args.installation_id,
                    "pem": args.pem.read_text(),
                },
            },
        }
    else:
        payload = {
            "provider": "gitlab",
            "repo_info": {
                "base_url": args.base_url,
                "auth_config": {"access_token": args.token},
            },
        }

    status, body = client.request("POST", "/source_control/repositories", payload)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    if status != 201:
        return 1
    print(f"\n.env에 추가하세요:\nSAURON_REPOSITORY_KEY={body['data']['public_key']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
