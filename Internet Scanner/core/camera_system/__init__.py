"""
Camera System Module Initialization

This module manages the Blink camera system, including video recording,
motion detection, and camera control functionality.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os
from pathlib import Path

# Import camera system components
from .blink_controller import BlinkController
from .video_processor import VideoProcessor
from .motion_detector import MotionDetector

# Configure camera system logging
logger = logging.getLogger('smart_monitor.camera_system')

class RecordingMode:
    """Recording mode constants"""
    CONTINUOUS = "continuous"
    MOTION = "motion"
    SCHEDULED = "scheduled"
    MANUAL = "manual"

class CameraStatus:
    """Camera status constants"""
    ONLINE = "online"
    OFFLINE = "offline"
    RECORDING = "recording"
    ERROR = "error"

class CameraSystem:
    """
    Main Camera System class handling camera operations and management
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Camera System
        
        Args:
            config: Camera system configuration dictionary
        """
        self.config = config
        self.storage_path = Path(config.get('storage_path', 'recordings'))
        self.storage_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.blink_controller = BlinkController(
            username=config.get('blink_username'),
            password=config.get('blink_password')
        )
        self.video_processor = VideoProcessor()
        self.motion_detector = MotionDetector(
            sensitivity=config.get('motion_sensitivity', 0.5)
        )
        
        # State tracking
        self.active_cameras: Dict[str, Dict] = {}
        self.recording_sessions: Dict[str, Dict] = {}
        self.system_active = False
        
    def start(self) -> bool:
        """
        Start the camera system
        
        Returns:
            bool: Success status
        """
        try:
            # Initialize Blink connection
            if not self.blink_controller.initialize():
                raise Exception("Failed to initialize Blink controller")
                
            # Discover and setup cameras
            self._setup_cameras()
            
            # Start components
            self.video_processor.start()
            self.motion_detector.start()
            
            self.system_active = True
            logger.info("Camera system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera system: {e}")
            return False
            
    def stop(self) -> bool:
        """
        Stop the camera system
        
        Returns:
            bool: Success status
        """
        try:
            # Stop all recordings
            self._stop_all_recordings()
            
            # Stop components
            self.video_processor.stop()
            self.motion_detector.stop()
            
            self.system_active = False
            logger.info("Camera system stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop camera system: {e}")
            return False

    def _setup_cameras(self) -> None:
        """
        Discover and setup all cameras
        """
        cameras = self.blink_controller.get_cameras()
        for camera in cameras:
            camera_id = camera['id']
            self.active_cameras[camera_id] = {
                'info': camera,
                'status': CameraStatus.ONLINE,
                'recording_mode': None,
                'last_motion': None
            }
            
    def start_recording(self, 
                       camera_id: str, 
                       mode: str = RecordingMode.MANUAL,
                       duration: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Start recording from specified camera
        
        Args:
            camera_id: Camera identifier
            mode: Recording mode
            duration: Recording duration in seconds (None for continuous)
            
        Returns:
            Tuple of (success status, recording ID if successful)
        """
        try:
            if camera_id not in self.active_cameras:
                raise ValueError(f"Unknown camera ID: {camera_id}")
                
            # Generate recording ID and path
            recording_id = f"REC_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            recording_path = self.storage_path / recording_id
            
            # Start recording session
            success = self.video_processor.start_recording(
                camera_id,
                str(recording_path),
                duration
            )
            
            if success:
                self.recording_sessions[recording_id] = {
                    'camera_id': camera_id,
                    'mode': mode,
                    'start_time': datetime.now(),
                    'duration': duration,
                    'path': recording_path
                }
                self.active_cameras[camera_id]['status'] = CameraStatus.RECORDING
                
                logger.info(f"Started recording {recording_id} from camera {camera_id}")
                return True, recording_id
                
            return False, None
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False, None
            
    def stop_recording(self, recording_id: str) -> bool:
        """
        Stop specific recording
        
        Args:
            recording_id: Recording identifier
            
        Returns:
            bool: Success status
        """
        try:
            if recording_id not in self.recording_sessions:
                raise ValueError(f"Unknown recording ID: {recording_id}")
                
            session = self.recording_sessions[recording_id]
            camera_id = session['camera_id']
            
            # Stop recording
            success = self.video_processor.stop_recording(camera_id)
            
            if success:
                # Update status
                self.active_cameras[camera_id]['status'] = CameraStatus.ONLINE
                del self.recording_sessions[recording_id]
                
                logger.info(f"Stopped recording {recording_id}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False
            
    def enable_motion_detection(self, 
                              camera_id: str,
                              sensitivity: Optional[float] = None) -> bool:
        """
        Enable motion detection for camera
        
        Args:
            camera_id: Camera identifier
            sensitivity: Motion detection sensitivity (0.0 to 1.0)
            
        Returns:
            bool: Success status
        """
        try:
            if camera_id not in self.active_cameras:
                raise ValueError(f"Unknown camera ID: {camera_id}")
                
            # Set sensitivity if provided
            if sensitivity is not None:
                self.motion_detector.set_sensitivity(camera_id, sensitivity)
                
            # Enable detection
            success = self.motion_detector.enable_detection(camera_id)
            
            if success:
                self.active_cameras[camera_id]['recording_mode'] = RecordingMode.MOTION
                logger.info(f"Enabled motion detection for camera {camera_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to enable motion detection: {e}")
            return False
            
    def get_camera_status(self, camera_id: str) -> Optional[Dict]:
        """
        Get current status of specific camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Dictionary with camera status information
        """
        return self.active_cameras.get(camera_id)
        
    def get_recordings(self, camera_id: Optional[str] = None) -> List[Dict]:
        """
        Get list of recordings
        
        Args:
            camera_id: Optional camera ID to filter recordings
            
        Returns:
            List of recording information dictionaries
        """
        recordings = []
        for rec_id, session in self.recording_sessions.items():
            if camera_id is None or session['camera_id'] == camera_id:
                recordings.append({
                    'id': rec_id,
                    **session
                })
        return recordings

# Define module exports
__all__ = [
    'CameraSystem',
    'RecordingMode',
    'CameraStatus',
    'BlinkController',
    'VideoProcessor',
    'MotionDetector'
]
Last edited just now