"""
Internet Tracker Module Initialization

This module handles internet usage tracking, website monitoring,
and bandwidth monitoring for connected devices.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import queue
import time

# Import tracker components
from .tracker import UsageTracker
from .website_monitor import WebsiteMonitor

# Configure internet tracker logging
logger = logging.getLogger('smart_monitor.internet_tracker')

class UsageType:
    """Usage type constants"""
    BROWSING = "browsing"
    STREAMING = "streaming"
    GAMING = "gaming"
    DOWNLOAD = "download"
    OTHER = "other"

class InternetTrackerSystem:
    """
    Main Internet Tracker System class handling usage monitoring and control
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Internet Tracker System
        
        Args:
            config: Internet tracker configuration dictionary
        """
        self.config = config
        self.usage_tracker = UsageTracker(config)
        self.website_monitor = WebsiteMonitor(config)
        
        # Tracking state
        self.device_usage: Dict[str, Dict] = {}
        self.daily_limits: Dict[str, int] = {}
        self.system_active = False
        
        # Initialize monitoring thread
        self.monitor_thread = None
        
        # Event queues
        self.event_queue = queue.Queue()
        self.callbacks = []
        
    def start(self) -> bool:
        """
        Start the internet tracking system
        
        Returns:
            bool: Success status
        """
        try:
            # Start components
            self.usage_tracker.start()
            self.website_monitor.start()
            
            # Start monitoring thread
            self.system_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_usage)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Internet tracker system started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start internet tracker: {e}")
            return False
            
    def stop(self) -> bool:
        """
        Stop the internet tracking system
        
        Returns:
            bool: Success status
        """
        try:
            self.system_active = False
            if self.monitor_thread:
                self.monitor_thread.join()
                
            # Stop components
            self.usage_tracker.stop()
            self.website_monitor.stop()
            
            logger.info("Internet tracker system stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop internet tracker: {e}")
            return False
            
    def set_daily_limit(self, device_id: str, limit_mb: int) -> bool:
        """
        Set daily usage limit for device
        
        Args:
            device_id: Device identifier
            limit_mb: Daily limit in megabytes
            
        Returns:
            bool: Success status
        """
        try:
            self.daily_limits[device_id] = limit_mb
            logger.info(f"Set daily limit for device {device_id}: {limit_mb}MB")
            return True
        except Exception as e:
            logger.error(f"Failed to set daily limit: {e}")
            return False
            
    def add_callback(self, callback) -> None:
        """
        Add callback for usage events
        
        Args:
            callback: Callback function
        """
        self.callbacks.append(callback)
        
    def get_device_usage(self, device_id: str) -> Optional[Dict]:
        """
        Get current usage statistics for device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Dictionary containing usage statistics
        """
        return self.device_usage.get(device_id)
        
    def get_daily_report(self, device_id: str) -> Dict:
        """
        Get daily usage report for device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Dictionary containing daily usage report
        """
        try:
            usage = self.usage_tracker.get_daily_usage(device_id)
            websites = self.website_monitor.get_daily_sites(device_id)
            
            return {
                'usage_mb': usage,
                'websites': websites,
                'limit_mb': self.daily_limits.get(device_id, 0),
                'date': datetime.now().date()
            }
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            return {}
            
    def _monitor_usage(self):
        """
        Main usage monitoring thread function
        """
        while self.system_active:
            try:
                # Update usage statistics
                for device_id in self.daily_limits.keys():
                    current_usage = self.usage_tracker.get_current_usage(device_id)
                    self.device_usage[device_id] = current_usage
                    
                    # Check usage limits
                    self._check_limits(device_id, current_usage)
                    
                # Process website access
                self._process_website_access()
                
                # Process callbacks
                self._process_callbacks()
                
            except Exception as e:
                logger.error(f"Error in usage monitoring: {e}")
            
            finally:
                time.sleep(self.config.get('update_interval', 60))
                
    def _check_limits(self, device_id: str, usage: Dict):
        """
        Check if device has exceeded usage limits
        
        Args:
            device_id: Device identifier
            usage: Current usage statistics
        """
        if device_id in self.daily_limits:
            limit = self.daily_limits[device_id]
            if usage['total_mb'] > limit:
                event = {
                    'type': 'limit_exceeded',
                    'device_id': device_id,
                    'usage': usage['total_mb'],
                    'limit': limit,
                    'timestamp': datetime.now()
                }
                self.event_queue.put(event)
                
    def _process_website_access(self):
        """
        Process website access events
        """
        for access in self.website_monitor.get_pending_access():
            event = {
                'type': 'website_access',
                'device_id': access['device_id'],
                'url': access['url'],
                'timestamp': access['timestamp']
            }
            self.event_queue.put(event)
            
    def _process_callbacks(self):
        """
        Process events and trigger callbacks
        """
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                for callback in self.callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
            except queue.Empty:
                break

# Define module exports
__all__ = [
    'InternetTrackerSystem',
    'UsageType',
    'UsageTracker',
    'WebsiteMonitor'
]