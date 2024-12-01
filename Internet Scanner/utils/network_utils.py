import socket
import netifaces
import subprocess
import platform
from typing import Dict, List, Optional

class NetworkUtils:
    """
    Network utility functions for network operations and analysis
    """
    
    @staticmethod
    def get_local_ip() -> str:
        """Get local IP address of the machine"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            print(f"Error getting local IP: {e}")
            return "127.0.0.1"
    
    @staticmethod
    def scan_network() -> List[Dict[str, str]]:
        """
        Scan local network for devices
        
        Returns:
            List of dictionaries containing device information
        """
        devices = []
        local_ip = NetworkUtils.get_local_ip()
        ip_parts = local_ip.split('.')
        network_prefix = '.'.join(ip_parts[:-1])
        
        for i in range(1, 255):
            ip = f"{network_prefix}.{i}"
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                mac = NetworkUtils.get_mac_address(ip)
                devices.append({
                    'ip': ip,
                    'hostname': hostname,
                    'mac': mac
                })
            except:
                continue
        return devices
    
    @staticmethod
    def get_mac_address(ip: str) -> Optional[str]:
        """Get MAC address for given IP"""
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(f"arp -a {ip}")
                return output.decode().split()[3]
            else:
                output = subprocess.check_output(["arp", "-n", ip])
                return output.decode().split()[2]
        except:
            return None
    
    @staticmethod
    def check_port(ip: str, port: int) -> bool:
        """Check if specific port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False