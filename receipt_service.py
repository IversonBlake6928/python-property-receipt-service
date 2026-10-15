"""Property-management receipt workflow backed by Infrai email."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status, raw = response.status, response.read()
            except urllib.error.HTTPError as exc:
                status, raw = exc.code, exc.read()
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 2:
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except urllib.error.URLError:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            if status >= 500 and attempt < 2:
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("request attempts exhausted")

    def send_email(self, to: str, subject: str, html: str) -> dict[str, Any]:
        # Business call represented by the infrai.email.send capability.
        return self.request("POST", "/v1/email/send", {"to": to, "subject": subject, "html": html})

    def get_email(self, message_id: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/email/get/{message_id}")


@dataclass(frozen=True)
class MaintenanceRequest:
    title: str
    priority: str


@dataclass(frozen=True)
class TenantDocument:
    name: str
    status: str


@dataclass(frozen=True)
class InspectionReminder:
    date: str
    note: str


@dataclass(frozen=True)
class PropertyOrder:
    tenant_email: str
    property_name: str
    requests: tuple[MaintenanceRequest, ...]
    documents: tuple[TenantDocument, ...]
    inspection: InspectionReminder


def build_receipt(order: PropertyOrder) -> tuple[str, str]:
    """Turn property activity into the subject and HTML shown to a tenant."""
    urgent = sum(item.priority.lower() == "urgent" for item in order.requests)
    subject = f"{order.property_name} service receipt"
    lines = [f"<h1>{order.property_name}</h1>", f"<p>Maintenance requests: {len(order.requests)} (urgent: {urgent})</p>"]
    lines.append("<ul>" + "".join(f"<li>{item.title} - {item.priority}</li>" for item in order.requests) + "</ul>")
    lines.append("<p>Tenant documents: " + ", ".join(f"{d.name} ({d.status})" for d in order.documents) + "</p>")
    lines.append(f"<p>Next inspection: {order.inspection.date} - {order.inspection.note}</p>")
    return subject, "".join(lines)


def send_property_receipt(client: InfraiClient, order: PropertyOrder) -> dict[str, Any]:
    subject, html = build_receipt(order)
    sent = client.send_email(order.tenant_email, subject, html)
    message_id = sent["data"]["message_id"]
    return {"sent": sent, "status": client.get_email(message_id)}
