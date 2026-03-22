import argparse
import socket
import threading

from multicast_utils import create_multicast_listener, create_multicast_sender


def tcp_receiver(sock: socket.socket) -> None:
    f = sock.makefile("r", encoding="utf-8", newline="\n")
    while True:
        line = f.readline()
        if not line:
            break
        print(line.rstrip("\n"))


def udp_receiver(sock: socket.socket) -> None:
    while True:
        data, addr = sock.recvfrom(65535)
        text = data.decode("utf-8")
        print(text)


def multicast_receiver(sock: socket.socket) -> None:
    while True:
        data, addr = sock.recvfrom(65535)
        text = data.decode("utf-8")
        print(f"[MCAST] {text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9020)
    parser.add_argument("--nick", default="user")
    parser.add_argument("--local-port", type=int, default=0)
    parser.add_argument("--multicast-group", default="239.255.0.1")
    parser.add_argument("--multicast-ttl", type=int, default=1)
    args = parser.parse_args()

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if args.local_port != 0:
        tcp_sock.bind(("0.0.0.0", args.local_port))
    tcp_sock.connect((args.host, args.port))
    local_port = int(tcp_sock.getsockname()[1])
    tcp_sock.sendall(f"NICK {args.nick}\n".encode("utf-8"))

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", local_port))

    threading.Thread(target=tcp_receiver, args=(tcp_sock,), daemon=True).start()
    threading.Thread(target=udp_receiver, args=(udp_sock,), daemon=True).start()

    mcast_listen = create_multicast_listener(args.multicast_group, args.port)
    threading.Thread(target=multicast_receiver, args=(mcast_listen,), daemon=True).start()
    mcast_send = create_multicast_sender(args.multicast_ttl)

    while True:
        line = input()
        if line == "/quit":
            break
        if line.startswith("U "):
            msg = line[2:]
            udp_sock.sendto(msg.encode("utf-8"), (args.host, args.port + 1))
        elif line.startswith("M "):
            msg = line[2:]
            mcast_send.sendto(f"{args.nick}: {msg}".encode("utf-8"), (args.multicast_group, args.port))
        else:
            tcp_sock.sendall((line + "\n").encode("utf-8"))
    
    tcp_sock.close()
    udp_sock.close()
    mcast_listen.close()


if __name__ == "__main__":
    main()

