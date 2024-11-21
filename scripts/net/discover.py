from zeroconf import Zeroconf, ServiceBrowser

class MyListener:
    """Listener for discovered services."""
    def add_service(self, zeroconf, service_type, name):
        print(f"Service added: {name}")
        info = zeroconf.get_service_info(service_type, name)
        if info:
            print(f"Service details for {name}:")
            print(f"  Address: {socket.inet_ntoa(info.addresses[0])}")
            print(f"  Port: {info.port}")
            print(f"  Properties: {info.properties}")

    def remove_service(self, zeroconf, service_type, name):
        print(f"Service removed: {name}")

def discover_services(service_name):
    """Discover all services of a specific type."""
    zeroconf = Zeroconf()
    listener = MyListener()
    
    if not service_name.startswith("_"):
        service_name = f"_{service_name}"
    if not service_name.endswith("._tcp.local."):
        service_name += "._tcp.local."

    print(f"Looking for services of type '{service_name}'...")
    browser = ServiceBrowser(zeroconf, service_name, listener)
    try:
        input("Press Enter to stop discovery...\n\n")
    finally:
        zeroconf.close()

if __name__ == "__main__":
    import argparse
    import socket

    # Set up CLI arguments
    parser = argparse.ArgumentParser(description="Discover services using Zeroconf")
    parser.add_argument('--service_name', type=str, required=True, help="Service name to discover")
    args = parser.parse_args()

    # Discover services
    discover_services(args.service_name)
