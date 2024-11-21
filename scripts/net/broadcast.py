from zeroconf import ServiceInfo, Zeroconf
import argparse
import socket
import uuid

def broadcast_service(ip, port, service_name):
    """Broadcast a service using Zeroconf."""
    # Ensure proper Zeroconf formatting for the service type
    if not service_name.startswith("_"):
        service_name = f"_{service_name}"
    if not service_name.endswith("._tcp.local."):
        service_name += "._tcp.local."

    # Generate a unique instance name
    instance_name = str(uuid.uuid4())

    service_type = service_name  # Service type (e.g., _calcp2p._tcp.local.)

    # Create ServiceInfo object
    info = ServiceInfo(
        type_=service_type,
        name=f"{instance_name}.{service_type}",  # Full instance name with service type
        addresses=[socket.inet_aton(ip)],
        port=port,
        server=f"{socket.gethostname()}.local."
    )
    
    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    print(f'Broadcasting {instance_name}.{service_type} on {ip}:{port}')
    try:
        input("Press Enter to exit...\n\n")
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()

if __name__ == "__main__":
    # Set up CLI arguments
    parser = argparse.ArgumentParser(description="Broadcast a service using Zeroconf")
    parser.add_argument('--ip', type=str, required=True, help="IP address to broadcast the service on")
    parser.add_argument('--port', type=int, required=True, help="Port to broadcast the service on")
    parser.add_argument('--service_name', type=str, required=True, help="Service type to broadcast")
    args = parser.parse_args()

    # Broadcast the service
    broadcast_service(args.ip, args.port, args.service_name)
