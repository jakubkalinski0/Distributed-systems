import argparse
import socket
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientInfo:
    nick: str
    peer_ip: str
    peer_tcp_port: int
    conn: socket.socket


class ChatServer:
    def __init__(self, bind: str, port: int) -> None:
        self.bind = bind
        self.port = port
        self._lock = threading.Lock()
        self._clients: dict[socket.socket, ClientInfo] = {}

    def _broadcast_tcp(self, line: str, *, exclude: socket.socket | None) -> None:
        data = (line + "\n").encode("utf-8")
        with self._lock:
            targets = [c.conn for c in self._clients.values() if c.conn is not exclude]
        for conn in targets:
            try:
                conn.sendall(data)
            except:
                pass

    def _broadcast_udp(self, udp_sock: socket.socket, payload: bytes, *, exclude_addr: tuple[str, int] | None) -> None:
        with self._lock:
            targets = [(c.peer_ip, c.peer_tcp_port) for c in self._clients.values()]
        for addr in targets:
            if exclude_addr is not None and addr == exclude_addr:
                continue
            try:
                udp_sock.sendto(payload, addr)
            except:
                pass

    def _find_nick_by_udp_addr(self, addr: tuple[str, int]) -> str | None:
        ip, port = addr
        with self._lock:
            for c in self._clients.values():
                if c.peer_ip == ip and c.peer_tcp_port == port:
                    return c.nick
        return None

    def _handle_client(self, conn: socket.socket, peer: tuple[str, int]) -> None:
        peer_ip, peer_port = peer[0], int(peer[1])
        nick = f"nick_{peer_port}"
        
        f = conn.makefile("r", encoding="utf-8", newline="\n")
        first = f.readline().rstrip("\n")
        if first.startswith("NICK "):
            nick = first[5:].strip()

        info = ClientInfo(nick=nick, peer_ip=peer_ip, peer_tcp_port=peer_port, conn=conn)
        with self._lock:
            self._clients[conn] = info

        print(f"[TCP] connected {nick} from {peer_ip}:{peer_port}")
        self._broadcast_tcp(f"*** {nick} joined ***", exclude=conn)

        try:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.rstrip("\n")
                if not line:
                    continue
                self._broadcast_tcp(f"{nick}: {line}", exclude=conn)
        except:
            pass
        
        with self._lock:
            self._clients.pop(conn)
        conn.close()
        print(f"[TCP] disconnected {nick} from {peer_ip}:{peer_port}")
        self._broadcast_tcp(f"*** {nick} left ***", exclude=None)

    def _udp_loop(self) -> None:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind((self.bind, self.port))
        print(f"[UDP] listening on {self.bind}:{self.port}")

        while True:
            data, addr = udp_sock.recvfrom(65535)
            nick = self._find_nick_by_udp_addr((addr[0], addr[1])) or "unknown"
            text = data.decode("utf-8")
            print(f"[UDP] from {addr[0]}:{addr[1]} nick={nick!r}")
            payload = f"[UDP] {nick}: {text}".encode("utf-8")
            self._broadcast_udp(udp_sock, payload, exclude_addr=(addr[0], addr[1]))

    def serve_forever(self) -> None:
        threading.Thread(target=self._udp_loop, daemon=True).start()

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

