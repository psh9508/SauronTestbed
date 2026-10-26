"""표준 라이브러리만 사용하는 최소 Sauron 클라이언트.

예외를 Sauron의 AnalyzeCreateReq 형식(event/stacktrace/breadcrumbs/fingerprint)으로 변환해
POST /analyze 로 보내고, GET /analyze/{job_id} 를 폴링해 결과를 받는다.
"""
import hashlib
import json
import logging
import time
import traceback
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SauronError(Exception):
    def __init__(self, status: int, body: Any):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


class BreadcrumbHandler(logging.Handler):
    """에러 직전 로그를 breadcrumbs로 보관하는 핸들러."""

    def __init__(self, maxlen: int = 50):
        super().__init__()
        self.records: deque[dict] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append({
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })


class SauronReporter:
    def __init__(
        self,
        base_url: str,
        repository_key: str,
        repository_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.repository_key = repository_key
        self.repository_url = repository_url
        self.timeout = timeout
        self.breadcrumbs = BreadcrumbHandler()

    def install_breadcrumbs(self, level: int = logging.INFO) -> None:
        root = logging.getLogger()
        root.setLevel(level)
        root.addHandler(self.breadcrumbs)

    # ---- payload ----

    @staticmethod
    def _relative_filename(filename: str) -> str:
        # Sauron은 stacktrace 경로와 저장소 경로를 suffix/basename으로 매칭하므로 저장소 상대경로로 보낸다
        try:
            return Path(filename).resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return filename

    @classmethod
    def build_stacktrace(cls, exc: BaseException) -> list[dict]:
        frames = traceback.extract_tb(exc.__traceback__)
        return [
            {
                "filename": cls._relative_filename(frame.filename),
                "lineno": frame.lineno or 0,
                "function": frame.name,
                "code": frame.line or None,
            }
            for frame in frames
        ]

    @staticmethod
    def fingerprint(error_type: str, stacktrace: list[dict], message: str = "") -> str:
        # 값(value)은 제외하고 타입 + 프레임 위치로 그룹핑 → 같은 버그는 같은 fingerprint
        parts = [error_type] + [f"{f['filename']}:{f['function']}:{f['lineno']}" for f in stacktrace]
        if not stacktrace:
            parts.append(message)
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def build_exception_payload(self, exc: BaseException) -> dict:
        stacktrace = self.build_stacktrace(exc)
        error_type = type(exc).__name__
        return self._payload(error_type, str(exc), stacktrace)

    def build_message_payload(self, error_type: str, message: str) -> dict:
        return self._payload(error_type, message, [])

    def _payload(self, error_type: str, value: str, stacktrace: list[dict]) -> dict:
        payload = {
            "repository_key": self.repository_key,
            "fingerprint": self.fingerprint(error_type, stacktrace, value),
            "event": {"type": error_type, "value": value, "stacktrace": stacktrace},
            "breadcrumbs": list(self.breadcrumbs.records),
        }
        if self.repository_url:
            payload["repository_url"] = self.repository_url
        return payload

    # ---- http ----

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw.decode(errors="replace")

    def send(self, payload: dict) -> dict:
        status, body = self.request("POST", "/analyze", payload)
        if status not in (200, 202):
            raise SauronError(status, body)
        return body["data"]

    def capture_exception(self, exc: BaseException) -> dict:
        return self.send(self.build_exception_payload(exc))

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
