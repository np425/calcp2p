import socket
from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo
import uuid
import argparse
import threading
from enum import Enum
from typing import NamedTuple
import asyncio


class NodeConnectionType(Enum):
    ServerToClient = 1
    ClientToServer = 2
    
class NodeConnection(NamedTuple):
    ip: str
    port: int
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    connection_type: NodeConnectionType


class Node:
    def __init__(self, ip: str, port: int):
        self.id = 
        self.connection: NodeConnection | None = None


class ChatApp:
    def __init__(self, ip: str, port: int):
        self.discovery = ServiceDiscovery(self, ip, port)
        self.client = ChatClient(self, ip, port)
        
    def on_client_discovery(self, ip: str, port: int):
        print(f'Discovered new client {ip}:{port}')
        self.client.connect_client(ip, port)
        
    def on_client_connected(self, ip: str, port: int):
        self.client.send_message(f'Hi {ip}:{port}')
        
    def on_client_added(self, conn: socket.socket):
        ip, port = conn.getsockname()
        print(f'New client added {ip}:{port}')
        
    def on_message_sent(self, conn: socket.socket, message: str):
        ip, port = conn.getsockname()
        print(f'{ip}:{port} sent {message}')
        
    def run(self):
        self.discovery.listen()
        self.client.run()

class ChatClient:
    def __init__(self, chat_app: ChatApp, ip: str, port: int):
        self.chat_app = chat_app
        self.ip = ip
        self.port = port
        self.server: socket.socket | None = None
        self.clients: list[socket.socket] = []
        
    def connect_client(self, ip: str, port: int):
        try:
            # Connect to the discovered client
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((ip, port))
            self.clients.append(client_socket)
            self.chat_app.on_client_connected(ip, port)
        except Exception as e:
            print(f"Failed to connect to client {ip}:{port}: {e}")
        
    def run(self):
        # Create and bind the socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.ip, self.port))
        self.server.listen(5)
        print(f"ChatClient listening on {self.ip}:{self.port}")

        # Start a thread to handle incoming messages from clients
        threading.Thread(target=self.listen_to_clients, daemon=True).start()
        
        # Accept new client connections in the main thread
        while True:
            try:
                conn, addr = self.server.accept()
                print(f"New client connected from {addr}")
            except Exception as e:
                print(f"Error accepting new client: {e}")
                break

    def listen_to_clients(self):
        while True:
            for client in list(self.clients):  # Work on a copy of the list
                try:
                    message = client.recv(1024).decode()
                    if message:
                        print(f"Message received: {message}")
                        self.chat_app.on_message_sent(client, message)
                except Exception as e:
                    print(f"Error in serve_messages: {e}")
                    self.clients.remove(client)
                    client.close()
                    
    def send_message(self, message: str):
        """Send the message to every connection."""
        for client in self.clients:
            try:
                client.sendall(message.encode())
                print(f"Sent message to {client.getpeername()}")
            except Exception as e:
                print(f"Failed to send message to {client.getpeername()}: {e}")
                self.clients.remove(client)
                client.close()

    def __del__(self):
        for client in self.clients:
            client.close()
            
        self.server.close()

class ServiceDiscovery:
    def __init__(self, chat_app: ChatApp, ip: str, port: int):
        self.chat_app = chat_app
        self.ip = ip
        self.port = port
        self.service_name = '_calcp2p._tcp.local.'
        self.instance_name = str(uuid.uuid4())
        
        self.zeroconf = Zeroconf()
        self.service_info = ServiceInfo(
            type_=self.service_name,
            name=f"{self.instance_name}.{self.service_name}",  # Full instance name with service type
            addresses=[socket.inet_aton(self.ip)],
            port=self.port,
            server=f"{socket.gethostname()}.local."
        )
        self.browser: ServiceBrowser | None = None

        
    def listen(self):
        self.zeroconf.register_service(self.service_info)
        print(f'Broadcasting {self.instance_name}.{self.service_name} on {self.ip}:{self.port}')
        
        self.browser = ServiceBrowser(self.zeroconf, self.service_name, self)
        print(f'Searching for service {self.service_name}')
        
    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        info = zeroconf.get_service_info(service_type, name)
        if info is None:
            return
        
        instance_name = name.split('.')[0]  # Get the part before the first dot

        # Ignore the service if it matches the local hostname
        if instance_name == self.instance_name:
            print(f"Ignoring self-discovered instance: {instance_name}")
            return
        
        if info:
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            
            self.chat_app.on_client_discovery(ip, port)
            
    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        pass

    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        pass
                
    def __del__(self):
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Dynamic TCP Communication with Client Discovery")
    parser.add_argument('--ip', type=str, default='0.0.0.0', help="Host IP address to bind the listener")
    parser.add_argument('--port', type=int, default=65432, help="Host port to bind the listener")
    args = parser.parse_args()
    
    app = ChatApp(args.ip, args.port)
    app.run()
