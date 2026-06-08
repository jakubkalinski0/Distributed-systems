"""JSON message helpers and publish with audit copy."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pika

from srq import topology as t


class MessageFormatError(ValueError):
    """Raised when message payload is not valid JSON or has invalid fields."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def loads_body(body: bytes) -> dict[str, Any]:
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MessageFormatError("Body nie jest UTF-8") from exc

    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise MessageFormatError(f"Błędny JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise MessageFormatError("JSON musi być obiektem")

    return payload


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise MessageFormatError(f"Pole '{key}' musi być tekstem")
    cleaned = value.strip()
    if not cleaned:
        raise MessageFormatError(f"Pole '{key}' nie może być puste")
    return cleaned


def _require_identifier(payload: dict[str, Any], key: str) -> str:
    value = _require_text(payload, key).lower()
    if not t.is_valid_identifier(value):
        raise MessageFormatError(
            f"Pole '{key}' musi pasować do [a-z0-9_-], max 32 znaki"
        )
    return value


def _require_service(payload: dict[str, Any]) -> str:
    service = _require_text(payload, "service").lower()
    if service not in t.SERVICE_CHOICES:
        raise MessageFormatError(
            f"Pole 'service' musi być jednym z: {', '.join(t.SERVICE_CHOICES)}"
        )
    return service


def _require_msg_type(payload: dict[str, Any], expected: str) -> None:
    msg_type = _require_text(payload, "msgType").upper()
    if msg_type != expected:
        raise MessageFormatError(f"Oczekiwano msgType={expected}, otrzymano {msg_type}")


def validate_order(payload: dict[str, Any]) -> dict[str, str]:
    _require_msg_type(payload, "ORDER")
    return {
        "agencyId": _require_identifier(payload, "agencyId"),
        "orderNo": _require_text(payload, "orderNo"),
        "service": _require_service(payload),
    }


def validate_confirmation(payload: dict[str, Any]) -> dict[str, str]:
    _require_msg_type(payload, "CONFIRMATION")
    data = validate_order({**payload, "msgType": "ORDER"})
    data["carrierId"] = _require_identifier(payload, "carrierId")
    return data


def validate_admin_broadcast(payload: dict[str, Any]) -> dict[str, str]:
    _require_msg_type(payload, "ADMIN_BROADCAST")
    mode = _require_text(payload, "mode").lower()
    if mode not in ("agencies", "carriers", "all"):
        raise MessageFormatError("Pole 'mode' musi być: agencies, carriers albo all")
    return {
        "mode": mode,
        "text": _require_text(payload, "text"),
    }


def publish_with_audit(
    channel: pika.channel.Channel,
    *,
    target_exchange: str,
    routing_key: str,
    body: dict[str, Any],
    sender_role: str,
    sender_id: str,
) -> None:
    """Publish to business exchange and duplicate to ex.audit (fanout)."""
    props = pika.BasicProperties(
        content_type="application/json",
        delivery_mode=pika.DeliveryMode.Persistent,
    )
    channel.basic_publish(
        exchange=target_exchange,
        routing_key=routing_key,
        body=dumps_body(body),
        properties=props,
    )
    audit_payload = {
        **body,
        "_auditMeta": {
            "targetExchange": target_exchange,
            "routingKey": routing_key or "(fanout)",
            "senderRole": sender_role,
            "senderId": sender_id,
            "capturedAt": utc_now_iso(),
        },
    }
    channel.basic_publish(
        exchange=t.EX_AUDIT,
        routing_key="",
        body=dumps_body(audit_payload),
        properties=props,
    )
