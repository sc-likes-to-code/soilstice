"""Shared HTTP acquisition layer for every provider (INTEGRATION_GUIDE §0.3, DATA_ARCHITECTURE §5.1 stage 1).

- Retries: up to N retries with exponential backoff (base, 2·base, 4·base) + jitter on 429, 5xx and timeouts.
  No retry on other 4xx.
- Raw cache: responses stored immutably under cache_dir/raw/<dataset_id>/<sha256(request)>.bin with a
  metadata file holding the ORIGINAL acquisition record, so provenance survives cache hits.
- Every request produces an AcquisitionRecord (URL, redacted params, HTTP status, sha256, bytes, retrieved_at).
  Secrets (tokens, passwords, keys) never reach the record or the logs.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.logging import get_logger
from app.repositories.records import AcquisitionRecord

log = get_logger("providers.http")

SECRET_KEYS = {"token", "key", "api_key", "apikey", "password", "authorization", "access_token"}
URS_HOST = "urs.earthdata.nasa.gov"


class ProviderError(Exception):
    """A provider could not deliver data. `missing_reason` is the contract code to report."""

    def __init__(self, message: str, missing_reason: str = "UPSTREAM_ERROR", *, http_status: int | None = None):
        super().__init__(message)
        self.missing_reason = missing_reason
        self.http_status = http_status


class ProviderNotConfigured(ProviderError):
    def __init__(self, message: str):
        super().__init__(message, "NOT_COMPUTED")


@dataclass
class Fetched:
    content: bytes
    status_code: int
    acquisition: AcquisitionRecord
    from_cache: bool

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.content)


def redact(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {k: ("<redacted>" if k.lower() in SECRET_KEYS else v) for k, v in params.items()}


def request_key(method: str, url: str, params: dict | None, body: Any) -> str:
    canon = json.dumps({"m": method.upper(), "u": url, "p": params or {}, "b": body}, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


class HttpAcquirer:
    def __init__(
        self,
        cache_dir: Path,
        *,
        retries: int = 3,
        backoff_base_s: float = 2.0,
        timeout_s: float = 60.0,
        record_sink: Callable[[AcquisitionRecord], None] | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.cache_dir = Path(cache_dir)
        self.retries = retries
        self.backoff_base_s = backoff_base_s
        self.timeout_s = timeout_s
        self.record_sink = record_sink
        self._transport = transport
        self._sleep = sleep

    def _client(self, timeout: float) -> httpx.Client:
        return httpx.Client(timeout=timeout, transport=self._transport, follow_redirects=False,
                            headers={"User-Agent": "soilstice-backend/0.2 (research prototype)"})

    def _paths(self, dataset_id: str, key: str) -> tuple[Path, Path]:
        d = self.cache_dir / "raw" / dataset_id
        return d / f"{key}.bin", d / f"{key}.json"

    def fetch(
        self,
        dataset_id: str,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        cache: bool = True,
        auth: EarthdataAuth | None = None,
        accept_status: tuple[int, ...] = (200,),
        retry_on_5xx: bool = True,
    ) -> Fetched:
        key = request_key(method, url, params, json_body)
        bin_path, meta_path = self._paths(dataset_id, key)
        if cache and bin_path.exists() and meta_path.exists():
            record = AcquisitionRecord.model_validate_json(meta_path.read_text())
            log.info("cache hit", extra={"dataset_id": dataset_id, "url": url})
            return Fetched(bin_path.read_bytes(), record.http_status or 200, record, True)

        attempt = 0
        last_exc: Exception | None = None
        while True:
            try:
                resp = self._send(method, url, params, json_body, timeout or self.timeout_s, auth, headers)
                status = resp.status_code
                if status in accept_status:
                    return self._store(dataset_id, url, params, resp, key, cache)
                retryable = status == 429 or (status >= 500 and retry_on_5xx)
                self._record_failure(dataset_id, url, params, status, f"HTTP{status}")
                if not retryable or attempt >= self.retries:
                    if status in (401, 403):
                        raise ProviderError(f"{dataset_id}: authentication rejected (HTTP {status}).",
                                            "UPSTREAM_ERROR", http_status=status)
                    raise ProviderError(f"{dataset_id}: upstream returned HTTP {status}.", "UPSTREAM_ERROR",
                                        http_status=status)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                self._record_failure(dataset_id, url, params, None, type(exc).__name__)
                if attempt >= self.retries:
                    raise ProviderError(f"{dataset_id}: upstream unreachable ({type(exc).__name__}).") from last_exc
            delay = self.backoff_base_s * (2**attempt) + random.uniform(0, self.backoff_base_s / 2)
            log.warning("retrying upstream request", extra={"dataset_id": dataset_id, "url": url, "attempt": attempt + 1,
                                                            "delay_s": round(delay, 2)})
            self._sleep(delay)
            attempt += 1

    def _send(self, method, url, params, json_body, timeout, auth, extra_headers=None) -> httpx.Response:
        """Manual redirect loop so Earthdata basic auth is only ever sent to urs.earthdata.nasa.gov."""
        with self._client(timeout) as client:
            req_url, req_params, hops = url, params, 0
            headers = dict(extra_headers or {})
            if auth:
                headers.update(auth.initial_headers())
            while True:
                resp = client.request(method if hops == 0 else "GET", req_url, params=req_params,
                                      json=json_body if hops == 0 else None, headers=headers)
                if resp.status_code in (301, 302, 303, 307, 308) and "location" in resp.headers and hops < 10:
                    nxt = resp.url.join(resp.headers["location"])
                    req_url, req_params, hops = str(nxt), None, hops + 1
                    headers = auth.headers_for(nxt.host) if auth else dict(extra_headers or {})
                    continue
                return resp

    def _store(self, dataset_id, url, params, resp: httpx.Response, key: str, cache: bool) -> Fetched:
        content = resp.content
        record = AcquisitionRecord(
            acquisition_id=uuid.uuid4(),
            dataset_id=dataset_id,
            request_url=url,
            request_params_redacted=redact(params),
            http_status=resp.status_code,
            sha256=hashlib.sha256(content).hexdigest(),
            bytes=len(content),
            retrieved_at=datetime.now(UTC),
        )
        if cache:
            bin_path, meta_path = self._paths(dataset_id, key)
            bin_path.parent.mkdir(parents=True, exist_ok=True)
            bin_path.write_bytes(content)
            record = record.model_copy(update={"object_uri": bin_path.as_posix()})
            meta_path.write_text(record.model_dump_json())
        if self.record_sink:
            self.record_sink(record)
        log.info("acquired", extra={"dataset_id": dataset_id, "url": url, "status": resp.status_code,
                                    "bytes": len(content)})
        return Fetched(content, resp.status_code, record, False)

    def _record_failure(self, dataset_id, url, params, status, error_class) -> None:
        record = AcquisitionRecord(
            acquisition_id=uuid.uuid4(), dataset_id=dataset_id, request_url=url,
            request_params_redacted=redact(params), http_status=status, retrieved_at=datetime.now(UTC),
            error_class=error_class,
        )
        if self.record_sink:
            self.record_sink(record)
        log.warning("upstream failure", extra={"dataset_id": dataset_id, "url": url, "status": status,
                                               "error_class": error_class})


class EarthdataAuth:
    """NASA Earthdata Login. Bearer token (preferred) on the first request; or basic auth sent ONLY to URS."""

    def __init__(self, token: str | None = None, username: str | None = None, password: str | None = None):
        if not token and not (username and password):
            raise ProviderNotConfigured(
                "NASA Earthdata credentials are not configured (set SOILSTICE_EARTHDATA_TOKEN, or "
                "SOILSTICE_EARTHDATA_USERNAME and SOILSTICE_EARTHDATA_PASSWORD)."
            )
        self._token = token
        self._basic = httpx.BasicAuth(username, password) if username and password else None

    def initial_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def headers_for(self, host: str) -> dict[str, str]:
        if host == URS_HOST and self._basic is not None:
            req = httpx.Request("GET", f"https://{host}/")
            return {"Authorization": next(self._basic.auth_flow(req)).headers["Authorization"]}
        return {}
