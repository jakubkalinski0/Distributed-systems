#!/usr/bin/env bash
# Integration test helper — manipulates znode /a via zkCli in Docker
set -euo pipefail

ACTION="${1:-full-test}"
CHILD_NAME="${2:-child1}"
ZK_CONTAINER="${ZK_CONTAINER:-zk1}"
ZK_SERVER="${ZK_SERVER:-localhost:2181}"

zk_cli() {
  printf '%s\n' "$@" | docker exec -i "$ZK_CONTAINER" zkCli.sh -server "$ZK_SERVER"
}

case "$ACTION" in
  create-a) zk_cli "create /a ''" ;;
  delete-a) zk_cli "delete /a" ;;
  add-child) zk_cli "create /a/$CHILD_NAME ''" ;;
  delete-child) zk_cli "delete /a/$CHILD_NAME" ;;
  list) zk_cli "ls /a" "get /a" ;;
  full-test)
    echo "=== Full integration test ==="
    zk_cli "delete /a/child2" "delete /a" 2>/dev/null || true
    sleep 2
    echo "Creating /a..."
    zk_cli "create /a ''"
    sleep 3
    echo "Adding children..."
    zk_cli "create /a/child1 'data1'" "create /a/child2 'data2'"
    sleep 2
    zk_cli "ls /a"
    sleep 2
    echo "Deleting child1..."
    zk_cli "delete /a/child1"
    sleep 2
    echo "Deleting /a..."
    zk_cli "delete /a/child2" "delete /a"
    echo "Done. Check http://localhost:8080 and http://localhost:9090"
    ;;
  *)
    echo "Unknown action: $ACTION"
    exit 1
    ;;
esac
