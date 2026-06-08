"""RabbitMQ exchanges, queues, and bindings for Agencje / Przewoźnicy / Admin."""

from __future__ import annotations

import re
from collections.abc import Iterable

SERVICE_CHOICES = ("people", "cargo", "satellite")

ORDER_SERVICE_TO_ROUTING_KEY = {
    service: f"order.{service}" for service in SERVICE_CHOICES
}

SERVICE_TO_ORDER_QUEUE = {
    service: f"q.orders.{service}" for service in SERVICE_CHOICES
}

DEMO_AGENCY_SLUGS = ("nasa", "esa")
DEMO_CARRIER_IDS = ("carrier1", "carrier2")

# Kept for backward compatibility in callers and docs.
AGENCY_SLUGS = DEMO_AGENCY_SLUGS
CARRIER_IDS = DEMO_CARRIER_IDS

EX_ORDERS = "ex.orders"
EX_CONFIRMATIONS = "ex.confirmations"
EX_AUDIT = "ex.audit"
EX_ADMIN_AGENCIES = "ex.admin.agencies"
EX_ADMIN_CARRIERS = "ex.admin.carriers"

_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


def confirmations_queue(slug: str) -> str:
    return f"q.confirmations.{slug}"


def admin_agency_notify_queue(slug: str) -> str:
    return f"q.admin.notify.agency.{slug}"


def admin_carrier_notify_queue(carrier_id: str) -> str:
    return f"q.admin.notify.carrier.{carrier_id}"


def agency_routing_key(slug: str) -> str:
    return f"agency.{slug}"


def is_valid_identifier(value: str) -> bool:
    return bool(_IDENTIFIER_RE.fullmatch(value))


def normalize_identifier(value: str, *, field_label: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{field_label}: pusty identyfikator")
    if not is_valid_identifier(normalized):
        raise ValueError(
            f"{field_label}: użyj [a-z0-9_-], max 32 znaki, pierwszy znak [a-z0-9]"
        )
    return normalized


def normalize_agency_slug(value: str) -> str:
    return normalize_identifier(value, field_label="slug agencji")


def normalize_carrier_id(value: str) -> str:
    return normalize_identifier(value, field_label="id przewoźnika")


def parse_services(value: str) -> tuple[str, ...]:
    picked = tuple(s.strip().lower() for s in value.split(",") if s.strip())
    unique = tuple(dict.fromkeys(picked))
    if len(unique) != 2:
        raise ValueError("Podaj dokładnie 2 różne usługi: people,cargo,satellite")
    for service in unique:
        if service not in SERVICE_TO_ORDER_QUEUE:
            raise ValueError(f"Nieznana usługa: {service}")
    return unique


def _normalize_unique(
    values: Iterable[str], *, normalizer
) -> tuple[str, ...]:
    cleaned = [normalizer(v) for v in values]
    return tuple(dict.fromkeys(cleaned))


def declare_agency_bindings(channel, slug: str) -> None:
    normalized_slug = normalize_agency_slug(slug)
    qconf = confirmations_queue(normalized_slug)
    channel.queue_declare(queue=qconf, durable=True)
    channel.queue_bind(
        exchange=EX_CONFIRMATIONS,
        queue=qconf,
        routing_key=agency_routing_key(normalized_slug),
    )

    qadmin = admin_agency_notify_queue(normalized_slug)
    channel.queue_declare(queue=qadmin, durable=True)
    channel.queue_bind(
        exchange=EX_ADMIN_AGENCIES,
        queue=qadmin,
    )


def declare_carrier_bindings(channel, carrier_id: str) -> None:
    normalized_cid = normalize_carrier_id(carrier_id)
    qc = admin_carrier_notify_queue(normalized_cid)
    channel.queue_declare(queue=qc, durable=True)
    channel.queue_bind(
        exchange=EX_ADMIN_CARRIERS,
        queue=qc,
    )


def declare_topology(
    channel,
    *,
    agency_slugs: Iterable[str] = DEMO_AGENCY_SLUGS,
    carrier_ids: Iterable[str] = DEMO_CARRIER_IDS,
) -> None:
    channel.exchange_declare(
        exchange=EX_ORDERS, exchange_type="topic", durable=True
    )
    channel.exchange_declare(
        exchange=EX_CONFIRMATIONS, exchange_type="topic", durable=True
    )
    channel.exchange_declare(
        exchange=EX_AUDIT, exchange_type="fanout", durable=True
    )
    channel.exchange_declare(
        exchange=EX_ADMIN_AGENCIES, exchange_type="fanout", durable=True
    )
    channel.exchange_declare(
        exchange=EX_ADMIN_CARRIERS, exchange_type="fanout", durable=True
    )

    for service, queue_name in SERVICE_TO_ORDER_QUEUE.items():
        routing_key = ORDER_SERVICE_TO_ROUTING_KEY[service]
        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(
            exchange=EX_ORDERS,
            queue=queue_name,
            routing_key=routing_key,
        )

    for slug in _normalize_unique(agency_slugs, normalizer=normalize_agency_slug):
        declare_agency_bindings(channel, slug)

    for cid in _normalize_unique(carrier_ids, normalizer=normalize_carrier_id):
        declare_carrier_bindings(channel, cid)

    channel.queue_declare(queue="q.audit.admin", durable=True)
    channel.queue_bind(exchange=EX_AUDIT, queue="q.audit.admin")
