import socket
import threading
import argparse
import time

BUFFER_SIZE = 1024
BROADCAST_PORT = 12345  # Port for broadcasting

def broadcast_server(ip, port):
    """Broadcast server presence on the local network."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as broadcast_socket:
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"SERVER:{ip}:{port}"
        while True:
            broadcast_socket.sendto(message.encode(), ('<broadcast>', BROADCAST_PORT))
            time.sleep(5)  # Broadcast every 5 seconds

def handle_client(conn, addr):
    """Handle communication with a connected client."""
    print(f"New connection from {addr}")
    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                print(f"Connection closed by {addr}")
                break
            print(f"Received from {addr}: {data.decode()}")
        except ConnectionResetError:
            print(f"Connection lost with {addr}")
            break
    conn.close()

def listen_for_clients(host_ip, host_port):
    """Listen for incoming client connections."""
    listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener_socket.bind((host_ip, host_port))
    listener_socket.listen()
    print(f"Listening for clients on {host_ip}:{host_port}")
    while True:
        conn, addr = listener_socket.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def discover_and_connect():
    """Discover servers on the local network and connect to them."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.bind(('', BROADCAST_PORT))
        print(f"Listening for broadcast messages on port {BROADCAST_PORT}")
        known_servers = set()
        while True:
            data, addr = udp_socket.recvfrom(1024)
            message = data.decode()
            if message.startswith("SERVER:"):
                server_ip, server_port = message.split(":")[1:]
                if (server_ip, server_port) not in known_servers:
                    known_servers.add((server_ip, server_port))
                    print(f"Discovered server at {server_ip}:{server_port}")
                    threading.Thread(target=connect_to_peer, args=(server_ip, int(server_port)), daemon=True).start()

def connect_to_peer(ip, port):
    """Connect to a peer and send messages."""
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                peer_socket.connect((ip, port))
                print(f"Connected to peer at {ip}:{port}")
                while True:
                    message = input(f"Send to {ip}:{port}: ")
                    if message.lower() == "exit":
                        return
                    peer_socket.sendall(message.encode())
        except ConnectionRefusedError:
            print(f"Connection to {ip}:{port} failed. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Dynamic TCP Communication with Client Discovery")
    parser.add_argument('--host_ip', type=str, required=True, help="Host IP address to bind the listener")
    parser.add_argument('--host_port', type=int, required=True, help="Host port to bind the listener")
    args = parser.parse_args()

    print("Starting server with dynamic client discovery...")

    # Start the listener thread
    threading.Thread(target=listen_for_clients, args=(args.host_ip, args.host_port), daemon=True).start()

    # Start the broadcast thread
    threading.Thread(target=broadcast_server, args=(args.host_ip, args.host_port), daemon=True).start()

    # Start the discovery thread
    threading.Thread(target=discover_and_connect, daemon=True).start()

    # Keep the main thread alive
    while True:
        time.sleep(1)
