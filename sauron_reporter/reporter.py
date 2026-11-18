"""표준 라이브러리만 사용하는 최소 Sauron API 클라이언트.

에러 전송은 sentry-sdk가 담당한다 (DSN → POST /api/<project_id>/envelope/).
Sentry 엔드포인트는 job_id를 돌려주지 않으므로, 전송 전후의 GET /analyze/errors를 비교해
이번 전송으로 생기거나 event_count가 늘어난 이벤트를 찾고, 그 analyze job을 폴링한다.
"""
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import sentry_sdk

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SauronError(Exception):
    def __init__(self, status: int, body: Any):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


class SauronClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ---- http ----

    def request(
        self,
        method: str,
        path: str,
        body: dict | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        if isinstance(body, dict):
            data = json.dumps(body).encode()
            headers = {"Content-Type": "application/json", **(headers or {})}
        else:
            data = body
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw.decode(errors="replace")

    def list_errors(self) -> list[dict]:
        status, body = self.request("GET", "/analyze/errors")
        if status != 200:
            raise SauronError(status, body)
        return body["data"]["errors"]

    def get_job(self, job_id: str) -> dict:
        status, body = self.request("GET", f"/analyze/{job_id}")
        if status != 200:
            raise SauronError(status, body)
        return body["data"]

    def wait_for_job(self, job_id: str, timeout: float = 300.0, interval: float = 3.0) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            job = self.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                return job
            if time.monotonic() > deadline:
                raise TimeoutError(f"job {job_id} still {job['status']} after {timeout}s")
            time.sleep(interval)

    # ---- sentry 전송 → 이벤트 찾기 ----

    def send_and_find(self, send: Callable[[], bool], timeout: float = 10.0) -> dict | None:
        """send()로 Sentry 이벤트를 보낸 뒤 Sauron에 기록된 에러 이벤트를 돌려준다.

        send()가 False를 돌려주면(보낸 이벤트 없음) None을 돌려준다.
        시나리오를 하나씩 보낸다는 전제로, 전송 전보다 event_count가 늘어난 이벤트를 이번 전송으로 본다.
        """
        before = {e["fingerprint"]: e["event_count"] for e in self.list_errors()}
        if not send():
            return None
        sentry_sdk.flush()

        deadline = time.monotonic() + timeout
        while True:
            changed = [e for e in self.list_errors() if e["event_count"] > before.get(e["fingerprint"], 0)]
            if changed:
                return changed[0]
            if time.monotonic() > deadline:
                raise TimeoutError(
                    "Sauron에 이벤트가 기록되지 않았습니다. 서버 로그와 SAURON_REPOSITORY_KEY를 확인하세요."
                )
            time.sleep(0.5)
