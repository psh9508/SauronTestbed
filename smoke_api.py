"""LLM 결과와 무관한 Sauron API 동작(검증/에러코드/중복 처리)을 확인하는 스모크 테스트.

  uv run python smoke_api.py
  uv run python smoke_api.py --wait     # 생성한 job이 completed/failed 될 때까지 대기

SAURON_REPOSITORY_KEY가 없으면 저장소 키가 필요한 테스트는 건너뛴다.
"""
import argparse
import secrets
import sys
import uuid

from sauron_reporter.config import reporter_from_env

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    return ok


def event(error_type: str = "RuntimeError", value: str = "smoke test") -> dict:
    return {
        "type": error_type,
        "value": value,
        "stacktrace": [{"filename": "shop/catalog.py", "lineno": 15, "function": "get_product"}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    client = reporter_from_env(require_key=False)
    key = client.repository_key

    status, body = client.request("GET", "/health")
    if not check("GET /health", status == 200 and body == {"status": "ok"}, f"{status} {body}"):
        print("서버에 연결할 수 없습니다. 중단합니다.")
        return 1

    status, body = client.request("GET", "/source_control/repositories")
    check("GET /source_control/repositories", status == 200, f"{status} {body}")

    status, body = client.request("POST", "/analyze", {
        "repository_key": "not-a-registered-key",
        "fingerprint": secrets.token_hex(16),
        "event": event(),
    })
    check(
        "POST /analyze 미등록 key → 404",
        status == 404 and body.get("code") == "CodeRepositoryKeyNotFoundError",
        f"{status} {body}",
    )

    status, body = client.request("POST", "/analyze", {
        "repository_key": key or "x",
        "fingerprint": "too-short",
        "event": event(),
    })
    check("POST /analyze fingerprint 길이 오류 → 422", status == 422, f"{status} {body}")

    status, body = client.request("POST", "/analyze", {
        "repository_key": key or "x",
        "fingerprint": secrets.token_hex(16),
    })
    check("POST /analyze event 누락 → 422", status == 422, f"{status} {body}")

    status, body = client.request("GET", f"/analyze/{uuid.uuid4()}")
    check(
        "GET /analyze/{없는 job} → 404",
        status == 404 and body.get("code") == "AnalyzeJobNotFoundError",
        f"{status} {body}",
    )

    status, body = client.request("GET", "/analyze/not-a-uuid")
    check("GET /analyze/{잘못된 uuid} → 422", status == 422, f"{status} {body}")

    if not key:
        print("\nSAURON_REPOSITORY_KEY가 없어 job 생성/중복 테스트를 건너뜁니다.")
    else:
        payload = {"repository_key": key, "fingerprint": secrets.token_hex(16), "event": event()}
        if client.repository_url:
            payload["repository_url"] = client.repository_url

        status, first = client.request("POST", "/analyze", payload)
        created = check(
            "POST /analyze 신규 fingerprint → 202 queued",
            status == 202 and first["data"]["status"] == "queued",
            f"{status} {first}",
        )

        if created:
            job_id = first["data"]["job_id"]
            status, second = client.request("POST", "/analyze", payload)
            check(
                "POST /analyze 같은 fingerprint → 200 기존 job, event_count=2",
                status == 200
                and second["data"]["job_id"] == job_id
                and second["data"]["event_count"] == 2,
                f"{status} {second}",
            )

            status, body = client.request("GET", "/analyze/errors")
            matched = [
                e for e in (body.get("data", {}).get("errors", []) if status == 200 else [])
                if e["fingerprint"] == payload["fingerprint"]
            ]
            check(
                "GET /analyze/errors 에 이벤트 포함",
                len(matched) == 1 and matched[0]["event_count"] == 2 and matched[0]["analyze_job_id"] == job_id,
                f"{status} {matched}",
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
