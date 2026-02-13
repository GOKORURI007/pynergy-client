import os
from typing import Tuple

from loguru import logger
from Xlib import display

from .base import BaseDeviceContext


class X11DeviceContext(BaseDeviceContext):
    def __init__(self):
        super().__init__()

    def update_screen_info(self) -> None:
        # 首先尝试使用 Xlib 获取屏幕尺寸
        try:
            d = display.Display()
            screen = d.screen()
            root = screen.root
            geometry = root.get_geometry()
            self.screen_size = (geometry.width, geometry.height)
            logger.debug(f'通过 Xlib 获取屏幕尺寸: {self.screen_size}')
            return
        except Exception as e:
            logger.warning(f'Xlib 获取屏幕尺寸失败: {e}')

        # 回退方案：检查环境变量
        env_width = os.environ.get('SCREEN_WIDTH')
        env_height = os.environ.get('SCREEN_HEIGHT')
        if env_width and env_height:
            try:
                self.screen_size = (int(env_width), int(env_height))
                logger.debug(f'通过环境变量获取屏幕尺寸: {self.screen_size}')
                return
            except ValueError:
                logger.warning('环境变量 SCREEN_WIDTH/SCREEN_HEIGHT 格式错误')

        # 最后的回退方案：使用默认值
        self.screen_size = (1920, 1080)
        logger.warning(f'使用默认屏幕尺寸: {self.screen_size}')

    def get_real_cursor_pos(self) -> Tuple[int, int] | None:
        try:
            d = display.Display()
            root = d.screen().root
            pointer = root.query_pointer()
            return pointer.root_x, pointer.root_y
        except Exception as e:
            logger.warning(f'X11 获取失败: {e}')

    def sync_logical_to_real(self):
        self.logical_pos = self.get_real_cursor_pos()
