"""CLI: Administrator - audyt wszystkich wiadomości + broadcast do Agencji / Przewoźników / wszystkich."""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pika

from srq.connection_utils import connect_blocking
from srq import topology as t
from srq import messaging as m


def _audit_loop() -> None:
    conn = connect_blocking()
    try:
        ch = conn.channel()
        t.declare_topology(ch)
        ch.basic_qos(prefetch_count=100)

        def on_audit(
            channel: pika.channel.Channel,
            method: pika.spec.Basic.Deliver,
            _props: pika.BasicProperties | None,
            body: bytes,
        ) -> None:
            try:
                payload = m.loads_body(body)
            except m.MessageFormatError as exc:
                print("[AUDYT][odrzucone]", exc)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            meta = payload.get("_auditMeta")
            if meta:
                sender_role = meta.get("senderRole") or "?"
                sender_id = meta.get("senderId") or "?"
                target_exchange = meta.get("targetExchange") or "?"
                routing_key = meta.get("routingKey") or "?"
                print(
                    "[AUDYT]",
                    payload.get("msgType"),
                    "<-",
                    sender_role,
                    sender_id,
                    "| do",
                    target_exchange,
                    "rk=",
                    routing_key,
                )
            else:
                print("[AUDYT]", payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)

        ch.basic_consume(
            queue="q.audit.admin", on_message_callback=on_audit, auto_ack=False
        )
        ch.start_consuming()
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Moduł administracyjny (premium)")
    ap.add_argument(
        "--broadcast",
        metavar="TXT",
        help="Wyślij broadcast (bez interakcji); wymaga --mode",
    )
    ap.add_argument(
        "--mode",
        choices=("agencies", "carriers", "all"),
        help="Cel broadcastu: agencje, przewoźnicy lub obie grupy",
    )
    ap.add_argument(
        "--audit-wait-seconds",
        type=float,
        default=0.6,
        help="W trybie --broadcast: ile sekund poczekać na wydruk audytu",
    )
    args = ap.parse_args()

    threading.Thread(target=_audit_loop, daemon=True).start()

    ctrl = connect_blocking()
    try:
        pub = ctrl.channel()
        t.declare_topology(pub)
        pub.basic_qos(prefetch_count=50)

        if args.broadcast is not None:
            if args.mode is None:
                raise SystemExit("Podaj --mode agencies|carriers|all razem z --broadcast")
            _send_broadcast(pub, args.mode, args.broadcast)
            # Daemonowy wątek audytu potrzebuje chwili, żeby wypisać kopię wiadomości.
            if args.audit_wait_seconds > 0:
                time.sleep(args.audit_wait_seconds)
            return

        print(
            "Administrator - komendy: agencies <tekst> | carriers <tekst> | all <tekst> | quit"
        )
        while True:
            line = input().strip()
            if not line:
                continue
            low = line.lower()
            if low in ("quit", "exit"):
                break
            parts = line.split(maxsplit=1)
            mode = parts[0].lower()
            if mode not in ("agencies", "carriers", "all"):
                print("Nieznana komenda.")
                continue
            if len(parts) < 2:
                print("Podaj treść komunikatu po spacji.")
                continue
            text = parts[1]
            _send_broadcast(pub, mode, text)
    finally:
        ctrl.close()


def _send_broadcast(
    channel: pika.channel.Channel, mode: str, text: str
) -> None:
    payload_base = {
        "msgType": "ADMIN_BROADCAST",
        "mode": mode,
        "text": text,
        "sentAt": m.utc_now_iso(),
    }
    targets: list[tuple[str, str]] = []
    if mode in ("agencies", "all"):
        targets.append((t.EX_ADMIN_AGENCIES, ""))
    if mode in ("carriers", "all"):
        targets.append((t.EX_ADMIN_CARRIERS, ""))
    for exch, rk in targets:
        body = {**payload_base}
        try:
            m.validate_admin_broadcast(body)
        except m.MessageFormatError as exc:
            raise SystemExit(f"Nieprawidłowy broadcast: {exc}") from exc
        print(f"broadcast ({mode}) ->", exch, "|", body["text"])
        m.publish_with_audit(
            channel,
            target_exchange=exch,
            routing_key=rk,
            body=body,
            sender_role="Administrator",
            sender_id="admin",
        )


if __name__ == "__main__":
    main()
