import asyncio
import json
import sys
from dataclasses import fields, replace
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from platformdirs import user_config_path

from .client.client import PynergyClient
from .client.dispatcher import MessageDispatcher
from .client.handlers import PynergyHandler
from .config import Available_Backends, Config, LogLevel
from .pynergy_protocol import PynergyParser
from .utils import init_backend, init_logger

app = typer.Typer(help="Pynergy - Deskflow 客户端", add_completion=False)


@app.command()
def main(
    # 配置文件路径
    config: Annotated[
        Path,
        typer.Option(help="配置文件路径")
    ] = user_config_path(appname='pynergy', ensure_exists=True) / 'client-config.json',

    # 网络配置
    server: Annotated[
        str | None,
        typer.Option(help="Deskflow 服务器 IP")
    ] = None,
    port: Annotated[
        int | None,
        typer.Option(help="端口号")
    ] = None,
    client_name: Annotated[
        str | None,
        typer.Option(help="客户端名称")
    ] = None,

    # 屏幕与后端
    mouse_backend: Annotated[
        Available_Backends | None, typer.Option(help="鼠标驱动后端")
    ] = None,
    keyboard_backend: Annotated[
        Available_Backends | None, typer.Option(help="键盘驱动后端")
    ] = None,
    screen_width: Annotated[int | None, typer.Option(help="屏幕宽度")] = None,
    screen_height: Annotated[int | None, typer.Option(help="屏幕高度")] = None,

    # 处理器参数
    abs_mouse_move: Annotated[bool | None, typer.Option(help="是否采用绝对位移")] = None,
    mouse_move_threshold: Annotated[
        int | None, typer.Option(help="单位 ms，约 125Hz，可以平衡平滑度和性能")
    ] = None,
    mouse_pos_sync_freq: Annotated[
        int | None, typer.Option(help="同步频率，每移动 n 次与系统同步鼠标真实位置")
    ] = None,

    # 日志参数
    logger_name: Annotated[str | None, typer.Option(help="Logger 名称")] = None,
    log_dir: Annotated[str | None, typer.Option(None, help="Log 目录位置")] = None,
    log_file: Annotated[str | None, typer.Option(help="Log 文件名词")] = None,
    log_level_file: Annotated[LogLevel | None, typer.Option(help="文件日志级别")] = None,
    log_level_stdout: Annotated[LogLevel | None, typer.Option(help="控制台日志级别")] = None,
):
    """
        启动 Pynergy 客户端，支持通过命令行参数覆盖 JSON 配置。
        """

    # 1. 加载 JSON 配置文件
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('{}', encoding='utf-8')

    try:
        with open(config, 'r', encoding='utf-8') as f:
            json_dict = json.load(f)
    except json.JSONDecodeError:
        json_dict = {}

    # 2. 实例化基础配置 (过滤无效字段)
    valid_fields = {f.name for f in fields(Config)}
    filtered_json = {k: v for k, v in json_dict.items() if k in valid_fields}
    cfg = Config(**filtered_json)

    # 3. 收集 CLI 传入的参数 (即 locals() 中不为 None 的部分 )
    # 排除掉非 Config 字段的参数，如 config_file
    cli_args = locals()
    overrides = {
        k: cli_args[k]
        for k in valid_fields
        if k in cli_args and cli_args[k] is not None
    }

    # 执行覆盖
    cfg = replace(cfg, **overrides)

    # 4. 运行应用
    try:
        asyncio.run(run_app(cfg))
    except KeyboardInterrupt:
        typer.echo("\n已停止服务")


async def run_app(cfg: Config):
    init_logger(cfg)
    logger.info(f'日志记录器已初始化: {cfg.log_dir}/{cfg.log_file}')

    device_ctx, mouse, keyboard = init_backend(cfg)
    assert device_ctx and mouse and keyboard
    if not cfg.screen_width or not cfg.screen_height:
        device_ctx.update_screen_info()
        logger.info(f'自动获取屏幕尺寸: {device_ctx.screen_size[0]}x{device_ctx.screen_size[1]}')

    handler = PynergyHandler(cfg, device_ctx, mouse, keyboard)
    dispatcher = MessageDispatcher(handler)
    parser = PynergyParser()
    client = PynergyClient(
        server=cfg.server,
        port=cfg.port,
        client_name=cfg.client_name,
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
