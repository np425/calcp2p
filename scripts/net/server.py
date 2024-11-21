import socket
import argparse

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="TCP Server")
parser.add_argument('--host', type=str, default='127.0.0.1', help='IP address to bind the server')
parser.add_argument('--port', type=int, required=True, help='Port number to listen on')
args = parser.parse_args()

# Create and bind the socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((args.host, args.port))
    server_socket.listen()
    print(f"Server is listening on {args.host}:{args.port}")
    
    conn, addr = server_socket.accept()  # Accept incoming connection
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)  # Receive data (1024 bytes at a time)
            if not data:
                break
            print(f"Received: {data.decode('utf-8')}")
            conn.sendall(data)  # Echo the data back to the client
