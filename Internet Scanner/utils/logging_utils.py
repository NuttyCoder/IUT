import logging
import os
from datetime import datetime
from typing import Optional

class LoggingUtils:
    """
    Logging utility functions for application-wide logging
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize logging utility
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging settings"""
        # Create logger
        logger = logging.getLogger('smart_monitor')
        logger.setLevel(logging.INFO)
        
        # Create handlers
        self._setup_file_handler()
        self._setup_console_handler()
    
    def _setup_file_handler(self):
        """Setup file handler for logging"""
        log_file = os.path.join(
            self.log_dir,
            f"monitor_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logging.getLogger('smart_monitor').addHandler(file_handler)
    
    def _setup_console_handler(self):
        """Setup console handler for logging"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logging.getLogger('smart_monitor').addHandler(console_handler)
    
    @staticmethod
    def log_error(error: Exception, context: Optional[str] = None):
        """
        Log error with context
        
        Args:
            error: Exception to log
            context: Optional context information
        """
        logger = logging.getLogger('smart_monitor')
        if context:
            logger.error(f"{context}: {str(error)}")
        else:
            logger.error(str(error))
    
    @staticmethod
    def log_activity(message: str, level: str = "info"):
        """
        Log activity message
        
        Args:
            message: Message to log
            level: Logging level (debug, info, warning, error)
        """
        logger = logging.getLogger('smart_monitor')
        getattr(logger, level.lower())(message)