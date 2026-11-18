"""LLM 결과와 무관한 Sauron API 동작(Sentry 수집/에러코드/중복 처리)을 확인하는 스모크 테스트.

  uv run python smoke_api.py
  uv run python smoke_api.py --wait     # 수집된 job이 completed/failed 될 때까지 대기

SAURON_REPOSITORY_KEY가 없으면 저장소 키가 필요한 테스트는 건너뛴다.
수집 테스트는 항상 같은 에러를 보내므로, 분석 job(LLM 호출)은 처음 실행할 때 한 번만 생긴다.
"""
import argparse
import json
import os
import sys
import uuid

import sentry_sdk

from sauron_reporter.config import client_from_env, init_sentry_from_env

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    return ok


def envelope(event: dict) -> bytes:
    """sentry-sdk 없이 envelope를 직접 만든다 (에러 응답 확인용)."""
    event_id = uuid.uuid4().hex
    return b"\n".join([
        json.dumps({"event_id": event_id}).encode(),
        json.dumps({"type": "event"}).encode(),
        json.dumps({"event_id": event_id, **event}).encode(),
    ])


def smoke_error() -> None:
    raise RuntimeError("smoke test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    client = client_from_env()
    key = os.environ.get("SAURON_REPOSITORY_KEY", "")

    status, body = client.request("GET", "/health")
    if not check("GET /health", status == 200 and body == {"status": "ok"}, f"{status} {body}"):
        print("서버에 연결할 수 없습니다. 중단합니다.")
        return 1

    status, body = client.request("GET", "/source_control/repositories")
    check("GET /source_control/repositories", status == 200, f"{status} {body}")

    status, body = client.request("POST", "/analyze", {})
    check("POST /analyze (제거된 자체 SDK 경로) → 404/405", status in (404, 405), f"{status} {body}")

    error_event = {"level": "error", "exception": {"values": [{"type": "RuntimeError", "value": "smoke"}]}}
    path = "/api/1/envelope/"

    status, body = client.request("POST", path, envelope({"level": "info", "message": "hello"}))
    check("envelope info 메시지 (key 없음) → 200, 분석 안 함", status == 200, f"{status} {body}")

    status, body = client.request("POST", path, envelope(error_event))
    check(
        "envelope 에러 이벤트 key 없음 → 401",
        status == 401 and body.get("code") == "SentryAuthMissingError",
        f"{status} {body}",
    )

    status, body = client.request("POST", f"{path}?sentry_key=not-a-registered-key", envelope(error_event))
    check(
        "envelope 미등록 key → 404",
        status == 404 and body.get("code") == "CodeRepositoryKeyNotFoundError",
        f"{status} {body}",
    )

    status, body = client.request("POST", path, b"not json\n")
    check("envelope 형식 오류 → 400", status == 400 and body.get("code") == "InvalidSentryEnvelopeError", f"{status} {body}")

    status, body = client.request("POST", path, b"x", headers={"Content-Encoding": "zstd"})
    check("envelope 미지원 압축 → 415", status == 415, f"{status} {body}")

    status, body = client.request("GET", f"/analyze/{uuid.uuid4()}")
    check(
        "GET /analyze/{없는 job} → 404",
        status == 404 and body.get("code") == "AnalyzeJobNotFoundError",
        f"{status} {body}",
    )

    status, body = client.request("GET", "/analyze/not-a-uuid")
    check("GET /analyze/{잘못된 uuid} → 422", status == 422, f"{status} {body}")

    if not key:
        print("\nSAURON_REPOSITORY_KEY가 없어 sentry-sdk 수집/중복 테스트를 건너뜁니다.")
    else:
        init_sentry_from_env()

        def send() -> bool:
            try:
                smoke_error()
            except RuntimeError:
                sentry_sdk.capture_exception()
            return True

        first = client.send_and_find(send)
        if check("sentry-sdk 에러 → 이벤트 기록 + job 연결", bool(first and first["analyze_job_id"]), f"{first}"):
            job_id = first["analyze_job_id"]
            second = client.send_and_find(send)
            check(
                "같은 에러 다시 전송 → 같은 fingerprint, event_count +1, 같은 job",
                second["fingerprint"] == first["fingerprint"]
                and second["event_count"] == first["event_count"] + 1
                and second["analyze_job_id"] == job_id,
                f"{first} → {second}",
            )

            status, body = client.request("GET", f"/analyze/{job_id}")
            check(
                "GET /analyze/{job_id} → 200",
                status == 200 and body["data"]["status"] in ("queued", "running", "completed", "failed"),
                f"{status} {body}",
            )

            if args.wait:
                job = client.wait_for_job(job_id)
                check(
                    "job 완료",
                    job["status"] == "completed" and bool(job["result_content"]),
                    f"{job['status']} {job['error_message']}",
                )

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
