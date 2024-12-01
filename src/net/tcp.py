from node import Connection, ActiveDiscovery, DiscoverCallbackType, Node
from enum import Enum
import asyncio
import socket
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, IPVersion
from uuid import uuid4, UUID
from typing import Callable
from collections import deque
import threading


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


SERVICE_NAME = "_calcp2p._tcp.local."

class ZeroconfService(ActiveDiscovery):
    def __init__(self, instance: UUID, ip: str, port: int):
        self.instance: UUID = instance
        self.ip: str = ip
        self.port: int = port

        self.zeroconf: Zeroconf = Zeroconf()
        self.info: ServiceInfo | None = None
        self.browser: ServiceBrowser | None = None
        
        self.callbacks: set[tuple[DiscoverCallbackType, Callable]] = set()
        self.nodes: deque[Node] = []
        
    def register_callback(self, callback_type: DiscoverCallbackType, handler: Callable):
        self.callbacks.add((callback_type, handler))
        
    def unregister_callback(self, callback_type: DiscoverCallbackType, handler: Callable):
        self.callbacks.discard((callback_type, handler))
        
    def _trigger_callback(self, callback_type: DiscoverCallbackType, *args, **kwargs):
        for cb_type, handler in self.callbacks:
            if cb_type == callback_type:
                handler(*args, **kwargs)
                
    def start(self):
        self.start_broadcasting()
        self.start_listening()

    def stop(self):
        self.stop_broadcasting()
        self.stop_listening()
        
    def is_active(self):
        return self.is_broadcasting() and self.is_listening()

    def start_broadcasting(self):
        try:
            ip_bytes = [socket.inet_aton(self.ip)]  # IPv4
        except OSError:
            ip_bytes = [socket.inet_pton(socket.AF_INET6, self.ip)]  # IPv6

        self.info = ServiceInfo(
            SERVICE_NAME,
            f'{str(self.instance)}.{SERVICE_NAME}',
            addresses=ip_bytes,
            port=self.port,
            properties={},
            server=f"{socket.gethostname()}.local.",
        )
        self.zeroconf.register_service(self.info)
        print(f"Broadcasting zeroconf '{SERVICE_NAME}' at {self.ip}:{self.port}")

    def stop_broadcasting(self):
        if self.info:
            self.zeroconf.unregister_service(self.info)
            self.info = None
            print(f"Stopped broadcasting zeroconf '{SERVICE_NAME}'.")

    def start_listening(self):
        if self.browser is None:
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_NAME, self)
            print(f"Listening for zeroconf services of type {SERVICE_NAME}")

    def stop_listening(self):
        if self.browser is not None:
            self.zeroconf.close()
            self.browser = None
            print("Stopped listening for zeroconf services.")

    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        info = zeroconf.get_service_info(service_type, name)
        if not info:
            print(f'Zeroconf service {name} has no info. Ignoring')
            return
        
        ip = info.parsed_addresses(IPVersion.V4Only)[0]
        port = info.port

        print(f"Zeroconf service discovered: {name}")
        print(f"Zeroconf service info: IP={ip}, Port={port}")
            
        instance = UUID(name.split('.')[0])
        if instance == self.instance:
            print('Zeroconf found instance of itself. Ignoring')
            return

        node = Node(instance)
        connection = TCPConnection(ip, port)
        node.add_connection(connection)
        
        self.nodes.append(node)
            
        self._trigger_callback(DiscoverCallbackType.OnDiscover, self, node)

    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        print(f"Zeroconf service removed: {name}")
        
        instance = UUID(name.split('.')[0])
        
        node = next((node for node in self.nodes if node.id == instance), None)
        
        if node is not None:
            self._trigger_callback(DiscoverCallbackType.OnRemove, self, node)
            self.nodes.remove(node)
        
    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        pass

    def is_broadcasting(self) -> bool:
        return self.info is not None

    def is_listening(self) -> bool:
        return self.browser is not None

    def __del__(self):
        self.stop()


class TCPServer(ActiveDiscovery):
    def __init__(self, host: str, port: int):
        self.server = None
        self.host = host
        self.port = port
        self.callbacks: set[tuple[DiscoverCallbackType, Callable]] = []
        self.nodes = []
        self._running = False        
        self._loop = None
        self._thread = None

    def register_callback(self, callback_type: DiscoverCallbackType, handler: Callable):
        self.callbacks.append((callback_type, handler))

    def unregister_callback(self, callback_type: DiscoverCallbackType, handler: Callable):
        self.callbacks.discard((callback_type, handler))
        
    def _trigger_callback(self, callback_type: DiscoverCallbackType, *args, **kwargs):
        for cb_type, handler in self.callbacks:
            if cb_type == callback_type:
                handler(*args, **kwargs)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._start_server())

    def stop(self):
        if self._running:
            asyncio.run_coroutine_threadsafe(self._stop_server(), self._loop).result()
            self._running = False
            self._loop.stop()
            self._thread.join()

    async def _start_server(self):
        print(f"TCP Server started on {self.host}:{self.port}")
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        async with self.server:
            await self.server.serve_forever()

    async def _stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print("TCP Server stopped.")

    def is_active(self) -> bool:
        return self._running

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_address = writer.get_extra_info('peername')
        if client_address:
            ip, port = client_address
            print(f"TCPServer received connection from {ip}:{port}")
        else:
            print("TCPServer could not retrieve client address")
            return

        instance = uuid4()
        connection = TCPConnection(ip, port, reader, writer, ConnectionType.ServerToClient)
        node = Node(instance)
        node.add_connection(connection)
        self.nodes.append(node)
        self._trigger_callback(DiscoverCallbackType.OnDiscover, self, node)

    def __del__(self):
        self.stop()

