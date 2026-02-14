import os
import socket
import sys
from pathlib import Path
from typing import Tuple

from loguru import logger

from . import config
from .device import (
    BaseDeviceContext,
    BaseKeyboardVirtualDevice,
    BaseMouseVirtualDevice,
    UInputKeyboardDevice,
    UInputMouseDevice,
    WaylandDeviceContext,
    X11DeviceContext,
)
from .device.base import PlatformInfo


def init_logger(cfg: config.Config):
    """
    初始化日志记录器。

    该函数会移除默认的日志处理器，并添加两个新的处理器：
    1. 标准输出（stdout）处理器：用于实时显示日志，带有颜色和简洁的格式。
    2. 文件处理器：将日志记录到指定文件，支持按大小轮转和压缩。

    Args:
        cfg: config dict
    """
    logger.remove()
    log_path = Path(cfg.log_dir) / cfg.log_file
    logger.add(
        sys.stdout,
        level=cfg.log_level_stdout,
        format='<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        colorize=True,
        diagnose=False,
    )

    logger.add(
        log_path,
        level=cfg.log_level_file,
        rotation='10 MB',
        compression='zip',
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
        diagnose=False,
    )

    logger.bind(name=cfg.logger_name)


def init_backend(
    cfg: config.Config,
) -> Tuple[
    BaseDeviceContext | None, BaseMouseVirtualDevice | None, BaseKeyboardVirtualDevice | None
]:
    """
    初始化输入设备后端。

    该函数会根据配置中的输入设备后端名称，调用相应的初始化函数。

    Args:
        cfg: config dict
    """
    device_ctx = None
    mouse = None
    keyboard = None

    platform_info = PlatformInfo()
    match platform_info.platform.lower():
        case 'linux':
            match platform_info.session_type.lower():
                case 'wayland':
                    device_ctx = WaylandDeviceContext()
                    if not cfg.mouse_backend:
                        mouse = UInputMouseDevice()
                    if not cfg.keyboard_backend:
                        keyboard = UInputKeyboardDevice()
                case 'x11':
                    device_ctx = X11DeviceContext()
                    if not cfg.mouse_backend:
                        mouse = UInputMouseDevice()
                    if not cfg.keyboard_backend:
                        keyboard = UInputKeyboardDevice()
                case _:
                    raise NotImplementedError(
                        f'Unsupported session type: {platform_info.session_type}'
                    )

            logger.info(f'Using {platform_info.session_type} backend')

        case 'windows':
            raise NotImplementedError('Windows support is WiP')
        case 'darwin':
            raise NotImplementedError('Darwin support is WiP')
        case _:
            raise NotImplementedError(f'Unsupported platform: {platform_info.platform}')

    if cfg.mouse_backend is not None:
        match cfg.mouse_backend:
            case 'uinput':
                mouse = UInputMouseDevice()
            case 'pynput':
                raise NotImplementedError('pynput backend is WiP')
            case 'libei':
                raise NotImplementedError('libei backend is WiP')
            case 'wlr':
                raise NotImplementedError('wlr backend is WiP')

    if cfg.keyboard_backend is not None:
        match cfg.keyboard_backend:
            case 'uinput':
                keyboard = UInputKeyboardDevice()
            case 'pynput':
                raise NotImplementedError('pynput backend is WiP')
            case 'libei':
                raise NotImplementedError('libei backend is WiP')
            case 'wlr':
                raise NotImplementedError('wlr backend is WiP')

    logger.info(f'Using {device_ctx.__class__.__name__} device context')
    logger.info(f'Using {mouse.__class__.__name__} mouse backend')
    logger.info(f'Using {keyboard.__class__.__name__} keyboard backend')

    return device_ctx, mouse, keyboard


his = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
addr = f'{runtime_dir}/hypr/{his}/.socket.sock'


def get_mouse_position_hyprland():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(addr)
        s.sendall(b'cursorpos')
        response = s.recv(1024).decode()  # 得到 "x, y"
        return response
