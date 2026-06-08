# Tier 2 — uruchomienie (Ray HDFS, 10 pkt)

## Szybki start — lokalnie (development)

W kontenerze Tier 1 lub lokalnie z Ray:

```powershell
cd Lab6_ray\for-students
docker compose up -d
```

W `tier2-hdfs.ipynb` ustaw `USE_REMOTE_CLUSTER = False`, uruchom **Restart & Run All**.

## Pełne rozproszenie (+1 pkt) — head + worker

```powershell
cd Lab6_ray\for-students
docker compose -f docker-compose.tier2.yaml down
docker compose -f docker-compose.tier2.yaml up -d
```

Po zmianie plików `hdfs/` zrestartuj compose — head i worker muszą mieć mount `./hdfs` (inaczej `ModuleNotFoundError: hdfs` przy aktorach).

**Head `exited with code 1`:** zwykle przez `--node-ip-address` w starej wersji compose — użyj aktualnego pliku (bez tej flagi).

**Ostrzeżenie `The "i" variable is not set`:** stara wersja compose miała pętlę `for i in ...` w YAML — Docker podstawiał `$i`. Aktualny plik używa skryptów `scripts/tier2-ray-*.sh`.

**Head `exited (2)` / `set: pipefail: invalid option`:** skrypty `.sh` zapisane w Windows z CRLF. Compose uruchamia `sed` usuwający `\r`; możesz też przekonwertować lokalnie (LF) albo polegać na `.gitattributes` (`*.sh text eol=lf`).

**Worker: `Failed to connect to GCS` / `WrongClusterID`:** head jeszcze nie gotowy — worker czeka w skrypcie do 4 min. Pełny reset:

```powershell
docker compose -f docker-compose.tier2.yaml down
docker compose -f docker-compose.tier2.yaml up -d
docker compose -f docker-compose.tier2.yaml ps
docker compose -f docker-compose.tier2.yaml logs ray-head --tail 40
docker compose -f docker-compose.tier2.yaml logs ray-worker --tail 20
```

`ray-head` i `ray-worker` powinny być **Up** (pierwszy start heada może trwać 1–3 min).

- Jupyter: **http://localhost:8889** (token: `raylab`)
- Ray Dashboard: **http://localhost:8265**
- W notebooku: `USE_REMOTE_CLUSTER = True` i `RAY_ADDRESS = "ray://ray-head:10001"` (ustawione przez `RAY_ADDRESS` w compose dla Jupyter)

W komórce „Rozproszenie” uruchom `!ray status` — powinny być **2 nody** (head + worker).

## Struktura

| Plik | Opis |
|------|------|
| `hdfs/data_node.py` | Aktor DataNode (bloki) |
| `hdfs/name_node.py` | Aktor NameNode (metadane) |
| `hdfs/client.py` | Klient — zapis/odczyt bezpośrednio na DataNodes |
| `notebook/tier2-hdfs.ipynb` | Testy CRUD + awaria + bonus API |

## Zatrzymanie

```powershell
docker compose -f docker-compose.tier2.yaml down
```
