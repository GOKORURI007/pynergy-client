import os
import sys
from pathlib import Path

from loguru import logger

from src import config


def init_logger(
    name: str = config.LOGGER_NAME,
    log_path: Path = config.LOG_DIR / config.LOG_FILE,
    log_level_stdout: config.LogLevel = config.LOG_LEVEL_STDOUT,
    log_level_file: config.LogLevel = config.LOG_LEVEL_FILE,
):
    """
    初始化日志记录器。

    该函数会移除默认的日志处理器，并添加两个新的处理器：
    1. 标准输出（stdout）处理器：用于实时显示日志，带有颜色和简洁的格式。
    2. 文件处理器：将日志记录到指定文件，支持按大小轮转和压缩。

    Args:
        name (str, optional): 日志记录器的名称。默认为 config.LOGGER_NAME。
        log_path (str, optional): 日志文件的路径。默认为 config.LOG_FILE。
        log_level_stdout (config.LogLevel, optional): 标准输出的日志级别。默认为 config.LOG_LEVEL_STDOUT。
        log_level_file (config.LogLevel, optional): 文件输出的日志级别。默认为 config.LOG_LEVEL_FILE。
    """
    config.LOG_DIR.mkdir(exist_ok=True)
    logger.remove()

    logger.add(
        sys.stdout,
        level=log_level_stdout,
        format='<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        colorize=True,
        diagnose=False,
    )

    logger.add(
        log_path,
        level=log_level_file,
        rotation='10 MB',
        compression='zip',
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
        diagnose=False,
    )

    logger.bind(name=name)


def get_screen_size() -> tuple[int, int]:
    """获取屏幕尺寸

    尝试从环境变量或 X11 获取屏幕尺寸，如果都失败则使用默认值。

    Returns:
        (width, height) 屏幕宽度和高度
    """
    try:
        import subprocess

        result = subprocess.run(
            ['xrandr', '--current', '--query'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.split('\n'):
            if '*' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == '*':
                        continue
                    try:
                        width, height = part.split('x')
                        return int(width), int(height)
                    except (ValueError, IndexError):
                        continue
    except (FileNotFoundError, Exception):
        pass

    env_width = os.environ.get('SCREEN_WIDTH')
    env_height = os.environ.get('SCREEN_HEIGHT')
    if env_width and env_height:
        return int(env_width), int(env_height)

    return 1920, 1080
