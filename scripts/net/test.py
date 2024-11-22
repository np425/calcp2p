import asyncio
import argparse


class Node:
    def __init__(self, host, port, peer_host, peer_port):
        self.host = host
        self.port = port
        self.peer_host = peer_host
        self.peer_port = peer_port
        self.connections = {}
        
    async def handle_connection(self, reader, writer, peer_name):
        """Handle bidirectional communication with a peer."""
        try:
            while True:
                data = await reader.read(100)
                if not data:
                    print(f"Peer {peer_name} disconnected.")
                    break
                message = data.decode()
                print(f"Received from {peer_name}: {message}")
                await writer.drain()
        except Exception as e:
            print(f"Error with peer {peer_name}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"Connection with {peer_name} closed.")
        
    async def start_server(self):
        async def handle_client(reader, writer):
            addr = writer.get_extra_info('peername')
            print(f"Accepted connection from {addr}")
            
            self.connections[(self.peer_host, self.peer_port)] = (reader, writer)
            
            await self.handle_connection(reader, writer, addr)

        server = await asyncio.start_server(handle_client, self.host, self.port)
        print(f"Server running on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()    
            
    async def connect_to_peer(self):
        """Connect to the peer node."""
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.peer_host, self.peer_port)
                print(f"Connected to peer at {self.peer_host}:{self.peer_port}")
                
                self.connections[(self.peer_host, self.peer_port)] = (reader, writer,)
                
                await self.handle_connection(reader, writer, f"{self.peer_host}:{self.peer_port}")
                break  # Exit the loop if connection succeeds
            except ConnectionRefusedError:
                print(f"Connection to {self.peer_host}:{self.peer_port} refused. Retrying in 5 seconds...")
                await asyncio.sleep(5)  # Wait before retrying
            except Exception as e:
                print(f"Unexpected error: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)  # Wait before retrying
            
    async def send_to_peer(self):
        """Send messages to the peer node."""
        while True:
            try:
                message = await asyncio.to_thread(input)
                # Simulate sending to connected peers
                
                _, writer = self.connections[(self.peer_host, self.peer_port)]
                
                writer.write(message.encode())
                await writer.drain()
            except Exception as e:
                print(f"Error sending message: {e}")
                break
        
    async def run(self):
        # Start the server
        asyncio.create_task(self.start_server())

        # If this node has a lower tuple, connect to the peer
        if (self.host, self.port) < (self.peer_host, self.peer_port):
            print(f"[{self.host}:{self.port}] Lower tuple. Initiating connection.")
            asyncio.create_task(self.connect_to_peer())
        else:
            pass

        asyncio.create_task(self.send_to_peer())
            
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Set up CLI arguments
    parser = argparse.ArgumentParser(description="Async Bidirectional Chat Node")
    parser.add_argument('--host', type=str, required=True, help="Node's IP address")
    parser.add_argument('--port', type=int, required=True, help="Node's port")
    parser.add_argument('--peer-host', type=str, required=True, help="Peer's IP address")
    parser.add_argument('--peer-port', type=int, required=True, help="Peer's port")
    args = parser.parse_args()

    # Create and run the node
    node = Node(args.host, args.port, args.peer_host, args.peer_port)
    asyncio.run(node.run())
