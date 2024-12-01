"""
Device Control Module Initialization

This module manages device control functionality, including network access,
device monitoring, and remote control capabilities.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import threading
import queue

# Import device control components
from .controller import DeviceController
from .network_manager import NetworkManager

# Configure device control logging
logger = logging.getLogger('smart_monitor.device_control')

class DeviceType:
    """Device type constants"""
    COMPUTER = "computer"
    MOBILE = "mobile"
    TABLET = "tablet"
    GAMING = "gaming"
    OTHER = "other"

class DeviceStatus:
    """Device status constants"""
    ONLINE = "online"
    OFFLINE = "offline"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"

class DeviceControlSystem:
    """
    Main Device Control System class handling device management and control
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Device Control System
        
        Args:
            config: Device control configuration dictionary
        """
        self.config = config
        self.network_manager = NetworkManager(config)
        self.controller = DeviceController()
        
        # Device tracking
        self.known_devices: Dict[str, Dict] = {}
        self.active_devices: Dict[str, Dict] = {}
        self.blocked_devices: Dict[str, Dict] = {}
        
        # Control queues
        self.command_queue = queue.Queue()
        self.system_active = False
        
        # Initialize tracking thread
        self.tracking_thread = None
        
    def start(self) -> bool:
        """
        Start the device control system
        
        Returns:
            bool: Success status
        """
        try:
            # Start network manager
            self.network_manager.start()
            
            # Start device tracking
            self.system_active = True
            self.tracking_thread = threading.Thread(target=self._track_devices)
            self.tracking_thread.daemon = True
            self.tracking_thread.start()
            
            logger.info("Device control system started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start device control system: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the device control system
        
        Returns:
            bool: Success status
        """
        try:
            self.system_active = False
            if self.tracking_thread:
                self.tracking_thread.join()
            
            # Stop network manager
            self.network_manager.stop()
            
            logger.info("Device control system stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop device control system: {e}")
            return False

    def register_device(self, device_info: Dict) -> Optional[str]:
        """
        Register a new device
        
        Args:
            device_info: Dictionary containing device information
            
        Returns:
            str: Device ID if successful, None otherwise
        """
        try:
            device_id = device_info.get('mac_address', '').replace(':', '')
            self.known_devices[device_id] = {
                'info': device_info,
                'status': DeviceStatus.OFFLINE,
                'last_seen': None,
                'restrictions': {}
            }
            logger.info(f"Registered new device: {device_id}")
            return device_id
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return None

    def block_device(self, device_id: str, duration: Optional[int] = None) -> bool:
        """
        Block network access for device
        
        Args:
            device_id: Device identifier
            duration: Optional block duration in seconds
            
        Returns:
            bool: Success status
        """
        try:
            if device_id not in self.known_devices:
                raise ValueError(f"Unknown device ID: {device_id}")
                
            success = self.network_manager.block_device(device_id)
            if success:
                self.blocked_devices[device_id] = {
                    'blocked_at': datetime.now(),
                    'duration': duration
                }
                self.known_devices[device_id]['status'] = DeviceStatus.BLOCKED
                
                logger.info(f"Blocked device: {device_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to block device: {e}")
            return False

    def unblock_device(self, device_id: str) -> bool:
        """
        Unblock network access for device
        
        Args:
            device_id: Device identifier
            
        Returns:
            bool: Success status
        """
        try:
            if device_id not in self.blocked_devices:
                return False
                
            success = self.network_manager.unblock_device(device_id)
            if success:
                del self.blocked_devices[device_id]
                self.known_devices[device_id]['status'] = DeviceStatus.ONLINE
                
                logger.info(f"Unblocked device: {device_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unblock device: {e}")
            return False

    def _track_devices(self):
        """
        Device tracking thread function
        """
        while self.system_active:
            try:
                # Scan for active devices
                active_devices = self.network_manager.scan_network()
                
                # Update device status
                for device_id, device in self.known_devices.items():
                    if device_id in active_devices:
                        device['status'] = DeviceStatus.ONLINE
                        device['last_seen'] = datetime.now()
                    else:
                        device['status'] = DeviceStatus.OFFLINE
                
                # Check blocked devices for duration expiry
                self._check_blocked_devices()
                
                # Process command queue
                self._process_commands()
                
            except Exception as e:
                logger.error(f"Error in device tracking: {e}")
            
            finally:
                threading.Event().wait(self.config.get('scan_interval', 60))

    def _check_blocked_devices(self):
        """
        Check blocked devices for duration expiry
        """
        now = datetime.now()
        expired = []
        
        for device_id, block_info in self.blocked_devices.items():
            if block_info['duration']:
                block_time = block_info['blocked_at']
                if (now - block_time).total_seconds() >= block_info['duration']:
                    expired.append(device_id)
        
        # Unblock expired devices
        for device_id in expired:
            self.unblock_device(device_id)

    def _process_commands(self):
        """
        Process queued control commands
        """
        while not self.command_queue.empty():
            try:
                command = self.command_queue.get_nowait()
                if command['action'] == 'block':
                    self.block_device(command['device_id'], command.get('duration'))
                elif command['action'] == 'unblock':
                    self.unblock_device(command['device_id'])
            except queue.Empty:
                break

# Define module exports
__all__ = [
    'DeviceControlSystem',
    'DeviceType',
    'DeviceStatus',
    'DeviceController',
    'NetworkManager'
]