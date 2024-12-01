# ui/__init__.py
"""
User interface module initialization
"""
from .main_window import MainWindow
from .internet_tab import InternetTab
from .devices_tab import DevicesTab
from .camera_tab import CameraTab
from .alerts_tab import AlertsTab

__all__ = [
    'MainWindow',
    'InternetTab',
    'DevicesTab',
    'CameraTab',
    'AlertsTab'
]