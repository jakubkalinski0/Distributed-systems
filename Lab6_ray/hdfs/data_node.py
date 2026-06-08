"""Storage-node actor — holds block chunks only (no artifact metadata)."""

from __future__ import annotations

import ray


@ray.remote(
    num_cpus=0.25,
    max_restarts=1,
    max_task_retries=1,
    scheduling_strategy="SPREAD",
)
class DataNode:
    """HDFS DataNode: stores blocks; NameNode assigns placement."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.status = "ALIVE"
        self.blocks: dict[str, bytes] = {}

    def put_block(self, block_id: str, data: bytes) -> dict:
        if self.status != "ALIVE":
            raise RuntimeError(f"DataNode {self.node_id} is {self.status}")
        self.blocks[block_id] = bytes(data)
        return {"node_id": self.node_id, "block_id": block_id, "size": len(data)}

    def get_block(self, block_id: str) -> bytes:
        if block_id not in self.blocks:
            raise KeyError(f"block {block_id} not on {self.node_id}")
        return self.blocks[block_id]

    def delete_block(self, block_id: str) -> bool:
        if block_id in self.blocks:
            del self.blocks[block_id]
            return True
        return False

    def list_blocks(self) -> list[dict]:
        return [
            {"block_id": bid, "size_bytes": len(data)}
            for bid, data in sorted(self.blocks.items())
        ]

    def get_status(self) -> dict:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "block_count": len(self.blocks),
        }

    def simulate_failure(self) -> dict:
        """Mark node dead — rejects new writes (PDF failure scenario)."""
        self.status = "DEAD"
        return self.get_status()


DATA_NODE_CLASS = DataNode
