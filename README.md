# Distributed Systems

Solutions and materials for a university distributed systems course. Each lab lives in its own top-level folder and can be run independently.

## Labs

### Lab 1: TCP and UDP Sockets

Socket programming in Python: multithreaded TCP chat, UDP messaging, and UDP multicast.

| Part | Folder | Topic |
|------|--------|-------|
| Home task 1 | [Task_1_tcp_chat](Lab1_TCP_and_UDP_sockets/Home%20Tasks/Task_1_tcp_chat/) | TCP chat server and client |
| Home task 2 | [Task_2_tcp_udp](Lab1_TCP_and_UDP_sockets/Home%20Tasks/Task_2_tcp_udp/) | TCP chat plus UDP channel |
| Home task 3 | [Task_3_tcp_udp_multicast](Lab1_TCP_and_UDP_sockets/Home%20Tasks/Task_3_tcp_udp_multicast/) | TCP, UDP, and multicast |
| In-class | [Lab tasks](Lab1_TCP_and_UDP_sockets/Lab%20tasks/) | Java and Python UDP exercises |

### Lab 2: RESTful API

HTTP APIs with FastAPI: in-class Doodle voting service and a home task that compares country data from public REST APIs.

| Part | Folder | Topic |
|------|--------|-------|
| In-class | [Lab task](Lab2_RESTful_API/Lab%20task/) | Doodle voting API |
| Home task | [country_info_comparator](Lab2_RESTful_API/Home%20task/country_info_comparator/) | Country comparison service |

### Lab 3 and 4: Middleware Technologies

Distributed middleware with ZeroC Ice and gRPC. The home task models a smart building with devices, two Java servers, and Python clients.

| Part | Folder | Topic |
|------|--------|-------|
| Home task | [project](Lab3&4_middleware/Home%20Tasks/project/) | Ice and gRPC smarthome system |

### Lab 5: RabbitMQ (Message-Oriented Middleware)

A RabbitMQ broker connects space agencies and carriers. Agencies publish orders; carriers compete for work; confirmations and admin broadcasts use dedicated exchanges and queues.

| Part | Folder | Topic |
|------|--------|-------|
| Home task | [Home Task](Lab5_RabbitMQ/Home%20Task/) | Agencies, carriers, and admin CLI |
| In-class | [Lab task](Lab5_RabbitMQ/Lab%20task/) | Java producer and consumer exercises |

### Lab 6: Ray

Distributed computing with Ray. Tier 1 covers tasks, actors, and object store usage in Jupyter. Tier 2 implements a miniature HDFS-like storage layer on a Ray cluster.

| Part | Folder | Topic |
|------|--------|-------|
| Tier 1 | [notebook/lab-ray.ipynb](Lab6_ray/notebook/lab-ray.ipynb) | Ray fundamentals |
| Tier 2 | [hdfs](Lab6_ray/hdfs/) and [tier2-hdfs.ipynb](Lab6_ray/notebook/tier2-hdfs.ipynb) | Distributed artifact storage |

See [Lab6_ray/README.md](Lab6_ray/README.md) for Docker setup.

### Lab 7: Apache ZooKeeper

A Java watcher application monitors znode `/a` in a three-node ZooKeeper ensemble. It launches an external graphical app when `/a` is created, shows child-count notifications, and renders the subtree in a browser GUI.

| Part | Folder | Topic |
|------|--------|-------|
| Application | [watcher-app](Lab7_zookeeper/watcher-app/) | ZK client, process manager, web UI |
| Infrastructure | [docker-compose.yml](Lab7_zookeeper/docker-compose.yml) | ZK ensemble and companion containers |

See [Lab7_zookeeper/README.md](Lab7_zookeeper/README.md) for build, test, and run instructions.

## Requirements

Common tooling across labs:

- Python 3.11+ (Labs 1, 2, 5, 6)
- Java 17+ and Maven 3.9+ (Labs 3, 4, 5, 7)
- Docker and Docker Compose (Labs 5, 6, 7)

Install Python dependencies from each lab's `requirements.txt` or create a virtual environment before running.

## Repository layout

```
Lab1_TCP_and_UDP_sockets/
Lab2_RESTful_API/
Lab3&4_middleware/
Lab5_RabbitMQ/
Lab6_ray/
Lab7_zookeeper/
```

Each lab folder contains its own README with detailed run commands where applicable.
