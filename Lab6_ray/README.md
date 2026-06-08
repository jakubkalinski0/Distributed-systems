# Lab 6: Ray

Distributed computing with Ray. Tier 1 covers tasks, actors, and the object store in Jupyter. Tier 2 adds a miniature HDFS-like storage layer on a Ray cluster.

## Tier 1: Ray fundamentals

### Requirements

- Docker Desktop (recommended; Ray runs inside the image)
- Port **8888** free on the host

### Run with Docker

```powershell
cd Lab6_ray
docker compose up -d
docker compose logs -f jupyter
```

Open **http://localhost:8888** (token: `raylab`) and run `notebook/lab-ray.ipynb`.

In the `ray.init` cell set:

```python
USE_REMOTE_CLUSTER = False
```

Then use **Kernel → Restart Kernel and Run All Cells**. Tier 1 is Part 7 (merge sort) and Part 8 (Monte Carlo pi).

### Local Python (optional)

Ray wheels may not exist for every Windows Python version. Use Python 3.10 to 3.12 if running outside Docker:

```powershell
cd Lab6_ray
py -3.10 -m pip install -r requirements.txt
py -3.10 -m ipykernel install --user --name ray-lab
```

### Stop

```powershell
docker compose down
```

## Tier 2: Ray HDFS

### Quick start (single node)

```powershell
cd Lab6_ray
docker compose up -d
```

Open `notebook/tier2-hdfs.ipynb`, set `USE_REMOTE_CLUSTER = False`, and run all cells.

### Distributed cluster (head + worker)

Use `docker-compose.tier2.yaml` when available:

```powershell
cd Lab6_ray
docker compose -f docker-compose.tier2.yaml up -d
```

- Jupyter: **http://localhost:8889** (token: `raylab`)
- Ray Dashboard: **http://localhost:8265**
- In the notebook: `USE_REMOTE_CLUSTER = True` and `RAY_ADDRESS = "ray://ray-head:10001"`

After changing files under `hdfs/`, restart compose so head and worker pick up the mount.

### Layout

| Path | Role |
|------|------|
| `hdfs/data_node.py` | DataNode actor (block storage) |
| `hdfs/name_node.py` | NameNode actor (metadata) |
| `hdfs/client.py` | Client (direct read/write to DataNodes) |
| `notebook/tier2-hdfs.ipynb` | CRUD tests, failure handling, bonus API |

### Stop

```powershell
docker compose -f docker-compose.tier2.yaml down
```

## Common issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: ray` | Run the notebook inside Docker, not a local kernel without Ray |
| Old AWS cluster link / timeout | Set `USE_REMOTE_CLUSTER = False` |
| `ModuleNotFoundError: hdfs` on actors | Restart compose after editing `hdfs/` |
| Head container exits immediately | Use the current compose file and check `docker compose logs ray-head` |
| Worker `WrongClusterID` | Full reset: `docker compose -f docker-compose.tier2.yaml down` then `up -d` |
