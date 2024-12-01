import psutil
import time
import socket
import nmap
import speedtest
from datetime import datetime
from scapy.all import ARP, Ether, srp

class HomeNetworkMonitor:
    def __init__(self):
        """Initialize network monitor"""
        self.nm = nmap.PortScanner()
        self.speed_test = speedtest.Speedtest()
        
    def get_connected_devices(self):
        """Scan for connected devices on network"""
        # Get your network IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network = '.'.join(local_ip.split('.')[:-1]) + '.0/24'
        
        # Create ARP request
        arp = ARP(pdst=network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether/arp
        
        # Send packet and get responses
        result = srp(packet, timeout=3, verbose=0)[0]
        
        devices = []
        for sent, received in result:
            devices.append({
                'ip': received.psrc,
                'mac': received.hwsrc,
                'hostname': self._get_hostname(received.psrc)
            })
            
        return devices
    
    def get_bandwidth_usage(self):
        """Get current bandwidth usage"""
        # Get network interface statistics
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
    
    def get_speed_test(self):
        """Run internet speed test"""
        print("Running speed test...")
        download_speed = self.speed_test.download() / 1_000_000  # Convert to Mbps
        upload_speed = self.speed_test.upload() / 1_000_000      # Convert to Mbps
        ping = self.speed_test.results.ping
        
        return {
            'download_mbps': round(download_speed, 2),
            'upload_mbps': round(upload_speed, 2),
            'ping_ms': round(ping, 2)
        }
    
    def get_active_connections(self):
        """Get list of active network connections"""
        connections = []
        for conn in psutil.net_connections():
            if conn.status == 'ESTABLISHED':
                try:
                    process = psutil.Process(conn.pid)
                    connections.append({
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}",
                        'status': conn.status,
                        'pid': conn.pid,
                        'program': process.name()
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return connections
    
    def _get_hostname(self, ip):
        """Get hostname for IP address"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.herror:
            return "Unknown"

def main():
    monitor = HomeNetworkMonitor()
    
    while True:
        print("\n=== Home Network Monitor ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show connected devices
        print("\nConnected Devices:")
        devices = monitor.get_connected_devices()
        for device in devices:
            print(f"IP: {device['ip']:<15} MAC: {device['mac']:<17} Hostname: {device['hostname']}")
        
        # Show bandwidth usage
        usage = monitor.get_bandwidth_usage()
        print("\nBandwidth Usage:")
        print(f"Sent: {usage['bytes_sent']/1024/1024:.2f} MB")
        print(f"Received: {usage['bytes_recv']/1024/1024:.2f} MB")
        
        # Show active connections
        print("\nActive Connections:")
        connections = monitor.get_active_connections()
        for conn in connections:
            print(f"Program: {conn['program']:<20} Local: {conn['local_address']:<21} "
                  f"Remote: {conn['remote_address']}")
        
        # Run speed test every hour
        if datetime.now().minute == 0:
            speed = monitor.get_speed_test()
            print("\nSpeed Test Results:")
            print(f"Download: {speed['download_mbps']} Mbps")
            print(f"Upload: {speed['upload_mbps']} Mbps")
            print(f"Ping: {speed['ping_ms']} ms")
        
        time.sleep(60)  # Update every minute

if __name__ == "__main__":
    main()
