import socket
import sys

def connect_to_tcp_socket(host: str, port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print(f"Connected to {host}:{port}")
        s.sendall(b"Hello, server!")  # Send a message
        data = s.recv(1024)  # Receive up to 1024 bytes
        print(f"Received: {data.decode()}")

connect_to_tcp_socket(sys.argv[1], int(sys.argv[2]))