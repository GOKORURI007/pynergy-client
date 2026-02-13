import asyncio
import json
import sys
from dataclasses import fields, replace
from pathlib import Path

import click
from loguru import logger
from platformdirs import user_config_path

from .client.client import PynergyClient
from .client.dispatcher import MessageDispatcher
from .client.handlers import PynergyHandler
from .config import Available_Backends, Config
from .pynergy_protocol import PynergyParser
from .utils import init_backend, init_logger


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
    '--abs-mouse-move',
    type=bool,
    default=None,
    help='是否采用绝对位移',
)
@click.option(
    '--mouse-backend',
    type=Available_Backends,
    default=None,
    help='屏幕宽度 (用于相对位移计算, 默认: 自动获取)',
)
@click.option(
    '--keyboard-backend',
    type=Available_Backends,
    default=None,
    help='屏幕宽度 (用于相对位移计算, 默认: 自动获取)',
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
def main(config: str, **kwargs) -> None:
    """Pynergy - Deskflow 客户端"""

    # --- 1. 加载并实例化基础配置 ---
    config_path = Path(config)
    if not config_path.exists():
        config_path.write_text('{}', encoding='utf-8')

    with open(config_path, 'r', encoding='utf-8') as f:
        json_dict = json.load(f)

    # 只从 JSON 中提取 Config 类存在的字段
    valid_fields = {f.name for f in fields(Config)}
    filtered_json = {k: v for k, v in json_dict.items() if k in valid_fields}

    # 实例化初始配置
    cfg = Config(**filtered_json)

    # --- 2. 使用 kwargs 覆盖 ---
    # kwargs 包含了所有 click 传入的参数（但不包含已被提取的 config）
    # 过滤掉 None 值，以及 Config 类中不存在的参数
    actual_overrides = {k: v for k, v in kwargs.items() if v is not None and k in valid_fields}

    # 一键覆盖
    cfg = replace(cfg, **actual_overrides)

    # 启动异步事件循环
    try:
        asyncio.run(run_app(cfg))
    except KeyboardInterrupt:
        pass


async def run_app(cfg: Config):
    init_logger(cfg)
    logger.info(f'日志记录器已初始化: {cfg.log_dir}/{cfg.log_file}')

    device_ctx, mouse, keyboard = init_backend(cfg)
    if not cfg.screen_width or not cfg.screen_height:
        device_ctx.update_screen_info()
        logger.info(f'自动获取屏幕尺寸: {device_ctx.screen_size[0]}x{device_ctx.screen_size[1]}')

    handler = PynergyHandler(device_ctx, mouse, keyboard)
    dispatcher = MessageDispatcher(handler)
    parser = PynergyParser()
    client = PynergyClient(
        server=cfg.server,
        port=cfg.port,
        client_name=cfg.client_name,
        abs_mouse_move=cfg.abs_mouse_move,
        parser=parser,
        dispatcher=dispatcher,
    )

    # 1. 启动消费者 (Worker)
    # 它会一直运行，等待队列里的消息
    worker_task = asyncio.create_task(dispatcher.worker(0))

    # 2. 启动生产者 (Client 监听)
    # 它会一直运行，直到断开连接
    client.listen_task = asyncio.create_task(client.run())

    try:
        await client.listen_task
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info('收到中断信号，正在退出...')
    except Exception as e:
        logger.error(f'客户端错误: {e}')
        sys.exit(1)
    finally:
        # 3. 停止所有任务
        await client.stop()  # 内部调用 close()
        worker_task.cancel()  # 停止 Worker
