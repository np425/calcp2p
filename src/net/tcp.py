from node import Connection, ActiveDiscovery
from enum import Enum
import asyncio
from uuid import UUID
import socket
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
from uuid import uuid4
import time


class ConnectionType(Enum):
    ServerToClient = 1
    ClientToServer = 2


class TCPConnection(Connection):
    def __init__(
        self,
        node_ip: str,
        node_port: int,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
        conn_type: ConnectionType | None = None
    ):
        self._ip = node_ip
        self._port = node_port
        
        if reader is not None and writer is not None:
            self._connected = True
        else:
            reader = None
            writer = None
            self._connected = False

        self._reader: asyncio.StreamReader | None = reader
        self._writer: asyncio.StreamWriter | None = writer
            
        if conn_type is None:
            conn_type = ConnectionType.ClientToServer
        self._conn_type = conn_type

    @property
    def protocol(self) -> str:
        return "TCP"

    @property
    def connected(self) -> bool:
        return self._connected

    async def is_alive(self) -> bool:
        if not self._connected:
            return False
        try:
            self._writer.write(b"")  # Write a no-op to check the connection
            await self._writer.drain()
            return True
        except (ConnectionError, asyncio.IncompleteReadError, AttributeError):
            self._connected = False
            return False

    async def connect(self) -> bool:
        if self._connected:
            return True

        if self._conn_type != ConnectionType.ClientToServer:
            raise ValueError("TCP Server cannot connect to client")

        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.ip, self.port
            )
            self._connected = True
            print(f"Connected to {self._ip}:{self._port}")
            return True
        except Exception as e:
            print(f"Failed to connect to {self._ip}:{self._port}: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> bool:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self._connected = False
        print(f"Disconnected from {self._ip}:{self._port}")
        return True

    async def write(self, data: bytes) -> bool:
        if not self._connected or not self._writer:
            return False

        try:
            self._writer.write(data)
            await self._writer.drain()
            print(f"Sent: {data}")
            return True
        except (ConnectionError, asyncio.IncompleteReadError) as e:
            print(f"Write failed: {e}")
            self._connected = False
            return False

    async def read(self) -> bytes | None:
        if not self._connected or not self._reader:
            return None

        try:
            data = await self._reader.read(1024)
            print(f"Received: {data}")
            return data if data else None
        except asyncio.IncompleteReadError:
            self._connected = False
            return None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TCPConnection):
            return False

        return (
            self._ip == other._ip
            and self._port == other._port
            and self._conn_type == other._conn_type
        )

    def __hash__(self) -> int:
        return hash((self._ip, self._port, self._conn_type))


class TCPDiscovery(ActiveDiscovery):
    def __init__(self, id: UUID):
        super().__init__()
        
        self.id = id
        self.zeroconf = ZeroconfService(self.id, self.server_ip, self.server_port)
        
        # Start TCP Server 
    
    def start(self):
        self.zeroconf.start_listening()
        self.zeroconf.start_broadcasting()
    
    def stop(self):
        self.zeroconf.stop()
    
    def is_active(self):
        return self.zeroconf.is_listening() and self.zeroconf.is_broadcasting()


SERVICE_NAME = "_calcp2p._tcp.local."

class ZeroconfService:
    def __init__(self, instance: UUID, ip: str, port: int):
        self.instance: UUID = instance
        self.ip: str = ip
        self.port: int = port

        self.zeroconf: Zeroconf = Zeroconf()
        self.info: ServiceInfo | None = None
        self.browser: ServiceBrowser | None = None

    def start_broadcasting(self):
        try:
            ip_bytes = [socket.inet_aton(self.ip)]  # IPv4
        except OSError:
            ip_bytes = [socket.inet_pton(socket.AF_INET6, self.ip)]  # IPv6

        self.info = ServiceInfo(
            SERVICE_NAME,
            f'_{str(self.instance)}.{SERVICE_NAME}',
            addresses=ip_bytes,
            port=self.port,
            properties={},
            server=f"{socket.gethostname()}.local.",
        )
        self.zeroconf.register_service(self.info)
        print(f"Broadcasting service '{SERVICE_NAME}' at {self.ip}:{self.port}")

    def stop_broadcasting(self):
        if self.info:
            self.zeroconf.unregister_service(self.info)
            self.info = None
            print(f"Stopped broadcasting service '{SERVICE_NAME}'.")

    def start_listening(self):
        if self.browser is None:
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_NAME, self)
            print(f"Listening for services of type {SERVICE_NAME}")

    def stop_listening(self):
        if self.browser is not None:
            self.zeroconf.close()
            self.browser = None
            print("Stopped listening for services.")

    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            print(f"Service discovered: {name}")
            print(f"Service info: IP={info.parsed_addresses()}, Port={info.port}")

    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        print(f"Service removed: {name}")
        
    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        pass

    def stop(self):
        """Stop all Zeroconf operations."""
        if self.info:
            self.stop_broadcasting()
        if self.browser:
            self.stop_listening()
        self.zeroconf.close()
        
    def is_broadcasting(self) -> bool:
        return self.info is not None

    def is_listening(self) -> bool:
        return self.browser is not None

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    # Unique instance ID for the service
    instance_id = uuid4()
    service_ip = "127.0.0.1"
    service_port = 12345

    # Create the Zeroconf service instance
    service = ZeroconfService(instance=instance_id, ip=service_ip, port=service_port)

    try:
        # Start broadcasting and listening for Zeroconf services
        service.start()
        print(f"Zeroconf service started for instance: {instance_id}.")
        print("Service is running. Press Ctrl+C to stop.")

        # Keep the application running to allow Zeroconf operations
        while True:
            time.sleep(1)  # Simulate a long-running application

    except KeyboardInterrupt:
        # Gracefully handle shutdown
        print("\nStopping Zeroconf service...")
        service.stop()
        print("Zeroconf service stopped.")