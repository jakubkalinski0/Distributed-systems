"""Name-node actor — metadata only; no artifact payload storage."""

from __future__ import annotations

from typing import Any

import ray


def _num_blocks(content_len: int, block_size: int) -> int:
    if content_len == 0:
        return 1
    return (content_len + block_size - 1) // block_size


def _pick_replica_nodes(
    alive: list[str], block_index: int, replication_factor: int
) -> list[str]:
    if len(alive) < replication_factor:
        raise RuntimeError(
            f"Need {replication_factor} alive DataNodes, have {len(alive)}"
        )
    nodes = []
    for r in range(replication_factor):
        nodes.append(alive[(block_index + r) % len(alive)])
    return nodes


@ray.remote
class NameNode:
    """HDFS NameNode: global metadata; clients write blocks directly to DataNodes."""

    def __init__(self, block_size: int = 256):
        self.block_size = block_size
        self.artifacts: dict[str, dict[str, Any]] = {}
        # node_id -> {"handle": ActorHandle, "status": "ALIVE"|"DEAD"}
        self.data_nodes: dict[str, dict[str, Any]] = {}

    def register_data_nodes(self, node_ids: list[str]) -> dict:
        """Register node ids; handles are wired separately via set_data_node_handle."""
        for nid in node_ids:
            if nid not in self.data_nodes:
                self.data_nodes[nid] = {"handle": None, "status": "ALIVE"}
        return {"registered": node_ids, "count": len(self.data_nodes)}

    def set_data_node_handle(self, node_id: str, handle) -> None:
        if node_id not in self.data_nodes:
            self.data_nodes[node_id] = {"handle": handle, "status": "ALIVE"}
        else:
            self.data_nodes[node_id]["handle"] = handle

    def _alive_nodes(self) -> list[str]:
        return [
            nid
            for nid, info in self.data_nodes.items()
            if info.get("status") == "ALIVE"
        ]

    def _handle(self, node_id: str):
        info = self.data_nodes.get(node_id)
        if not info or info["handle"] is None:
            raise RuntimeError(f"No handle for DataNode {node_id}")
        return info["handle"]

    def plan_create(
        self, name: str, content_len: int, replication_factor: int = 2
    ) -> dict:
        if name in self.artifacts:
            raise ValueError(f"Artifact {name!r} already exists")
        alive = self._alive_nodes()
        nblocks = _num_blocks(content_len, self.block_size)
        blocks = []
        for i in range(nblocks):
            block_id = f"{name}::block::{i}"
            replicas = _pick_replica_nodes(alive, i, replication_factor)
            blocks.append(
                {
                    "block_index": i,
                    "block_id": block_id,
                    "replicas": replicas,
                }
            )
        return {
            "name": name,
            "content_len": content_len,
            "block_size": self.block_size,
            "replication_factor": replication_factor,
            "blocks": blocks,
        }

    def commit_create(self, plan: dict) -> dict:
        name = plan["name"]
        if name in self.artifacts:
            raise ValueError(f"Artifact {name!r} already exists")
        self.artifacts[name] = {
            "size": plan["content_len"],
            "block_size": plan["block_size"],
            "replication_factor": plan["replication_factor"],
            "blocks": [
                {
                    "block_index": b["block_index"],
                    "block_id": b["block_id"],
                    "replicas": list(b["replicas"]),
                }
                for b in plan["blocks"]
            ],
        }
        return {"committed": name, "blocks": len(plan["blocks"])}

    def get_locations(self, name: str) -> dict:
        if name not in self.artifacts:
            raise KeyError(f"Artifact {name!r} not found")
        art = self.artifacts[name]
        return {
            "name": name,
            "size": art["size"],
            "block_size": art["block_size"],
            "blocks": art["blocks"],
        }

    def plan_delete(self, name: str) -> dict:
        if name not in self.artifacts:
            raise KeyError(f"Artifact {name!r} not found")
        art = self.artifacts[name]
        deletions = []
        for b in art["blocks"]:
            for node_id in b["replicas"]:
                deletions.append({"node_id": node_id, "block_id": b["block_id"]})
        return {"name": name, "deletions": deletions}

    def commit_delete(self, name: str) -> dict:
        if name not in self.artifacts:
            raise KeyError(f"Artifact {name!r} not found")
        del self.artifacts[name]
        return {"deleted": name}

    def plan_update(self, name: str, new_content: bytes) -> dict:
        """Porównanie blok po bloku ze starą treścią (odczyt z repliki); zwraca tylko zmienione."""
        if name not in self.artifacts:
            raise KeyError(f"Artifact {name!r} not found")
        art = self.artifacts[name]
        old_size = art["size"]
        new_size = len(new_content)
        old_n = _num_blocks(old_size, self.block_size)
        new_n = _num_blocks(new_size, self.block_size)
        rf = art["replication_factor"]
        alive = self._alive_nodes()

        old_blocks = art["blocks"]
        changed = []
        unchanged_ids = set()

        for i in range(max(old_n, new_n)):
            start = i * self.block_size
            new_chunk = new_content[start : start + self.block_size]

            if i < old_n and i < new_n:
                block_id = old_blocks[i]["block_id"]
                old_chunk = self._read_block_from_replica(old_blocks[i])
                if old_chunk == new_chunk:
                    unchanged_ids.add(block_id)
                    continue
                replicas = list(old_blocks[i]["replicas"])
            elif i < new_n:
                block_id = f"{name}::block::{i}"
                replicas = _pick_replica_nodes(alive, i, rf)
            else:
                continue

            changed.append(
                {
                    "block_index": i,
                    "block_id": block_id,
                    "replicas": replicas,
                    "data": new_chunk,
                    "is_new_block": i >= old_n,
                }
            )

        trailing_delete = []
        if new_n < old_n:
            for i in range(new_n, old_n):
                b = old_blocks[i]
                for node_id in b["replicas"]:
                    trailing_delete.append(
                        {"node_id": node_id, "block_id": b["block_id"]}
                    )

        return {
            "name": name,
            "new_size": new_size,
            "changed_blocks": changed,
            "unchanged_block_ids": list(unchanged_ids),
            "trailing_deletions": trailing_delete,
            "replication_factor": rf,
        }

    def commit_update(self, name: str, new_size: int, changed_blocks: list) -> dict:
        if name not in self.artifacts:
            raise KeyError(f"Artifact {name!r} not found")
        art = self.artifacts[name]
        rf = art["replication_factor"]
        alive = self._alive_nodes()

        block_by_index = {b["block_index"]: b for b in art["blocks"]}

        for ch in changed_blocks:
            idx = ch["block_index"]
            entry = {
                "block_index": idx,
                "block_id": ch["block_id"],
                "replicas": list(ch["replicas"]),
            }
            block_by_index[idx] = entry

        new_n = _num_blocks(new_size, self.block_size)
        new_block_list = []
        for i in range(new_n):
            if i in block_by_index:
                new_block_list.append(block_by_index[i])
            else:
                block_id = f"{name}::block::{i}"
                replicas = _pick_replica_nodes(alive, i, rf)
                new_block_list.append(
                    {
                        "block_index": i,
                        "block_id": block_id,
                        "replicas": replicas,
                    }
                )

        art["size"] = new_size
        art["blocks"] = new_block_list
        return {"updated": name, "size": new_size, "blocks": len(new_block_list)}

    def _read_block_from_replica(self, block_meta: dict) -> bytes:
        for node_id in block_meta["replicas"]:
            info = self.data_nodes.get(node_id)
            if not info or info["status"] != "ALIVE":
                continue
            try:
                return ray.get(
                    self._handle(node_id).get_block.remote(block_meta["block_id"])
                )
            except Exception:
                continue
        raise RuntimeError(f"No readable replica for {block_meta['block_id']}")

    def report_node_failure(self, node_id: str) -> dict:
        """Oznacz węzeł jako DEAD i skopiuj brakujące repliki z żywych DataNodes."""
        if node_id not in self.data_nodes:
            raise KeyError(f"Unknown DataNode {node_id}")
        self.data_nodes[node_id]["status"] = "DEAD"
        try:
            ray.get(self._handle(node_id).simulate_failure.remote())
        except Exception:
            pass

        replications = []
        rf = None
        for name, art in self.artifacts.items():
            rf = art["replication_factor"]
            for b in art["blocks"]:
                replicas = b["replicas"]
                if node_id not in replicas:
                    continue
                alive_reps = [
                    n
                    for n in replicas
                    if self.data_nodes.get(n, {}).get("status") == "ALIVE"
                ]
                while len(alive_reps) < art["replication_factor"]:
                    if not alive_reps:
                        raise RuntimeError(
                            f"No alive replica left for block {b['block_id']}"
                        )
                    source = alive_reps[0]
                    data = ray.get(
                        self._handle(source).get_block.remote(b["block_id"])
                    )
                    targets = [
                        n
                        for n in self._alive_nodes()
                        if n not in alive_reps
                    ]
                    if not targets:
                        raise RuntimeError("No target DataNode for re-replication")
                    target = targets[0]
                    ray.get(
                        self._handle(target).put_block.remote(b["block_id"], data)
                    )
                    alive_reps.append(target)
                    replications.append(
                        {
                            "block_id": b["block_id"],
                            "from": source,
                            "to": target,
                            "artifact": name,
                        }
                    )
                b["replicas"] = alive_reps[: art["replication_factor"]]

        return {
            "failed_node": node_id,
            "replications": replications,
        }

    def list_artifacts(self) -> list[dict]:
        return [
            {
                "name": name,
                "size": art["size"],
                "blocks": len(art["blocks"]),
                "replication_factor": art["replication_factor"],
            }
            for name, art in sorted(self.artifacts.items())
        ]

    def list_cluster_state(self) -> dict:
        nodes = []
        for nid, info in sorted(self.data_nodes.items()):
            st = {"node_id": nid, "status": info["status"]}
            if info["handle"] is not None and info["status"] == "ALIVE":
                try:
                    st["remote"] = ray.get(info["handle"].get_status.remote())
                except Exception as e:
                    st["remote_error"] = str(e)
            nodes.append(st)
        return {
            "artifacts": self.list_artifacts(),
            "data_nodes": nodes,
        }


NAME_NODE_CLASS = NameNode
