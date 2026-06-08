"""Quick smoke test: python hdfs/smoke_test.py (inside Docker with PYTHONPATH=/home/ray)."""
import sys

sys.path.insert(0, "/home/ray")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import ray

from hdfs.constants import BLOCK_SIZE
from hdfs.client import ArtifactClient
from hdfs.data_node import DataNode
from hdfs.name_node import NameNode


def main():
    ray.init(ignore_reinit_error=True)
    handles = {f"dn-{i}": DataNode.remote(f"dn-{i}") for i in range(3)}
    nn = NameNode.remote(block_size=BLOCK_SIZE)
    ray.get(nn.register_data_nodes.remote(list(handles.keys())))
    for k, h in handles.items():
        ray.get(nn.set_data_node_handle.remote(k, h))
    c = ArtifactClient(nn, handles)
    c.create("t", "hello" * 100, replication_factor=2)
    assert c.get("t") == "hello" * 100
    c.update("t", "hello" * 99 + "X")
    c.delete("t")
    print("smoke OK")
    ray.shutdown()


if __name__ == "__main__":
    main()
