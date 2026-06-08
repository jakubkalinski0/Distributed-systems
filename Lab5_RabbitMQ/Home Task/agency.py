"""CLI: kosmiczna Agencja - zlecenia + odbiór potwierdzeń oraz komunikatów admina."""

from __future__ import annotations

import argparse
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pika

from srq.connection_utils import connect_blocking
from srq import topology as t
from srq import messaging as m


SERVICE_CHOICES = t.SERVICE_CHOICES


def _consume_confirmations(slug: str) -> None:
    conn = connect_blocking()
    try:
        ch = conn.channel()
        t.declare_topology(ch)
        t.declare_agency_bindings(ch, slug)
        ch.basic_qos(prefetch_count=50)
        qconf = t.confirmations_queue(slug)

        def on_confirmation(
            channel: pika.channel.Channel,
            method: pika.spec.Basic.Deliver,
            _props: pika.BasicProperties | None,
            body: bytes,
        ) -> None:
            try:
                payload = m.loads_body(body)
                data = m.validate_confirmation(payload)
            except m.MessageFormatError as exc:
                print("[potwierdzenie][odrzucone]", exc)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            print(
                "[potwierdzenie]",
                payload.get("msgType"),
                "zlecenie",
                data["orderNo"],
                "usługa",
                data["service"],
                "Przewoźnik",
                data["carrierId"],
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)

        ch.basic_consume(queue=qconf, on_message_callback=on_confirmation, auto_ack=False)
        ch.start_consuming()
    finally:
        conn.close()


def _consume_admin(slug: str) -> None:
    conn = connect_blocking()
    try:
        ch = conn.channel()
        t.declare_topology(ch)
        t.declare_agency_bindings(ch, slug)
        ch.basic_qos(prefetch_count=50)
        qadm = t.admin_agency_notify_queue(slug)

        def on_admin(
            channel: pika.channel.Channel,
            method: pika.spec.Basic.Deliver,
            _props: pika.BasicProperties | None,
            body: bytes,
        ) -> None:
            try:
                payload = m.loads_body(body)
                data = m.validate_admin_broadcast(payload)
            except m.MessageFormatError as exc:
                print("[admin][odrzucone]", exc)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            print(
                "[admin]",
                data["text"],
                "| tryb:",
                data["mode"],
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)

        ch.basic_consume(queue=qadm, on_message_callback=on_admin, auto_ack=False)
        ch.start_consuming()
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Agencja kosmiczna")
    ap.add_argument(
        "--slug",
        type=t.normalize_agency_slug,
        required=True,
        help="Identyfikator agencji [a-z0-9_-], np. nasa",
    )
    args = ap.parse_args()
    slug = args.slug

    threading.Thread(target=_consume_confirmations, args=(slug,), daemon=True).start()
    threading.Thread(target=_consume_admin, args=(slug,), daemon=True).start()

    publisher_conn = connect_blocking()
    publisher = publisher_conn.channel()
    t.declare_topology(publisher)
    publisher.basic_qos(prefetch_count=50)

    print(
        "Agencja:",
        slug,
        "- komendy: people|cargo|satellite oraz numer zlecenia, np.: cargo 101",
        "lub quit",
    )
    try:
        while True:
            line = input().strip().lower()
            if line in ("quit", "exit"):
                break
            parts = line.split()
            if len(parts) != 2:
                print("Wpisz: <usługa> <numer_zlecenia>")
                continue
            service_raw, order_no = parts
            if service_raw not in SERVICE_CHOICES:
                print("Usługa musi być jedną z:", SERVICE_CHOICES)
                continue
            rk = t.ORDER_SERVICE_TO_ROUTING_KEY[service_raw]
            body = {
                "msgType": "ORDER",
                "agencyId": slug,
                "orderNo": order_no,
                "service": service_raw,
                "issuedAt": m.utc_now_iso(),
            }
            try:
                m.validate_order(body)
            except m.MessageFormatError as exc:
                print("Błąd wiadomości ORDER:", exc)
                continue
            m.publish_with_audit(
                publisher,
                target_exchange=t.EX_ORDERS,
                routing_key=rk,
                body=body,
                sender_role="Agencja",
                sender_id=slug,
            )
            print("wysłano zlecenie:", body)
    finally:
        publisher_conn.close()


if __name__ == "__main__":
    main()
