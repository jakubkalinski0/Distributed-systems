"""Klient po stronie drivera — zapis/odczyt bloków bezpośrednio na DataNodes.

NameNode dostaje tylko plany i commity (metadane); treść artefaktu nigdy
nie trafia do NameNode (wymóg PDF).
"""

from __future__ import annotations

import ray

from hdfs.constants import BLOCK_SIZE, DEFAULT_REPLICATION_FACTOR


class ArtifactClient:
    """API użytkownika: create, get, update, delete + listowanie stanu klastra."""

    def __init__(
        self,
        name_node,
        data_node_handles: dict[str, object],
        block_size: int = BLOCK_SIZE,
    ):
        self.name_node = name_node
        self.data_nodes = data_node_handles
        self.block_size = block_size

    def _dn(self, node_id: str):
        if node_id not in self.data_nodes:
            raise KeyError(f"Unknown DataNode {node_id}")
        return self.data_nodes[node_id]

    @staticmethod
    def _split(content: bytes, block_size: int) -> list[bytes]:
        if not content:
            return [b""]
        chunks = []
        for i in range(0, len(content), block_size):
            chunks.append(content[i : i + block_size])
        return chunks

    def create(
        self,
        name: str,
        content: str | bytes,
        replication_factor: int = DEFAULT_REPLICATION_FACTOR,
    ) -> dict:
        """plan_create → put_block na każdej replice → commit_create."""
        data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        plan = ray.get(
            self.name_node.plan_create.remote(
                name, len(data), replication_factor
            )
        )
        chunks = self._split(data, plan["block_size"])
        puts = []
        for block, chunk in zip(plan["blocks"], chunks):
            for node_id in block["replicas"]:
                puts.append(
                    self._dn(node_id).put_block.remote(block["block_id"], chunk)
                )
        ray.get(puts)
        return ray.get(self.name_node.commit_create.remote(plan))

    def get(self, name: str) -> str:
        """Skleja bloki z pierwszej dostępnej repliki każdego chunka."""
        loc = ray.get(self.name_node.get_locations.remote(name))
        parts = []
        for block in loc["blocks"]:
            chunk = None
            for node_id in block["replicas"]:
                try:
                    chunk = ray.get(
                        self._dn(node_id).get_block.remote(block["block_id"])
                    )
                    break
                except Exception:
                    continue
            if chunk is None:
                raise RuntimeError(
                    f"Cannot read block {block['block_id']} for {name}"
                )
            parts.append(chunk)
        raw = b"".join(parts)
        return raw[: loc["size"]].decode("utf-8")

    def update(self, name: str, new_content: str | bytes) -> dict:
        """Tylko zmienione bloki (diff w NameNode.plan_update) — nie delete+create całości."""
        data = (
            new_content.encode("utf-8")
            if isinstance(new_content, str)
            else bytes(new_content)
        )
        plan = ray.get(self.name_node.plan_update.remote(name, data))
        puts = []
        for ch in plan["changed_blocks"]:
            for node_id in ch["replicas"]:
                puts.append(
                    self._dn(node_id).put_block.remote(ch["block_id"], ch["data"])
                )
        if puts:
            ray.get(puts)
        dels = [
            self._dn(d["node_id"]).delete_block.remote(d["block_id"])
            for d in plan["trailing_deletions"]
        ]
        if dels:
            ray.get(dels)
        changed_meta = [
            {
                "block_index": ch["block_index"],
                "block_id": ch["block_id"],
                "replicas": ch["replicas"],
            }
            for ch in plan["changed_blocks"]
        ]
        commit = ray.get(
            self.name_node.commit_update.remote(
                name, plan["new_size"], changed_meta
            )
        )
        return {
            "commit": commit,
            "changed_block_count": len(plan["changed_blocks"]),
            "unchanged_block_ids": plan["unchanged_block_ids"],
        }

    def delete(self, name: str) -> dict:
        plan = ray.get(self.name_node.plan_delete.remote(name))
        refs = [
            self._dn(d["node_id"]).delete_block.remote(d["block_id"])
            for d in plan["deletions"]
        ]
        if refs:
            ray.get(refs)
        return ray.get(self.name_node.commit_delete.remote(name))

    def list_cluster_state(self) -> dict:
        return ray.get(self.name_node.list_cluster_state.remote())

    def list_all_blocks_on_nodes(self) -> dict[str, list]:
        out = {}
        for node_id, handle in self.data_nodes.items():
            try:
                out[node_id] = ray.get(handle.list_blocks.remote())
            except Exception as e:
                out[node_id] = {"error": str(e)}
        return out

    def report_node_failure(self, node_id: str) -> dict:
        return ray.get(self.name_node.report_node_failure.remote(node_id))
