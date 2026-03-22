import argparse
import socket
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientInfo:
    nick: str
    conn: socket.socket


class ChatServer:
    def __init__(self, bind: str, port: int) -> None:
        self.bind = bind
        self.port = port
        self._lock = threading.Lock()
        self._clients: dict[socket.socket, ClientInfo] = {}

    def _broadcast(self, line: str, *, exclude: socket.socket | None) -> None:
        data = (line + "\n").encode("utf-8")
        with self._lock:
            targets = [c.conn for c in self._clients.values() if c.conn is not exclude]
        for conn in targets:
            try:
                conn.sendall(data)
            except:
                pass

    def _handle_client(self, conn: socket.socket, peer: tuple[str, int]) -> None:
        peer_ip, peer_port = peer[0], int(peer[1])
        nick = f"nick_{peer_port}"
        
        f = conn.makefile("r", encoding="utf-8", newline="\n")
        first_line = f.readline().rstrip("\n")
        if first_line.startswith("NICK "):
            nick = first_line[5:].strip()

        with self._lock:
            self._clients[conn] = ClientInfo(nick=nick, conn=conn)

        print(f"[TCP] connected {nick} from {peer_ip}:{peer_port}")
        self._broadcast(f"*** {nick} joined ***", exclude=conn)

        try:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.rstrip("\n")
                if not line:
                    continue
                self._broadcast(f"{nick}: {line}", exclude=conn)
        except:
            pass
        
        with self._lock:
            self._clients.pop(conn)
        conn.close()
        print(f"[TCP] disconnected {nick} from {peer_ip}:{peer_port}")
        self._broadcast(f"*** {nick} left ***", exclude=None)

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.bind, self.port))
            server_sock.listen()
            print(f"[TCP] listening on {self.bind}:{self.port}")

            while True:
                conn, peer = server_sock.accept()
                t = threading.Thread(target=self._handle_client, args=(conn, peer), daemon=True)
                t.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9020)
    args = parser.parse_args()

    ChatServer(args.bind, args.port).serve_forever()


if __name__ == "__main__":
    main()

