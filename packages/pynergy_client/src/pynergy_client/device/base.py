import os
import platform
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from loguru import logger


@dataclass
class PlatformInfo:
    """Device information"""

    platform: str = platform.system()
    session_type: str = os.environ.get('XDG_SESSION_TYPE', 'unknown')
    desktop_environment: str = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')


class BaseDeviceContext(ABC):
    def __init__(self):
        self.platform_info: PlatformInfo = PlatformInfo()
        self.logical_pos: Tuple[int, int] = (0, 0)
        self.screen_size: Tuple[int, int] = (0, 0)
        self.scale: float = 1.0

    @abstractmethod
    def update_screen_info(self) -> None:
        """Get current system screen resolution, scale, and other metadata"""
        pass

    @abstractmethod
    def get_real_cursor_pos(self) -> Tuple[int, int] | None:
        """Get the real cursor position from the system"""
        pass

    def sync_logical_to_real(self):
        """Sync logical position to real position to prevent offset accumulation"""
        real_pos = self.get_real_cursor_pos()
        if real_pos:
            self.logical_pos = real_pos

    def calculate_relative_move(self, target_x: int, target_y: int) -> Tuple[int, int]:
        """
        Convert target absolute coordinates to relative displacement from current logical position,
        and automatically update internal logical position.
        """
        # 1. Boundary clamping: prevent target coordinates from exceeding local screen range
        clamped_x = max(0, min(target_x, self.screen_size[0]))
        clamped_y = max(0, min(target_y, self.screen_size[1]))

        # 2. Calculate displacement (Delta)
        dx = clamped_x - self.logical_pos[0]
        dy = clamped_y - self.logical_pos[1]

        # 3. Update logical position (important: this is for next calculation)
        self.logical_pos = (clamped_x, clamped_y)
        logger.opt(lazy=True).trace('{log}', log=lambda: f'Logical pos: {self.logical_pos}')
        return dx, dy

    @staticmethod
    def get_active_screen_resolution_by_kernel():
        drm_path = "/sys/class/drm"
        # Filter out all interface directories (e.g., card1-DP-1)
        interfaces = [d for d in os.listdir(drm_path) if "-" in d and d.startswith("card")]

        for interface in interfaces:
            interface_path = os.path.join(drm_path, interface)

            # 1. Check connection status
            status_file = os.path.join(interface_path, "status")
            if not os.path.exists(status_file):
                continue

            with open(status_file, "r") as f:
                if f.read().strip() != "connected":
                    continue

            # 2. Read resolution mode
            modes_file = os.path.join(interface_path, "modes")
            if os.path.exists(modes_file):
                with open(modes_file, "r") as f:
                    # The first line is usually the current active resolution, format: "2560x1440"
                    current_mode = f.readline().strip()
                    if current_mode:
                        width, height = map(int, current_mode.split('x'))
                        return width, height

        return None


class BaseVirtualDevice(ABC):
    @abstractmethod
    def syn(self) -> None:
        """Synchronize events"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close device"""
        pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class BaseMouseVirtualDevice(BaseVirtualDevice):
    def __init__(self):
        self.pressed_btns: set[int] = set()

    @abstractmethod
    def move_absolute(self, x: int, y: int) -> None:
        """Execute absolute coordinate movement"""
        pass

    @abstractmethod
    def move_relative(self, dx: int, dy: int) -> None:
        """Execute relative coordinate displacement"""
        pass

    @abstractmethod
    def wheel_relative(self, dy: int = 0, dx: int = 0) -> None:
        """Write wheel event"""
        pass

    @abstractmethod
    def wheel_absolute(self, degree: int = 0) -> None:
        """"""
        pass

    @abstractmethod
    def send_button(self, button_id: int, down: bool) -> None:
        """Send mouse button (left/middle/right) command"""
        pass

    @abstractmethod
    def release_all_button(self) -> None:
        """"""
        pass


class BaseKeyboardVirtualDevice(BaseVirtualDevice):
    def __init__(self):
        self.pressed_keys: set[int] = set()
        self.current_modifiers: int = 0

    @abstractmethod
    def send_key(self, key_code: int, down: bool) -> None:
        """Send key command"""
        pass

    @abstractmethod
    def release_all_key(self) -> None:
        """"""
        pass

    @abstractmethod
    def sync_modifiers(self, modifiers: int) -> None:
        """Sync modifier key state"""
        pass
