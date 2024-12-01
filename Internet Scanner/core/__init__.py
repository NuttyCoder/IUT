"""
Core module initialization
Core functionality for the Smart Monitor system.

This module initializes all core components of the system and provides
version information and system-wide configurations.
"""

import logging
from typing import Dict, Any

# Version information
__version__ = '1.0.0'
__author__ = 'Your Name'
__license__ = 'MIT'

# Import core components
from .internet_tracker import InternetTracker
from .device_control import DeviceController
from .camera_system import CameraSystem
from .alert_system import AlertSystem

# Configure core logging
logger = logging.getLogger('smart_monitor.core')

class CoreSystem:
    """
    Main core system initialization and management.
    Handles the initialization and coordination of all core subsystems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the core system with configuration.
        
        Args:
            config: Dictionary containing system configuration
        """
        self.config = config
        self.initialized = False
        
        # Initialize core components
        try:
            self.internet_tracker = InternetTracker(config.get('internet', {}))
            self.device_controller = DeviceController(config.get('devices', {}))
            self.camera_system = CameraSystem(config.get('camera', {}))
            self.alert_system = AlertSystem(config.get('alerts', {}))
            
            self.initialized = True
            logger.info("Core system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize core system: {e}")
            raise
    
    def start(self) -> bool:
        """
        Start all core systems.
        
        Returns:
            bool: True if all systems started successfully
        """
        if not self.initialized:
            logger.error("Cannot start: Core system not initialized")
            return False
            
        try:
            # Start core components
            self.internet_tracker.start()
            self.device_controller.start()
            self.camera_system.start()
            self.alert_system.start()
            
            logger.info("All core systems started")
            return True
        except Exception as e:
            logger.error(f"Failed to start core systems: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop all core systems.
        
        Returns:
            bool: True if all systems stopped successfully
        """
        try:
            # Stop core components
            self.internet_tracker.stop()
            self.device_controller.stop()
            self.camera_system.stop()
            self.alert_system.stop()
            
            logger.info("All core systems stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop core systems: {e}")
            return False
    
    def status(self) -> Dict[str, bool]:
        """
        Get status of all core systems.
        
        Returns:
            Dict containing status of each core system
        """
        return {
            'internet_tracker': self.internet_tracker.is_running(),
            'device_controller': self.device_controller.is_running(),
            'camera_system': self.camera_system.is_running(),
            'alert_system': self.alert_system.is_running()
        }

# Define what should be available when importing from core
__all__ = [
    'CoreSystem',
    'InternetTracker',
    'DeviceController',
    'CameraSystem',
    'AlertSystem',
    '__version__',
    '__author__',
    '__license__'
]
