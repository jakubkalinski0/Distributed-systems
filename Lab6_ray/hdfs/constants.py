"""Stałe HDFS — osobny moduł, żeby uniknąć cyklicznego importu hdfs <-> client."""

BLOCK_SIZE = 256
DEFAULT_REPLICATION_FACTOR = 2
