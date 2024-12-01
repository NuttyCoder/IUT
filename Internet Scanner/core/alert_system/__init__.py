"""
Alert System Module Initialization

This module handles the alert and notification system for the Smart Monitor.
It provides functionality for managing alerts, notifications, and alert rules.
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime

# Import alert system components
from .alert_manager import AlertManager
from .notification_sender import NotificationSender

# Configure alert system logging
logger = logging.getLogger('smart_monitor.alert_system')

class AlertType:
    """Alert type constants"""
    USAGE_LIMIT = "usage_limit"
    DEVICE_OFFLINE = "device_offline"
    MOTION_DETECTED = "motion_detected"
    RESTRICTED_ACCESS = "restricted_access"
    SYSTEM_ERROR = "system_error"
    CAMERA_OFFLINE = "camera_offline"
    NETWORK_ISSUE = "network_issue"

class AlertPriority:
    """Alert priority levels"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class AlertSystem:
    """
    Main Alert System class handling alerts and notifications
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Alert System
        
        Args:
            config: Alert system configuration dictionary
        """
        self.config = config
        self.alert_manager = AlertManager()
        self.notification_sender = NotificationSender(config)
        self.alert_handlers: Dict[str, List[Callable]] = {}
        self.active = False
        
    def start(self) -> bool:
        """
        Start the alert system
        
        Returns:
            bool: Success status
        """
        try:
            self.active = True
            self.alert_manager.start()
            self.notification_sender.start()
            logger.info("Alert system started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start alert system: {e}")
            return False
            
    def stop(self) -> bool:
        """
        Stop the alert system
        
        Returns:
            bool: Success status
        """
        try:
            self.active = False
            self.alert_manager.stop()
            self.notification_sender.stop()
            logger.info("Alert system stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop alert system: {e}")
            return False

    def add_alert_handler(self, alert_type: str, handler: Callable) -> None:
        """
        Add handler for specific alert type
        
        Args:
            alert_type: Type of alert to handle
            handler: Callback function for handling alert
        """
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)
        
    def remove_alert_handler(self, alert_type: str, handler: Callable) -> None:
        """
        Remove specific alert handler
        
        Args:
            alert_type: Type of alert
            handler: Handler to remove
        """
        if alert_type in self.alert_handlers:
            self.alert_handlers[alert_type].remove(handler)

    def trigger_alert(self, 
                     alert_type: str, 
                     message: str, 
                     priority: int = AlertPriority.MEDIUM,
                     data: Optional[Dict] = None) -> bool:
        """
        Trigger a new alert
        
        Args:
            alert_type: Type of alert to trigger
            message: Alert message
            priority: Alert priority level
            data: Additional alert data
            
        Returns:
            bool: Success status
        """
        try:
            # Create alert object
            alert = {
                'type': alert_type,
                'message': message,
                'priority': priority,
                'timestamp': datetime.now(),
                'data': data or {}
            }
            
            # Process alert through manager
            self.alert_manager.process_alert(alert)
            
            # Call registered handlers
            if alert_type in self.alert_handlers:
                for handler in self.alert_handlers[alert_type]:
                    handler(alert)
                    
            # Send notification based on priority
            if priority >= AlertPriority.HIGH:
                self.notification_sender.send_notification(alert)
                
            logger.info(f"Alert triggered: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
            return False

    def get_active_alerts(self) -> List[Dict]:
        """
        Get list of active alerts
        
        Returns:
            List of active alerts
        """
        return self.alert_manager.get_active_alerts()

    def clear_alert(self, alert_id: str) -> bool:
        """
        Clear specific alert
        
        Args:
            alert_id: ID of alert to clear
            
        Returns:
            bool: Success status
        """
        return self.alert_manager.clear_alert(alert_id)

# Define module exports
__all__ = [
    'AlertSystem',
    'AlertType',
    'AlertPriority',
    'AlertManager',
    'NotificationSender'
]