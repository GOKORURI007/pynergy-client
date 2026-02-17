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
)
from .device.base import PlatformInfo


def init_logger(cfg: config.Config):
    """
    Initialize logger.

    This function removes default handlers and adds two new handlers:
    1. Stdout handler: Displays logs in real-time with colors and concise format.
    2. File handler: Records logs to specified file with size-based rotation and compression.

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
    Initialize input device backend.

    This function calls the corresponding initialization function based on the
    input device backend name in the configuration.

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
                case _:
                    raise NotImplementedError(
                        f'Unsupported session type: {platform_info.session_type}'
                    )

            logger.info(f'Using {platform_info.session_type} backend')
        case _:
            raise NotImplementedError(f'Unsupported platform: {platform_info.platform}')

    if cfg.mouse_backend is not None:
        match cfg.mouse_backend:
            case 'uinput':
                mouse = UInputMouseDevice()
            case 'libei':
                raise NotImplementedError('libei backend is WiP')
            case 'wlr':
                raise NotImplementedError('wlr backend is WiP')
            case _:
                raise ValueError(f'Unsupported mouse backend: {cfg.mouse_backend}')

    if cfg.keyboard_backend is not None:
        match cfg.keyboard_backend:
            case 'uinput':
                keyboard = UInputKeyboardDevice()
            case 'libei':
                raise NotImplementedError('libei backend is WiP')
            case 'wlr':
                raise NotImplementedError('wlr backend is WiP')
            case _:
                raise ValueError(f'Unsupported keyboard backend: {cfg.keyboard_backend}')

    logger.info(f'Using {device_ctx.__class__.__name__} device context')
    logger.info(f'Using {mouse.__class__.__name__} mouse backend')
    logger.info(f'Using {keyboard.__class__.__name__} keyboard backend')

    return device_ctx, mouse, keyboard
