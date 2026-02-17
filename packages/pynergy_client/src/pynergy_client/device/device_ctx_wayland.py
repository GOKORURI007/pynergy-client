import os
import shutil
import subprocess
from typing import Tuple

from loguru import logger

from .base import BaseDeviceContext


class WaylandDeviceContext(BaseDeviceContext):
    def __init__(self):
        super().__init__()

    def update_screen_info(self) -> None:
        """获取Wayland环境下的屏幕信息"""
        # 首先尝试使用标准的 Wayland 工具获取屏幕信息
        try:
            # 尝试使用 wlr-randr (sway/wayfire 等)
            if shutil.which('wlr-randr'):
                result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if 'current' in line and 'x' in line:
                        # 解析类似 "1920x1080" 的格式
                        parts = line.split()
                        for part in parts:
                            if 'x' in part and part.replace('x', '').isdigit():
                                width, height = part.split('x')
                                self.screen_size = (int(width), int(height))
                                logger.opt(lazy=True).debug(
                                    '{log}',
                                    log=lambda: f'通过 wlr-randr 获取屏幕尺寸: {self.screen_size}'
                                )
                                return

            # 尝试使用 hyprctl (Hyprland)
            if shutil.which('hyprctl'):
                result = subprocess.run(
                    ['hyprctl', 'monitors'], capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'resolution:' in line.lower():
                        # 解析 Hyprland monitor 信息
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'resolution:' and i + 1 < len(parts):
                                res_part = parts[i + 1]
                                if 'x' in res_part:
                                    width, height = res_part.split('x')
                                    self.screen_size = (int(width), int(height))
                                    logger.opt(lazy=True).debug(
                                        '{log}',
                                        log=lambda: f'通过 hyprctl 获取屏幕尺寸: {self.screen_size}'
                                    )
                                    return

        except Exception as e:
            err_str = str(e)
            logger.opt(lazy=True).warning(
                '{log}',
                log=lambda: f'Wayland 屏幕信息获取失败: {err_str}'
            )

        # 回退方案：检查环境变量
        env_width = os.environ.get('SCREEN_WIDTH')
        env_height = os.environ.get('SCREEN_HEIGHT')
        if env_width and env_height:
            try:
                self.screen_size = (int(env_width), int(env_height))
                logger.opt(lazy=True).debug(
                    '{log}',
                    log=lambda: f'通过环境变量获取屏幕尺寸: {self.screen_size}'
                )
                return
            except ValueError:
                logger.opt(lazy=True).warning(
                    '{log}',
                    log=lambda: '环境变量 SCREEN_WIDTH/SCREEN_HEIGHT 格式错误'
                )

        # 最后的回退方案：使用默认值
        self.screen_size = (1920, 1080)
        logger.opt(lazy=True).warning('{log}', log=lambda: f'使用默认屏幕尺寸: {self.screen_size}')

    def get_real_cursor_pos(self) -> Tuple[int, int] | None:
        """根据不同的桌面环境获取鼠标指针位置"""
        # A. Hyprland (较常见)
        if shutil.which('hyprctl'):
            try:
                # 输出格式通常为 "x, y"
                out: str = subprocess.check_output(['hyprctl', 'cursorpos'], text=True)
                x, y = map(int, out.strip().split(','))
                return x, y
            except Exception as e:
                err_str = str(e)
                logger.opt(lazy=True).warning('{log}', log=lambda: f'Hyprland 获取失败: {err_str}')

        # B. KDE Plasma (Wayland)
        if shutil.which('qdbus'):
            try:
                # 调用 KDE 的 DBus 接口
                out = subprocess.check_output(
                    ['qdbus', 'org.kde.KWin', '/KWin', 'org.kde.KWin.cursorPos'], text=True
                )
                # 输出通常是 QPoint(x, y)
                parts = out.strip().replace('QPoint(', '').replace(')', '').split(',')
                return int(parts[0]), int(parts[1])
            except Exception as e:
                err_str = str(e)
                logger.opt(lazy=True).warning(
                    '{log}',
                    log=lambda: f'KDE Plasma 获取失败: {err_str}'
                )

        # C. Sway/Wayfire (使用 swaymsg)
        if shutil.which('swaymsg'):
            try:
                out = subprocess.check_output(['swaymsg', '-t', 'get_inputs'], text=True)
                # 这个比较复杂，需要解析 JSON，暂时跳过
                pass
            except Exception as e:
                err_str = str(e)
                logger.opt(lazy=True).warning('{log}', log=lambda: f'Sway 获取失败: {err_str}')

        # D. 通用方案：尝试使用 wlroots 工具
        if shutil.which('wlrctl'):
            try:
                out = subprocess.check_output(['wlrctl', 'pointer'], text=True)
                # 解析输出格式
                parts = out.strip().split()
                for part in parts:
                    if part.startswith('x:') and part.endswith('y:'):
                        x = int(part[2:-1])  # 移除 'x:' 和可能的逗号
                        y = int(parts[parts.index(part) + 1].rstrip(','))
                        return x, y
            except Exception as e:
                err_str = str(e)
                logger.opt(lazy=True).warning('{log}', log=lambda: f'wlrctl 获取失败: {err_str}')

        # E. 最后尝试使用环境变量或默认值
        logger.opt(lazy=True).warning(
            '{log}',
            log=lambda: '警告: 当前Wayland环境下无法获取精确的鼠标位置'
        )
        # 返回中心位置作为 fallback
        if self.screen_size[0] > 0 and self.screen_size[1] > 0:
            return self.screen_size[0] // 2, self.screen_size[1] // 2

        return None
