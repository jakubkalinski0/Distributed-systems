#!/usr/bin/env bash
set -e

echo "Waiting for head at ray-head:6379..."
for n in $(seq 1 120); do
  if python -c "import socket; s=socket.create_connection(('ray-head',6379),3); s.close()" 2>/dev/null \
     && ray status --address=ray-head:6379 >/dev/null 2>&1; then
    echo "Head reachable after ${n}s"
    break
  fi
  sleep 2
done

if ! ray status --address=ray-head:6379 >/dev/null 2>&1; then
  echo "ERROR: cannot reach Ray head"
  exit 1
fi

echo "Starting worker..."
exec ray start --address=ray-head:6379 --num-cpus=4 --block
