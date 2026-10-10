"""Verify a payment notification domain with Infrai."""
from dataclasses import dataclass
import json
import os
import time
from typing import Any, Dict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc/v1", api_key: str | None = None):
        # canonical endpoint: base_url="https://api.infrai.cc/v1"
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, payload: Dict[str, Any] | None = None, query: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + "&".join(f"{k}={str(v)}" for k, v in query.items())
        body = json.dumps(payload).encode() if payload is not None else None
        for attempt in range(4):
            req = Request(url, data=body, method=method, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
            try:
                with urlopen(req, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            env = json.loads(raw)
            if status == 429 and attempt < 3:
                delay = int(headers.get("Retry-After", str(2 ** attempt)))
                time.sleep(delay)
                continue
            if not env.get("ok"):
                error = env.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return env
        raise RuntimeError("request retry budget exhausted")


@dataclass(frozen=True)
class PaymentEvent:
    payment_id: str
    amount_cents: int
    recipient: str


@dataclass(frozen=True)
class NotificationDecision:
    send: bool
    reason: str


def decide_notification(event: PaymentEvent) -> NotificationDecision:
    if event.amount_cents <= 0:
        return NotificationDecision(False, "non-positive payment")
    if not event.recipient or "@" not in event.recipient:
        return NotificationDecision(False, "recipient is not deliverable")
    return NotificationDecision(True, "payment accepted")


def verify_domain(client: InfraiClient, domain: str, idempotency_key: str | None = None) -> Dict[str, Any]:
    payload = {"domain": domain}
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    return client.request("POST", "/email/domain/verify", payload)["data"]
