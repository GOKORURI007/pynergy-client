import os
import shutil
import subprocess
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


def get_mouse_position() -> tuple[int, int] | None:
    """
    根据当前系统环境 (X11/Wayland) 获取鼠标全局坐标
    Returns: (x, y) 元组，失败返回 None
    """
    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
    if not session_type:
        logger.warning('无法获取当前系统环境 XDG_SESSION_TYPE')
        return None

    # --- 1. 处理 X11 环境 ---
    if session_type == 'x11':
        try:
            from Xlib import display

            d = display.Display()
            root = d.screen().root
            pointer = root.query_pointer()
            return pointer.root_x, pointer.root_y
        except Exception as e:
            logger.warning(f'X11 获取失败: {e}')

    # --- 2. 处理 Wayland 环境 ---
    # Wayland 没有统一 API，需根据不同的合成器 (Compositor) 分别处理
    if session_type == 'wayland' or os.environ.get('WAYLAND_DISPLAY'):
        # A. Hyprland (NixOS 用户常用)
        if shutil.which('hyprctl'):
            try:
                # 输出格式通常为 "x, y"
                out: str = subprocess.check_output(['hyprctl', 'cursorpos'], text=True)
                x, y = map(int, out.strip().split(','))
                return x, y
            except Exception as e:
                logger.warning(f'Hyprland 获取失败: {e}')

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
                logger.warning(f'KDE Plasma 获取失败: {e}')

        # C. GNOME (Wayland) - 极难获取
        # GNOME 出于安全考虑彻底封死了非插件获取坐标的路径
        # 除非通过特定的开发者工具或正在运行的录屏会话
        logger.warning('警告: GNOME Wayland 环境下获取全局坐标受限')

    return None
