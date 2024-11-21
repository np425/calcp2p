import socket
import threading
import argparse
import time

BUFFER_SIZE = 1024

def handle_incoming_connections(sock):
    """Listen for and handle incoming connections."""
    sock.listen()
    print(f"Listening on {sock.getsockname()}...")
    conn, addr = sock.accept()
    print(f"Connection established with {addr}")
    while True:
        data = conn.recv(BUFFER_SIZE)
        if not data:
            print(f"Connection closed by {addr}")
            break
        print(f"Received: {data.decode()}")
        conn.sendall(f"Echo: {data.decode()}".encode())
    conn.close()

def connect_to_peer(ip, port):
    """Connect to a peer and send messages."""
    while True:
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((ip, port))
            print(f"Connected to peer at {ip}:{port}")
            break
        except ConnectionRefusedError:
            print(f"Connection to {ip}:{port} failed. Retrying in 2 seconds...")
            time.sleep(2)
    
    while True:
        message = input("Send: ")
        if message.lower() == "exit":
            break
        peer_socket.sendall(message.encode())
        response = peer_socket.recv(BUFFER_SIZE)
        print(f"Response: {response.decode()}")
    peer_socket.close()

def start_listener(ip, port):
    """Start a listener for incoming connections."""
    listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener_socket.bind((ip, port))
    threading.Thread(target=handle_incoming_connections, args=(listener_socket,), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bidirectional TCP Communication")
    parser.add_argument('--host_ip', type=str, required=True, help="Host IP address to bind the listener")
    parser.add_argument('--host_port', type=int, required=True, help="Host port to bind the listener")
    parser.add_argument('--client_ip', type=str, required=True, help="Client IP address to connect to")
    parser.add_argument('--client_port', type=int, required=True, help="Client port to connect to")
    args = parser.parse_args()

    print("Starting bidirectional communication...")

    start_listener(args.host_ip, args.host_port)
    connect_to_peer(args.client_ip, args.client_port)
