import argparse
import socket
import threading


def tcp_receiver(sock: socket.socket) -> None:
    f = sock.makefile("r", encoding="utf-8", newline="\n")
    while True:
        line = f.readline()
        if not line:
            break
        print(line.rstrip("\n"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9020)
    parser.add_argument("--nick", default="user")
    args = parser.parse_args()

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.connect((args.host, args.port))
    tcp_sock.sendall(f"NICK {args.nick}\n".encode("utf-8"))

    threading.Thread(target=tcp_receiver, args=(tcp_sock,), daemon=True).start()

    while True:
        line = input()
        if line == "/quit":
            break
        tcp_sock.sendall((line + "\n").encode("utf-8"))
    
    tcp_sock.close()


if __name__ == "__main__":
    main()
