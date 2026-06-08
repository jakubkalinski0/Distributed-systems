"""CLI: Przewoźnik - nasłuchuje typów usług (konkurencja przy współdzielonej kolejce cargo)."""

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


def _consume_admin(carrier_id: str) -> None:
    conn = connect_blocking()
    try:
        ch = conn.channel()
        t.declare_topology(ch)
        t.declare_carrier_bindings(ch, carrier_id)
        ch.basic_qos(prefetch_count=50)
        adm_q = t.admin_carrier_notify_queue(carrier_id)

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

        ch.basic_consume(queue=adm_q, on_message_callback=on_admin, auto_ack=False)
        ch.start_consuming()
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Przewoźnik kosmiczny")
    ap.add_argument(
        "--id",
        dest="carrier_id",
        type=t.normalize_carrier_id,
        required=True,
        help="Identyfikator przewoźnika [a-z0-9_-], np. carrier1",
    )
    ap.add_argument(
        "--services",
        required=True,
        help="Dwie usługi oddzielone przecinkiem, np. people,cargo",
    )
    args = ap.parse_args()
    try:
        wanted = t.parse_services(args.services)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    queues = sorted({t.SERVICE_TO_ORDER_QUEUE[s] for s in wanted})
    cid = args.carrier_id

    threading.Thread(target=_consume_admin, args=(cid,), daemon=True).start()

    connection = connect_blocking()
    ch = connection.channel()
    t.declare_topology(ch)
    t.declare_carrier_bindings(ch, cid)
    ch.basic_qos(prefetch_count=1)

    def on_order(
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        _props: pika.BasicProperties | None,
        body: bytes,
    ) -> None:
        try:
            payload = m.loads_body(body)
            data = m.validate_order(payload)
        except m.MessageFormatError as exc:
            print("[zlecenie][odrzucone]", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        slug = data["agencyId"]
        order_no = data["orderNo"]
        service = data["service"]
        if service not in wanted:
            print("[zlecenie][odrzucone] przewoźnik nie obsługuje:", service)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        print("[zlecenie]", "od", slug, order_no, service)

        confirming = {
            "msgType": "CONFIRMATION",
            "agencyId": slug,
            "orderNo": order_no,
            "service": service,
            "carrierId": cid,
            "completedAt": m.utc_now_iso(),
        }
        try:
            m.validate_confirmation(confirming)
        except m.MessageFormatError as exc:
            print("[potwierdzenie][błąd lokalny]", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return
        m.publish_with_audit(
            channel,
            target_exchange=t.EX_CONFIRMATIONS,
            routing_key=t.agency_routing_key(str(slug)),
            body=confirming,
            sender_role="Przewoźnik",
            sender_id=cid,
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        print("  -> potwierdzenie dla agencji", slug)

    for qname in queues:
        ch.basic_consume(queue=qname, on_message_callback=on_order, auto_ack=False)

    print(f"Przewoźnik {cid} oczekuje zleceń na kolejkach:", ", ".join(queues))
    ch.start_consuming()


if __name__ == "__main__":
    main()
