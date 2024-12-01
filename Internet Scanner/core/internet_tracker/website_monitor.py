import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import threading
import queue
import sqlite3
import re
from urllib.parse import urlparse
import scapy.all as scapy
from scapy.layers import http
from collections import defaultdict

class WebsiteMonitor:
    def __init__(self, db_connection: sqlite3.Connection, config: Dict):
        """
        Initialize Website Monitor
        
        Args:
            db_connection: Database connection
            config: Configuration dictionary
        """
        self.db = db_connection
        self.config = config
        self.active = False
        
        # Monitoring state
        self.blocked_sites: Set[str] = set()
        self.restricted_categories: Set[str] = set()
        self.device_restrictions: Dict[str, Dict] = {}
        
        # Packet capture
        self.packet_queue = queue.Queue()
        self.capture_thread = None
        
        # Website categorization
        self.categories = self._load_categories()
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables"""
        cursor = self.db.cursor()
        
        # Website access log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS website_access (
                id INTEGER PRIMARY KEY,
                device_id TEXT,
                url TEXT,
                domain TEXT,
                category TEXT,
                timestamp DATETIME,
                duration INTEGER
            )
        ''')
        
        # Blocked websites
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_sites (
                domain TEXT PRIMARY KEY,
                category TEXT,
                reason TEXT,
                added_date DATETIME
            )
        ''')
        
        # Website categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS website_categories (
                domain TEXT PRIMARY KEY,
                category TEXT,
                last_updated DATETIME
            )
        ''')
        
        self.db.commit()
        
    def start(self):
        """Start website monitoring"""
        self.active = True
        
        # Start packet capture
        self.capture_thread = threading.Thread(target=self._capture_packets)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_packets)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        logging.info("Website monitoring started")
        
    def stop(self):
        """Stop website monitoring"""
        self.active = False
        if self.capture_thread:
            self.capture_thread.join()
        if self.process_thread:
            self.process_thread.join()
        logging.info("Website monitoring stopped")
        
    def block_website(self, domain: str, reason: str = "manually blocked"):
        """
        Block specific website
        
        Args:
            domain: Domain to block
            reason: Reason for blocking
        """
        cursor = self.db.cursor()
        category = self._get_category(domain)
        
        cursor.execute('''
            INSERT OR REPLACE INTO blocked_sites 
            (domain, category, reason, added_date)
            VALUES (?, ?, ?, ?)
        ''', (domain, category, reason, datetime.now()))
        
        self.blocked_sites.add(domain)
        self.db.commit()
        
    def unblock_website(self, domain: str):
        """
        Unblock specific website
        
        Args:
            domain: Domain to unblock
        """
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM blocked_sites WHERE domain = ?', (domain,))
        
        if domain in self.blocked_sites:
            self.blocked_sites.remove(domain)
            
        self.db.commit()
        
    def set_device_restrictions(self, device_id: str, restrictions: Dict):
        """
        Set website restrictions for device
        
        Args:
            device_id: Device identifier
            restrictions: Dictionary of restrictions
        """
        self.device_restrictions[device_id] = restrictions
        
    def _capture_packets(self):
        """Capture network packets"""
        try:
            # Start packet capture
            scapy.sniff(
                filter="tcp port 80 or tcp port 443",
                prn=self._packet_callback,
                store=0
            )
        except Exception as e:
            logging.error(f"Packet capture error: {e}")
            
    def _packet_callback(self, packet):
        """Process captured packet"""
        try:
            if packet.haslayer(http.HTTPRequest):
                self.packet_queue.put(packet)
        except Exception as e:
            logging.error(f"Packet callback error: {e}")
            
    def _process_packets(self):
        """Process captured packets"""
        while self.active:
            try:
                while not self.packet_queue.empty():
                    packet = self.packet_queue.get_nowait()
                    self._process_http_packet(packet)
            except queue.Empty:
                pass
            except Exception as e:
                logging.error(f"Packet processing error: {e}")
                
    def _process_http_packet(self, packet):
        """
        Process HTTP packet
        
        Args:
            packet: Scapy packet
        """
        try:
            http_layer = packet[http.HTTPRequest]
            url = f"{http_layer.Host.decode()}{http_layer.Path.decode()}"
            domain = self._extract_domain(url)
            device_id = self._get_device_id(packet)
            
            # Check if blocked
            if self._is_blocked(domain, device_id):
                self._log_blocked_access(device_id, url, domain)
                return
                
            # Log access
            self._log_access(device_id, url, domain)
            
        except Exception as e:
            logging.error(f"HTTP packet processing error: {e}")
            
    def _is_blocked(self, domain: str, device_id: str) -> bool:
        """
        Check if domain is blocked
        
        Args:
            domain: Domain to check
            device_id: Device identifier
            
        Returns:
            bool: True if blocked
        """
        # Check global blocks
        if domain in self.blocked_sites:
            return True
            
        # Check device restrictions
        if device_id in self.device_restrictions:
            restrictions = self.device_restrictions[device_id]
            category = self._get_category(domain)
            
            if category in restrictions.get('blocked_categories', []):
                return True
                
        return False
        
    def _log_access(self, device_id: str, url: str, domain: str):
        """
        Log website access
        
        Args:
            device_id: Device identifier
            url: Accessed URL
            domain: Domain
        """
        try:
            cursor = self.db.cursor()
            category = self._get_category(domain)
            
            cursor.execute('''
                INSERT INTO website_access 
                (device_id, url, domain, category, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (device_id, url, domain, category, datetime.now()))
            
            self.db.commit()
            
        except Exception as e:
            logging.error(f"Error logging access: {e}")
            
    def _log_blocked_access(self, device_id: str, url: str, domain: str):
        """Log blocked access attempt"""
        logging.warning(f"Blocked access attempt: {device_id} -> {url}")
        
    def _get_category(self, domain: str) -> str:
        """Get website category"""
        return self.categories.get(domain, 'uncategorized')
        
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except:
            return url
            
    def _get_device_id(self, packet) -> Optional[str]:
        """Get device ID from packet"""
        try:
            # Implementation depends on how devices are identified
            src_mac = packet[scapy.Ether].src
            return f"device_{src_mac.replace(':', '')}"
        except:
            return None
            
    def _load_categories(self) -> Dict[str, str]:
        """Load website categories from database"""
        categories = {}
        try:
            cursor = self.db.cursor()
            cursor.execute('SELECT domain, category FROM website_categories')
            for domain, category in cursor.fetchall():
                categories[domain] = category
        except Exception as e:
            logging.error(f"Error loading categories: {e}")
        return categories
        
    def get_device_history(self, device_id: str, days: int = 1) -> List[Dict]:
        """
        Get website access history for device
        
        Args:
            device_id: Device identifier
            days: Number of days of history
            
        Returns:
            List of access records
        """
        try:
            cursor = self.db.cursor()
            start_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT url, domain, category, timestamp, duration
                FROM website_access
                WHERE device_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (device_id, start_date))
            
            return [{
                'url': row[0],
                'domain': row[1],
                'category': row[2],
                'timestamp': row[3],
                'duration': row[4]
            } for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Error getting device history: {e}")
            return []