"""
Global project configuration file.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from platformdirs import user_log_path

LogLevel = Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
Available_Backends = Literal[
    'uinput',
    # 'pynput',
    # 'libei',
    # 'wlr'
]


@dataclass
class Config:
    server: str = '127.0.0.1'
    port: int = 24800
    client_name: str = 'Pynergy'
    screen_width: int | None = None
    screen_height: int | None = None
    mouse_backend: Available_Backends | None = None
    keyboard_backend: Available_Backends | None = None

    # --- Handler ---
    abs_mouse_move: bool = False
    mouse_move_threshold: int = 8  # Unit: ms, approx 125Hz, balances smoothness and performance
    mouse_pos_sync_freq: int = 2  # Sync frequency, sync actual mouse position with system every n moves

    # --- Logger ---
    logger_name: str = 'Pynergy'
    # Log directory
    log_dir: Path = user_log_path(appname='pynergy', appauthor=False)
    # Log file name
    log_file: str = 'pynergy.log'
    # File output log level
    log_level_file: LogLevel = 'WARNING'
    # Stdout log level
    log_level_stdout: LogLevel = 'INFO'
