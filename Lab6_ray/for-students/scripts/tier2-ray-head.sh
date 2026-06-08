#!/usr/bin/env bash
set -e

ray start --head \
  --port=6379 \
  --dashboard-host=0.0.0.0 \
  --dashboard-port=8265 \
  --ray-client-server-port=10001 \
  --num-cpus=4

echo "Waiting for Ray head (GCS + dashboard)..."
for n in $(seq 1 120); do
  if python -c "import socket; s=socket.create_connection(('127.0.0.1',6379),3); s.close()" 2>/dev/null \
     && ray status >/dev/null 2>&1; then
    echo "Ray head ready after ${n}s"
    # Utrzymaj kontener przy życiu (demony Ray działają w tle).
    exec sleep infinity
  fi
  sleep 2
done

echo "ERROR: Ray head did not become ready in time"
exit 1
