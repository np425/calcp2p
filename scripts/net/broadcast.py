from zeroconf import ServiceInfo, Zeroconf
import argparse
import socket

def broadcast_service(ip, port, service_name):
    """Broadcast a service using Zeroconf."""
    desc = {'info': 'My unique service'}
    
    # Ensure proper Zeroconf formatting
    if not service_name.startswith("_"):
        service_name = f"_{service_name}"
    if not service_name.endswith("._tcp.local."):
        service_name += "._tcp.local."

    service_type = service_name
    service_name_full = f"MyService.{service_name}"  # Unique instance name
    
    # Create ServiceInfo object
    info = ServiceInfo(
        type_=service_type,
        name=service_name_full,
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties=desc,
        server=f"{socket.gethostname()}.local."
    )
    
    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    print(f"Service {service_type} is being broadcast on {ip}:{port}")
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
    parser.add_argument('--service_name', type=str, required=True, help="Service name to broadcast")
    args = parser.parse_args()

    # Broadcast the service
    broadcast_service(args.ip, args.port, args.service_name)
