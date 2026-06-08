"""Shared AMQP URL and connection bootstrap."""

from __future__ import annotations

import os

import pika

DEFAULT_AMQP_URL = os.environ.get("AMQP_URL", "amqp://guest:guest@localhost:5672/%2f")


def connect_blocking() -> pika.BlockingConnection:
    params = pika.URLParameters(DEFAULT_AMQP_URL)
    return pika.BlockingConnection(params)
