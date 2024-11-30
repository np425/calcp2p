from uuid import UUID, uuid4
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable
from collections import deque


class Connection(ABC):
    @property
    @abstractmethod
    def protocol(self) -> str:
        pass

    @property
    @abstractmethod
    def connected(self) -> bool:
        pass

    @abstractmethod
    async def is_alive(self) -> bool:
        pass

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        pass

    @abstractmethod
    async def write(self, data: bytes) -> bool:
        pass

    @abstractmethod
    async def read(self) -> bytes | None:
        pass


class Node:
    def __init__(self, id: UUID):
        self._id = id
        self._connections: deque[Connection] = deque()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def protocols(self) -> list[str]:
        return list(set(conn.protocol for conn in self._connections))

    @property
    def connected(self) -> list[str]:
        return list(set(conn.protocol for conn in self._connections if conn.connected))

    def add_connection(self, conn: Connection) -> bool:
        exists = not any(_conn == conn for _conn in self._connections)
        if not exists:
            self._connections.append(conn)
        return exists

    async def is_alive(self, protocol: str | None = None) -> bool:
        for conn in self._connections:
            if protocol is None or conn.protocol == protocol:
                if await conn.is_alive():
                    return True
        return False

    async def connect(self, protocol: str | None = None) -> bool:
        for conn in self._connections:
            if protocol is not None and conn.protocol != protocol:
                continue

            if await conn.connect():
                return True
        return False

    async def disconnect(self, protocol: str | None = None) -> bool:
        for conn in self._connections:
            if protocol is not None and conn.protocol != protocol:
                continue

            if conn.connected:
                continue

            return await conn.disconnect()
        return True


class DiscoverCallbackType(Enum):
    OnDiscover = 1
    OnUpdate = 2
    OnRemove = 3
    OnConnect = 4
    OnDisconnect = 5

class ActiveDiscovery(ABC):
    @abstractmethod
    def register_callback(self, callback_type: DiscoverCallbackType, handler: Callable):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def is_active(self):
        pass


class Network:
    def __init__(self):
        self.discoveries: set[Connection] = set()
        self.nodes = dict[UUID, Node]
        self._id = uuid4()

    def add_discovery(self, discovery: ActiveDiscovery):
        discovery.register_callback(
            DiscoverCallbackType.OnDiscover, self._on_node_discover
        )
        discovery.register_callback(DiscoverCallbackType.OnUpdate, self._on_node_update)
        discovery.register_callback(DiscoverCallbackType.OnRemove, self._on_node_remove)
        discovery.start_in_bg()
        self.discoveries.add(discovery)

    def remove_discovery(self, discovery: ActiveDiscovery):
        discovery.stop()
        self.discoveries.remove(discovery)

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def remove_node(self, id: UUID):
        self.nodes.pop(id)

    def _on_node_discover(self, discovery: ActiveDiscovery, node: Node):
        node.connect()
        self.add_node(node)

    def _on_node_update(self, discovery: ActiveDiscovery, node: Node):
        pass

    def _on_node_remove(self, discovery: ActiveDiscovery, node: Node):
        pass
