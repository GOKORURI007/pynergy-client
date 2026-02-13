"""
项目全局配置文件。
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
    abs_mouse_move: bool = True
    screen_width: int = None
    screen_height: int = None
    mouse_backend: Available_Backends | None = None
    keyboard_backend: Available_Backends | None = None
    # 日志名称
    logger_name: str = 'Pynergy'
    # 日志文件夹
    log_dir: Path = user_log_path(appname='pynergy', appauthor=False)
    # 日志文件名
    log_file: str = 'pynergy.log'
    # 文件输出日志级别
    log_level_file: LogLevel = 'WARNING'
    # 标准输出日志级别
    log_level_stdout: LogLevel = 'INFO'
