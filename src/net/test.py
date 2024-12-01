from node import Network
from tcp import ZeroconfService, TCPServer
import time
import socket

def get_random_available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))  # Bind to any available port
        return s.getsockname()[1]  # Get the assigned port number

port = get_random_available_port()
network = Network()

# server.start()


server = TCPServer('127.0.0.1', port)
zeroconf = ZeroconfService(network.host_id, '127.0.0.1', port)
network.add_discovery(zeroconf)
network.add_discovery(server)

while True:
    time.sleep(1)