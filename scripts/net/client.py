import socket
import argparse

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="TCP Client")
parser.add_argument('--host', type=str, required=True, help='Server IP address')
parser.add_argument('--port', type=int, required=True, help='Server port number')
args = parser.parse_args()

# Connect to the server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((args.host, args.port))
    print(f"Connected to the server at {args.host}:{args.port}")
    
    while True:
        message = input("Enter message to send (or 'exit' to quit): ")
        if message.lower() == 'exit':
            break
        client_socket.sendall(message.encode('utf-8'))  # Send data
        data = client_socket.recv(1024)  # Receive echoed data
        print(f"Received back: {data.decode('utf-8')}")
