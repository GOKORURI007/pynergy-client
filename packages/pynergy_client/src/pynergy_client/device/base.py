import os
import platform
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from loguru import logger


@dataclass
class PlatformInfo:
    """设备信息"""

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
        """获取当前系统的屏幕分辨率、缩放等元数据"""
        pass

    @abstractmethod
    def get_real_cursor_pos(self) -> Tuple[int, int] | None:
        """获取系统底层真实的鼠标指针位置"""
        pass

    def sync_logical_to_real(self):
        """同步理论位置到真实位置，防止偏移累积"""
        real_pos = self.get_real_cursor_pos()
        if real_pos:
            self.logical_pos = real_pos

    def calculate_relative_move(self, target_x: int, target_y: int) -> Tuple[int, int]:
        """
        将目标绝对坐标转换为相对于当前理论位置的位移量，
        并自动更新内部理论位置。
        """
        # 1. 边界裁剪：防止目标坐标超出本地屏幕范围
        clamped_x = max(0, min(target_x, self.screen_size[0]))
        clamped_y = max(0, min(target_y, self.screen_size[1]))

        # 2. 计算位移 (Delta)
        dx = clamped_x - self.logical_pos[0]
        dy = clamped_y - self.logical_pos[1]

        # 3. 更新理论位置 (重要：这是为了下次计算)
        self.logical_pos = (clamped_x, clamped_y)
        logger.opt(lazy=True).trace('{log}', log=lambda: f'Logical pos: {self.logical_pos}')
        return dx, dy


class BaseVirtualDevice(ABC):
    @abstractmethod
    def syn(self) -> None:
        """同步事件"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭设备"""
        pass

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


class BaseMouseVirtualDevice(BaseVirtualDevice):
    def __init__(self):
        self.pressed_btns: set[int] = set()

    @abstractmethod
    def move_absolute(self, x: int, y: int) -> None:
        """执行绝对坐标移动"""
        pass

    @abstractmethod
    def move_relative(self, dx: int, dy: int) -> None:
        """执行相对坐标位移"""
        pass

    @abstractmethod
    def wheel_relative(self, dy: int = 0, dx: int = 0) -> None:
        """写入滚轮事件"""
        pass

    @abstractmethod
    def wheel_absolute(self, degree: int = 0) -> None:
        """"""
        pass

    @abstractmethod
    def send_button(self, button_id: int, down: bool) -> None:
        """发送鼠标按键（左/中/右）指令"""
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
        """发送按键指令"""
        pass

    @abstractmethod
    def release_all_key(self) -> None:
        """"""
        pass

    @abstractmethod
    def sync_modifiers(self, modifiers: int) -> None:
        """同步修饰键状态"""
        pass
