import socket

serverIP = "127.0.0.1"
serverPort = 9010
msg = "żółta gęś"

print('PYTHON UDP CLIENT')

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
    client.settimeout(2.0)
    client.sendto(msg.encode("utf-8"), (serverIP, serverPort))
    print("sent message: " + msg)

    buff, address = client.recvfrom(1024)
    print("received response: " + buff.decode("utf-8", errors="replace"))