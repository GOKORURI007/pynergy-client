import json
import sys
from dataclasses import fields
from pathlib import Path

import click
from loguru import logger
from platformdirs import user_config_path

from src.client.connection import PynergyClient, get_screen_size
from src.config import Config
from src.utils import init_logger


@click.command()
@click.option(
    '--server',
    '-s',
    type=str,
    default=None,
    help='Deskflow 服务器 IP 地址',
)
@click.option(
    '--port',
    '-p',
    type=int,
    default=None,
    help='端口号 (默认: 24800)',
)
@click.option(
    '--client-name',
    '-n',
    default=None,
    help='客户端名称 (默认: Pynergy)',
)
@click.option(
    '--screen-width',
    type=int,
    default=None,
    help='屏幕宽度 (用于相对位移计算, 默认: 自动获取)',
)
@click.option(
    '--screen-height',
    type=int,
    default=None,
    help='屏幕高度 (用于相对位移计算, 默认: 自动获取)',
)
@click.option(
    '--logger-name',
    default=None,
    help='客户端名称 (默认: Pynergy)',
)
@click.option(
    '--log-dir',
    default=None,
    help='客户端名称 (默认: Pynergy)',
)
@click.option(
    '--log-file',
    default=None,
    help='客户端名称 (默认: Pynergy)',
)
@click.option(
    '--log-level-file',
    default=None,
    help='客户端名称 (默认: Pynergy)',
)
@click.option(
    '--log-level-stdout',
    default=None,
    help='客户端名称 (默认: Pynergy)',
)
@click.option(
    '--config',
    '-c',
    default=user_config_path(appname='pynergy', ensure_exists=True) / 'config.json',
    help='坐标模式 (relative 或 absolute, 默认: relative)',
)
def main(
    server: str | None,
    port: int | None,
    client_name: str | None,
    screen_width: int | None,
    screen_height: int | None,
    logger_name: str | None,
    log_dir: str | None,
    log_file: str | None,
    log_level_file: str | None,
    log_level_stdout: str | None,
    config: str,
) -> None:
    """Pynergy - Deskflow 客户端

    连接 Deskflow 服务器并将输入事件注入系统。
    """

    if not Path(config).exists():
        with open(config, 'w+', encoding='utf-8') as f:
            f.write('{}')

    with open(config, 'r', encoding='utf-8') as f:
        json_dict = json.load(f)

    # 1. 获取 dataclass 的所有字段名
    valid_fields = {f.name for f in fields(Config)}

    # 2. 过滤字典：只保留 dataclass 中存在的键
    filtered_data = {k: v for k, v in json_dict.items() if k in valid_fields}

    # 3. 实例化：未提供的 'city' 和 'is_active' 将保留默认值
    cfg = Config(**filtered_data)

    init_logger(
        name=logger_name if logger_name else cfg.logger_name,
        log_dir=log_dir if log_dir else cfg.log_dir,
        log_file=log_file if log_file else cfg.log_file,
        log_level_stdout=log_level_stdout if log_level_stdout else cfg.log_level_stdout,
        log_level_file=log_level_file if log_level_file else cfg.log_level_file,
    )

    if (screen_width is None or screen_height is None) and (
        cfg.screen_width is None or cfg.screen_height
    ):
        screen_width, screen_height = get_screen_size()
        logger.info(f'自动获取屏幕尺寸: {screen_width}x{screen_height}')

    logger.info(f'启动客户端，服务器: {server}:{port}, 客户端名称: {client_name}')

    try:
        client = PynergyClient(
            server=server if server else cfg.server,
            port=port if port else cfg.port,
            screen_width=screen_width if screen_width else cfg.screen_width,
            screen_height=screen_height if screen_height else cfg.screen_height,
            client_name=client_name if client_name else cfg.client_name,
        )
        client.run()
    except KeyboardInterrupt:
        logger.info('收到中断信号，正在退出...')
    except Exception as e:
        logger.error(f'客户端错误: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
