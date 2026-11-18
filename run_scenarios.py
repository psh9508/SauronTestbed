"""시나리오를 실행해 발생한 에러를 sentry-sdk로 Sauron에 보내고 분석 결과를 출력한다.

  uv run python run_scenarios.py --list
  uv run python run_scenarios.py                      # 전체 시나리오
  uv run python run_scenarios.py zero_stock bad_quantity
  uv run python run_scenarios.py --no-wait            # 전송만 하고 폴링하지 않음
  uv run python run_scenarios.py --dry-run            # 전송 없이 sentry 이벤트만 출력
"""
import argparse
import logging
import sys

import sentry_sdk

from sauron_reporter import SauronError
from sauron_reporter.config import init_sentry_from_env
from scenarios import MESSAGE_SCENARIOS, SCENARIOS


def _send_scenario(name: str) -> bool:
    """시나리오를 실행해 에러를 sentry로 보낸다. 예외가 나지 않으면 False."""
    # 시나리오마다 breadcrumbs를 새로 쌓는다
    sentry_sdk.get_isolation_scope().clear_breadcrumbs()

    if name in MESSAGE_SCENARIOS:
        logging.getLogger("shop.orders").error(MESSAGE_SCENARIOS[name])
        return True
    try:
        SCENARIOS[name]()
    except Exception:
        sentry_sdk.capture_exception()
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", help="실행할 시나리오 이름 (기본: 전체)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--no-wait", action="store_true", help="job 완료를 기다리지 않음")
    parser.add_argument("--dry-run", action="store_true", help="Sauron에 보내지 않고 sentry 이벤트만 출력")
    parser.add_argument("--timeout", type=float, default=300.0, help="job 대기 시간(초)")
    args = parser.parse_args()

    all_names = list(SCENARIOS) + list(MESSAGE_SCENARIOS)
    if args.list:
        print("\n".join(all_names))
        return 0

    names = args.names or all_names
    unknown = [n for n in names if n not in all_names]
    if unknown:
        parser.error(f"unknown scenario: {', '.join(unknown)}")

    client = init_sentry_from_env(dry_run=args.dry_run)
    release = sentry_sdk.get_client().options.get("release")
    print(f"release(git_commit_sha)={release or '(없음: default branch)'}")

    jobs: list[tuple[str, str]] = []
    failed = 0
    for name in names:
        print(f"\n===== {name} =====")

        if args.dry_run:
            if not _send_scenario(name):
                print("  예외가 발생하지 않았습니다")
                failed += 1
            sentry_sdk.flush()
            continue

        try:
            error = client.send_and_find(lambda: _send_scenario(name))
        except (SauronError, TimeoutError) as e:
            print(f"  전송 실패: {e}")
            failed += 1
            continue
        if error is None:
            print("  예외가 발생하지 않았습니다")
            failed += 1
            continue

        job_id = error["analyze_job_id"]
        if error["event_count"] > 1:
            print(f"  기존 이벤트 (event_count={error['event_count']}) job_id={job_id}")
        else:
            print(f"  queued job_id={job_id}")
        print(f"  fingerprint={error['fingerprint']}")
        jobs.append((name, job_id))

    if args.no_wait or args.dry_run:
        return 1 if failed else 0

    for name, job_id in jobs:
        print(f"\n===== result: {name} ({job_id}) =====")
        try:
            job = client.wait_for_job(job_id, timeout=args.timeout)
        except (SauronError, TimeoutError) as e:
            print(f"  {e}")
            failed += 1
            continue
        print(f"  status={job['status']} started={job['started_at']} finished={job['finished_at']}")
        if job["status"] == "failed":
            print(f"  error: {job['error_message']}")
            failed += 1
        else:
            print(job["result_content"])

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
