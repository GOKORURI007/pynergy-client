"""
Global project configuration file.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from platformdirs import user_config_path, user_log_path

LogLevel = Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
Available_Backends = Literal[
    'uinput',
    # 'pynput',
    # 'libei',
    # 'wlr'
]


@dataclass
class Config:
    server: str = 'localhost'
    port: int = 24800
    client_name: str = 'Pynergy'
    screen_width: int | None = None
    screen_height: int | None = None
    mouse_backend: Available_Backends | None = None
    keyboard_backend: Available_Backends | None = None

    # --- Handler ---
    abs_mouse_move: bool = False
    mouse_move_threshold: int = 8  # Unit: ms, approx 125Hz, balances smoothness and performance
    mouse_pos_sync_freq: int = (
        2  # Sync frequency, sync actual mouse position with system every n moves
    )

    tls: bool = False
    mtls: bool = False
    tls_trust: bool = False
    pem_path: Path = user_config_path(appname='pynergy', appauthor=False) / 'pynergy.pem'

    # --- Logger ---
    logger_name: str = 'Pynergy'
    log_dir: Path = user_log_path(appname='pynergy', appauthor=False)  # Log directory
    log_file: str = 'pynergy.log'  # Log file name
    log_level_file: LogLevel = 'WARNING'  # File output log level
    log_level_stdout: LogLevel = 'INFO'  # Stdout log level

    def __post_init__(self):
        if isinstance(self.pem_path, str):
            if self.pem_path.startswith('~'):
                self.pem_path = Path(self.pem_path).expanduser()
            self.pem_path = Path(self.pem_path)
        if isinstance(self.log_dir, str):
            if self.log_dir.startswith('~'):
                self.log_dir = Path(self.log_dir).expanduser()
            self.log_dir = Path(self.log_dir)
