import socket

serverIP = "127.0.0.1"
serverPort = 9013
msg_bytes = (300).to_bytes(4, byteorder='little')

print('PYTHON UDP CLIENT')
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
    client.settimeout(2.0)
    client.sendto(msg_bytes, (serverIP, serverPort))
    print("sent number: " + str(int.from_bytes(msg_bytes, byteorder='little')))

    buff, address = client.recvfrom(1024)
    if len(buff) < 4:
        raise ValueError("Expected 4 bytes response, got " + str(len(buff)))
    received = int.from_bytes(buff[:4], byteorder='little')
    print("received number: " + str(received))