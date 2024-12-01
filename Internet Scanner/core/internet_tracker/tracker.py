import psutil
import time
from datetime import datetime, timedelta
import threading
import logging
from typing import Dict, List, Optional
import sqlite3
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class UsageData:
    """Data structure for usage statistics"""
    bytes_sent: int = 0
    bytes_received: int = 0
    active_time: int = 0
    start_time: Optional[float] = None
    last_update: Optional[float] = None

class InternetTracker:
    def __init__(self, db_connection: sqlite3.Connection, config: Dict):
        """
        Initialize Internet Usage Tracker
        
        Args:
            db_connection: Database connection
            config: Configuration dictionary
        """
        self.db = db_connection
        self.config = config
        self.active = False
        
        # Device tracking
        self.device_stats = defaultdict(UsageData)
        self.device_limits = {}
        
        # Callbacks for events
        self.limit_callbacks = []
        
        # Initialize database tables
        self._init_database()
        
        # Start monitoring thread
        self.monitor_thread = None
        
    def _init_database(self):
        """Initialize database tables"""
        cursor = self.db.cursor()
        
        # Real-time usage tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_data (
                id INTEGER PRIMARY KEY,
                device_id TEXT,
                timestamp DATETIME,
                bytes_sent INTEGER,
                bytes_received INTEGER,
                duration INTEGER
            )
        ''')
        
        # Daily summaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY,
                device_id TEXT,
                date DATE,
                total_bytes INTEGER,
                total_time INTEGER,
                UNIQUE(device_id, date)
            )
        ''')
        
        # Usage limits
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_limits (
                device_id TEXT PRIMARY KEY,
                daily_limit INTEGER,
                notification_threshold INTEGER
            )
        ''')
        
        self.db.commit()
        
    def start(self):
        """Start internet usage tracking"""
        self.active = True
        self.monitor_thread = threading.Thread(target=self._monitor_usage)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logging.info("Internet usage tracking started")
        
    def stop(self):
        """Stop internet usage tracking"""
        self.active = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self._save_final_stats()
        logging.info("Internet usage tracking stopped")
        
    def set_device_limit(self, device_id: str, daily_limit_mb: int, 
                        notification_threshold: int = 90):
        """
        Set daily usage limit for device
        
        Args:
            device_id: Device identifier
            daily_limit_mb: Daily limit in megabytes
            notification_threshold: Percentage for notification
        """
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO device_limits 
            (device_id, daily_limit, notification_threshold)
            VALUES (?, ?, ?)
        ''', (device_id, daily_limit_mb, notification_threshold))
        
        self.device_limits[device_id] = {
            'limit': daily_limit_mb,
            'threshold': notification_threshold
        }
        self.db.commit()
        
    def add_limit_callback(self, callback):
        """Add callback for limit notifications"""
        self.limit_callbacks.append(callback)
        
    def _monitor_usage(self):
        """Main monitoring loop"""
        last_save = time.time()
        check_interval = self.config.get('check_interval', 1)
        save_interval = self.config.get('save_interval', 60)
        
        while self.active:
            try:
                current_time = time.time()
                
                # Update network statistics
                self._update_stats()
                
                # Check limits
                self._check_limits()
                
                # Periodically save to database
                if current_time - last_save >= save_interval:
                    self._save_stats()
                    last_save = current_time
                    
                time.sleep(check_interval)
                
            except Exception as e:
                logging.error(f"Error monitoring usage: {e}")
                time.sleep(5)
                
    def _update_stats(self):
        """Update network statistics"""
        try:
            net_counters = psutil.net_io_counters(pernic=True)
            
            for interface, counters in net_counters.items():
                device_id = self._get_device_id(interface)
                if not device_id:
                    continue
                    
                stats = self.device_stats[device_id]
                
                if not stats.start_time:
                    stats.start_time = time.time()
                    stats.bytes_sent = counters.bytes_sent
                    stats.bytes_received = counters.bytes_recv
                else:
                    # Calculate differences
                    sent_diff = counters.bytes_sent - stats.bytes_sent
                    recv_diff = counters.bytes_recv - stats.bytes_received
                    
                    # Update totals
                    stats.bytes_sent += sent_diff
                    stats.bytes_received += recv_diff
                    
                stats.last_update = time.time()
                
        except Exception as e:
            logging.error(f"Error updating stats: {e}")
            
    def _check_limits(self):
        """Check usage limits and trigger notifications"""
        for device_id, stats in self.device_stats.items():
            if device_id in self.device_limits:
                limit = self.device_limits[device_id]
                total_mb = (stats.bytes_sent + stats.bytes_received) / 1024 / 1024
                
                if total_mb >= limit['limit']:
                    self._trigger_limit_exceeded(device_id, total_mb, limit['limit'])
                elif (total_mb / limit['limit'] * 100) >= limit['threshold']:
                    self._trigger_threshold_reached(device_id, total_mb, limit['limit'])
                    
    def _save_stats(self):
        """Save current statistics to database"""
        try:
            cursor = self.db.cursor()
            current_time = datetime.now()
            
            for device_id, stats in self.device_stats.items():
                if not stats.last_update:
                    continue
                    
                # Save detailed usage
                cursor.execute('''
                    INSERT INTO usage_data 
                    (device_id, timestamp, bytes_sent, bytes_received, duration)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    device_id,
                    current_time,
                    stats.bytes_sent,
                    stats.bytes_received,
                    int(time.time() - stats.start_time)
                ))
                
                # Update daily summary
                self._update_daily_summary(cursor, device_id, stats)
                
            self.db.commit()
            self._reset_stats()
            
        except Exception as e:
            logging.error(f"Error saving stats: {e}")
            self.db.rollback()
            
    def _update_daily_summary(self, cursor: sqlite3.Cursor, 
                            device_id: str, stats: UsageData):
        """Update daily usage summary"""
        today = datetime.now().date()
        total_bytes = stats.bytes_sent + stats.bytes_received
        duration = int(time.time() - stats.start_time)
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_summary 
            (device_id, date, total_bytes, total_time)
            VALUES (
                ?, ?, 
                COALESCE((SELECT total_bytes FROM daily_summary 
                         WHERE device_id = ? AND date = ?) + ?, ?),
                COALESCE((SELECT total_time FROM daily_summary 
                         WHERE device_id = ? AND date = ?) + ?, ?)
            )
        ''', (
            device_id, today,
            device_id, today, total_bytes, total_bytes,
            device_id, today, duration, duration
        ))
        
    def get_usage_report(self, device_id: str, days: int = 1) -> Dict:
        """
        Get usage report for device
        
        Args:
            device_id: Device identifier
            days: Number of days for report
            
        Returns:
            Dictionary containing usage statistics
        """
        try:
            cursor = self.db.cursor()
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days-1)
            
            cursor.execute('''
                SELECT date, total_bytes, total_time
                FROM daily_summary
                WHERE device_id = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
            ''', (device_id, start_date, end_date))
            
            daily_data = cursor.fetchall()
            
            report = {
                'device_id': device_id,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'daily_usage': [
                    {
                        'date': row[0],
                        'total_mb': row[1] / 1024 / 1024,
                        'total_hours': row[2] / 3600
                    }
                    for row in daily_data
                ],
                'total_usage': sum(row[1] for row in daily_data) / 1024 / 1024,
                'total_time': sum(row[2] for row in daily_data) / 3600
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error generating report: {e}")
            return {}
            
    def _trigger_limit_exceeded(self, device_id: str, usage: float, limit: float):
        """Trigger limit exceeded callbacks"""
        event = {
            'type': 'limit_exceeded',
            'device_id': device_id,
            'usage_mb': usage,
            'limit_mb': limit,
            'timestamp': datetime.now()
        }
        
        for callback in self.limit_callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(f"Error in limit callback: {e}")
                
    def _trigger_threshold_reached(self, device_id: str, usage: float, limit: float):
        """Trigger threshold reached callbacks"""
        event = {
            'type': 'threshold_reached',
            'device_id': device_id,
            'usage_mb': usage,
            'limit_mb': limit,
            'timestamp': datetime.now()
        }
        
        for callback in self.limit_callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(f"Error in threshold callback: {e}")
                
    def _get_device_id(self, interface: str) -> Optional[str]:
        """Get device ID from network interface"""
        # Implementation depends on how devices are identified in your system
        pass
        
    def _reset_stats(self):
        """Reset current statistics"""
        for device_id in self.device_stats:
            self.device_stats[device_id] = UsageData(start_time=time.time())
            
    def _save_final_stats(self):
        """Save final statistics before stopping"""
        self._save_stats()
