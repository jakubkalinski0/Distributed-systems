# Lab 7 — ZooKeeper Watcher Application

Java application using **Apache ZooKeeper 3.8.4** watch APIs to monitor znode `/a`, launch/stop an external graphical application, display child-count notifications, and visualize the subtree in a browser GUI.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Compose (lab7_zookeeper)                              │
│  zk1 ─┬─ zk2 ─┬─ zk3     (3-node ensemble, ZK 3.8.4)      │
│       └───────┴───────► watcher-app :8080                    │
│                              │                               │
│                              ├─► Web GUI (notifications)     │
│                              └─► docker start/stop           │
│                                   external-gui :9090         │
└─────────────────────────────────────────────────────────────┘
```

| Component | Role |
|-----------|------|
| `zk1`, `zk2`, `zk3` | Replicated ZooKeeper 3.8.4 ensemble |
| `watcher-app` | ZK client, watch handler, Web GUI, process manager |
| `external-gui` | Containerized external graphical app (nginx + HTML) |
| Browser `@ :8080` | Live status, toast notifications, tree view |

### Watch behavior

1. **Existence watch on `/a`** — launch external app on create; stop on delete; re-register watch after each event.
2. **Children watch on `/a`** — on child change, show notification with current count and refresh tree.
3. **Tree visualization** — recursive `getChildren` + `getData` under `/a`, pushed via WebSocket.
4. **Reconnection** — on `SyncConnected` + `None`, re-sync state and re-register watches.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Ports free: `2181–2183`, `8080`, `9090`
- For **host mode**: Java 17+, Maven 3.9+

Verify Docker before starting:

```powershell
.\scripts\verify-docker.ps1
```

## Quick start (Docker)

```powershell
cd Lab7_zookeeper
docker compose up -d --build
```

Open:

- **Watcher GUI:** http://localhost:8080
- **External app (when /a exists):** http://localhost:9090

## Testing

### Automated script

```powershell
.\scripts\test-zk-ops.ps1 -Action full-test
```

Or on Linux/macOS:

```bash
chmod +x scripts/test-zk-ops.sh
./scripts/test-zk-ops.sh full-test
```

### Manual zkCli

```powershell
docker exec -it zk1 zkCli.sh -server localhost:2181
```

```
create /a ""
create /a/child1 "hello"
create /a/child2 "world"
ls /a
delete /a/child1
delete /a/child2
delete /a
```

### Failover test

```powershell
docker stop zk2
# create /a and children via zkCli — watcher reconnects via zk1/zk3
docker start zk2
```

### API

```powershell
Invoke-RestMethod http://localhost:8080/api/state
```

## Host mode (Windows Calculator)

Run only the ZK cluster in Docker, watcher on the host:

```powershell
docker compose up -d zk1 zk2 zk3
cd watcher-app
mvn package -DskipTests
java -jar target/zk-watcher-app-1.0.0.jar `
  --zk-connect localhost:2181,localhost:2182,localhost:2183 `
  --external-app-mode process `
  --external-app calc.exe
```

Default external app on Windows without `--external-app` is `calc.exe`.

## CLI options

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--zk-connect` | `ZK_CONNECT_STRING` | `localhost:2181` | ZK ensemble connect string |
| `--zk-root` | `ZK_ROOT_PATH` | `/a` | Watched znode path |
| `--session-timeout` | `ZK_SESSION_TIMEOUT_MS` | `30000` | Session timeout (ms) |
| `--http-port` | `HTTP_PORT` | `8080` | Web GUI port |
| `--external-app-mode` | `EXTERNAL_APP_MODE` | `process` | `process` or `docker` |
| `--external-app` | — | OS default | Command for ProcessBuilder |
| `--external-docker-container` | `EXTERNAL_DOCKER_CONTAINER` | `external-gui` | Container name (docker mode) |

## Build (without Docker)

```powershell
cd watcher-app
mvn package -DskipTests
java -jar target/zk-watcher-app-1.0.0.jar --help
```

## Project structure

```
Lab7_zookeeper/
├── docker-compose.yml
├── external-gui/html/          # External app page
├── scripts/
│   ├── verify-docker.ps1
│   ├── test-zk-ops.ps1
│   └── test-zk-ops.sh
├── watcher-app/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/java/pl/distributed/zkwatcher/
│       ├── WatcherApp.java
│       ├── config/AppConfig.java
│       ├── zk/NodeAWatcher.java, TreeBuilder.java
│       ├── process/ProcessManager.java, DockerProcessLauncher.java
│       ├── web/WebServer.java, EventBroadcaster.java
│       └── model/TreeNode.java, AppState.java
└── apache-zookeeper-3.8.4-bin/ # Bundled reference/docs
```

## Validation results

Tested on Windows 10 with Docker Desktop (WSL2 backend), June 2026.

| Requirement | Result |
|-------------|--------|
| ZK 3.8.4 APIs | Pass — `org.apache.zookeeper:zookeeper:3.8.4` |
| 3-node replicated ensemble | Pass — `zk1,zk2,zk3` healthy |
| Watch `/a` creation → launch app | Pass — `external-gui` started via Docker API |
| Watch `/a` deletion → stop app | Pass — container stopped |
| Child added → notification | Pass — logs: `Child added — total children: N` |
| Tree visualization | Pass — `/api/state` returns nested tree JSON |
| Web GUI | Pass — http://localhost:8080 |
| Failover (stop zk2) | Pass — operations continue via remaining nodes |
| Maven build | Pass |
| Docker compose up | Pass |

## Assumptions

- **Language:** Java (best fit for ZK 3.8.4; matches lab materials).
- **GUI:** Browser-based (works in Docker; satisfies graphical notifications + tree view).
- **Docker external app:** Linux containers cannot launch native Windows `calc.exe`; Docker mode uses the `external-gui` companion container. Host mode uses `calc.exe` on Windows.
- **One-shot watches:** Re-registered after every event and on reconnect (`SyncConnected` + `EventType.None` only).

## Architectural decisions

- **Javalin** for embedded HTTP + WebSocket (lightweight, Docker-friendly).
- **Gson** for WebSocket payloads; **Jackson** for REST `/api/state`.
- **Docker CLI** copied into watcher image to control `external-gui` via mounted `/var/run/docker.sock`.
- **Official `zookeeper:3.8.4` image** for the ensemble instead of the local tarball (same version, simpler ops).

## Stop / cleanup

```powershell
docker compose down
```
