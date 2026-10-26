"""sauron-python SDK로 시나리오 에러를 Sauron에 보낸다.

  uv run python sdk_scenarios.py                    # 전체 시나리오를 capture_exception으로 전송
  uv run python sdk_scenarios.py zero_stock         # 일부만
  uv run python sdk_scenarios.py --uncaught zero_stock  # 잡지 않은 예외 → excepthook 경로로 전송
"""
import argparse
import logging

from sauron_python import capture_exception

from sauron_reporter.config import init_sdk_from_env
from scenarios import SCENARIOS

logger = logging.getLogger("sdk_scenarios")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", help="실행할 시나리오 (기본: 전체)")
    parser.add_argument("--uncaught", action="store_true", help="첫 시나리오 예외를 잡지 않고 프로세스를 종료")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    init_sdk_from_env()

    names = args.names or list(SCENARIOS)
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        parser.error(f"알 수 없는 시나리오: {', '.join(unknown)}")

    for name in names:
        logger.info("scenario start: %s", name)
        if args.uncaught:
            SCENARIOS[name]()
        try:
            SCENARIOS[name]()
        except Exception:
            capture_exception()
            print(f"sent: {name}")
    # 전송은 백그라운드 워커가 처리하고, 종료 시 atexit에서 flush된다


if __name__ == "__main__":
    main()
