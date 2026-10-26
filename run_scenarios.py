"""버그 시나리오를 실행해 발생한 에러를 Sauron에 보내고 분석 결과를 출력한다.

  uv run python run_scenarios.py --list
  uv run python run_scenarios.py                      # 전체 시나리오
  uv run python run_scenarios.py zero_stock bad_quantity
  uv run python run_scenarios.py --no-wait            # 전송만 하고 폴링하지 않음
  uv run python run_scenarios.py --dry-run            # 전송 없이 payload만 출력
"""
import argparse
import json
import logging
import sys

from sauron_reporter import SauronError
from sauron_reporter.config import reporter_from_env
from scenarios import MESSAGE_SCENARIOS, SCENARIOS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", help="실행할 시나리오 이름 (기본: 전체)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--no-wait", action="store_true", help="job 완료를 기다리지 않음")
    parser.add_argument("--dry-run", action="store_true", help="Sauron에 보내지 않고 payload만 출력")
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

    reporter = reporter_from_env(require_key=not args.dry_run)
    reporter.install_breadcrumbs()

    jobs: list[tuple[str, str]] = []
    failed = 0
    for name in names:
        print(f"\n===== {name} =====")
        reporter.breadcrumbs.records.clear()

        if name in MESSAGE_SCENARIOS:
            error_type, message = MESSAGE_SCENARIOS[name]
            logging.getLogger("shop.orders").error(message)
            payload = reporter.build_message_payload(error_type, message)
        else:
            try:
                SCENARIOS[name]()
            except Exception as exc:
                payload = reporter.build_exception_payload(exc)
            else:
                print("  예외가 발생하지 않았습니다 (버그가 고쳐졌나요?)")
                failed += 1
                continue

        event = payload["event"]
        print(f"  {event['type']}: {event['value']}")
        for frame in event["stacktrace"]:
            print(f"    {frame['filename']}:{frame['lineno']} in {frame['function']}")
        print(f"  fingerprint={payload['fingerprint']} breadcrumbs={len(payload['breadcrumbs'])}")

        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue

        try:
            data = reporter.send(payload)
        except SauronError as e:
            print(f"  전송 실패: {e}")
            failed += 1
            continue

        if "event_count" in data:
            print(f"  기존 이벤트 (event_count={data['event_count']}) job_id={data['job_id']}")
        else:
            print(f"  queued job_id={data['job_id']}")
        jobs.append((name, data["job_id"]))

    if args.no_wait or args.dry_run:
        return 1 if failed else 0

    for name, job_id in jobs:
        print(f"\n===== result: {name} ({job_id}) =====")
        try:
            job = reporter.wait_for_job(job_id, timeout=args.timeout)
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
