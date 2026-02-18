import asyncio
import json
import platform
import sys
from dataclasses import fields, replace
from pathlib import Path
from typing import Annotated

import typer
from click.core import ParameterSource
from loguru import logger
from platformdirs import user_config_path, user_log_path
from pynergy_protocol import PynergyParser

from . import __version__
from .client.client import PynergyClient
from .client.dispatcher import MessageDispatcher
from .client.handlers import PynergyHandler
from .config import Available_Backends, Config, LogLevel
from .i18n import _
from .utils import init_backend, init_logger

app = typer.Typer(help=_('Pynergy Client'), add_completion=True)


def version_callback(value: bool):
    if value:
        # 这里可以直接 print，或者使用 typer.echo
        typer.echo(f'Pynergy Client Version: {__version__}')
        raise typer.Exit()


@app.command()
def main(
    ctx: typer.Context,
    config: Annotated[
        Path, typer.Option(help=_('Path to the configuration file'))
    ] = user_config_path(appname='pynergy', ensure_exists=True) / 'client-config.json',
    server: Annotated[
        str | None, typer.Option(help=_('Deskflow/Others server IP address'))
    ] = 'localhost',
    port: Annotated[int | None, typer.Option(help=_('Port number'))] = 24800,
    client_name: Annotated[str | None, typer.Option(help=_('Client name'))] = platform.node(),
    mouse_backend: Annotated[
        Available_Backends | None, typer.Option(help=_('Mouse backend'))
    ] = None,
    keyboard_backend: Annotated[
        Available_Backends | None, typer.Option(help=_('Keyboard backend'))
    ] = None,
    tls: Annotated[bool | None, typer.Option(help=_('Whether to use tls'))] = False,
    mtls: Annotated[bool | None, typer.Option(help=_('Whether to use mtls'))] = False,
    tls_trust: Annotated[bool | None, typer.Option(help=_('Whether to trust the server'))] = False,
    screen_width: Annotated[int | None, typer.Option(help=_('Screen width'))] = None,
    screen_height: Annotated[int | None, typer.Option(help=_('Screen height'))] = None,
    abs_mouse_move: Annotated[
        bool | None, typer.Option(help=_('Whether to use absolute displacement'))
    ] = False,
    mouse_move_threshold: Annotated[
        int | None, typer.Option(help=_('Unit: ms, balances smoothness and performance'))
    ] = 8,
    mouse_pos_sync_freq: Annotated[
        int | None,
        typer.Option(help=_('Sync frequency, sync with system real position every n moves')),
    ] = 2,
    logger_name: Annotated[str | None, typer.Option(help=_('Logger name'))] = 'Pynergy',
    log_dir: Annotated[str | None, typer.Option(help=_('Log directory location'))] = user_log_path(
        appname='pynergy', appauthor=False
    ),
    log_file: Annotated[str | None, typer.Option(help=_('Log file name'))] = 'pynergy.log',
    log_level_file: Annotated[LogLevel | None, typer.Option(help=_('File log level'))] = 'WARNING',
    log_level_stdout: Annotated[
        LogLevel | None, typer.Option(help=_('Console log level'))
    ] = 'INFO',
    version: Annotated[
        bool | None,
        typer.Option(
            '--version',
            '-v',
            help=_('Show the version and exit.'),
            callback=version_callback,
            is_eager=True,  # 确保在其他参数处理之前运行
        ),
    ] = None,
):
    """
    Launch the Pynergy client, which supports overriding JSON configurations via command-line arguments.
    The priority is CLI > config_file > default
    """

    # 1. Load the JSON configuration file
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('{}', encoding='utf-8')

    try:
        with open(config, 'r', encoding='utf-8') as f:
            json_dict = json.load(f)
    except json.JSONDecodeError:
        json_dict = {}

    # 2. Instantiate base configuration (filter invalid fields)
    valid_fields = {f.name for f in fields(Config)}
    filtered_json = {k: v for k, v in json_dict.items() if k in valid_fields}
    cfg = Config(**filtered_json)

    # 3. Collect the parameters passed in by the CLI (i.e. the non-non-none) part of locals())
    # Exclude parameters that are not Config fields, such as config_file
    cli_args = locals()
    overrides = {}
    for k in valid_fields:
        if k in cli_args:
            source = ctx.get_parameter_source(k)
            if source != ParameterSource.DEFAULT:
                overrides[k] = cli_args[k]

    # Override config
    cfg = replace(cfg, **overrides)

    # 4. Run app
    try:
        asyncio.run(run_app(cfg))
    except KeyboardInterrupt:
        typer.echo('\nService stopped')


async def run_app(cfg: Config):
    init_logger(cfg)
    logger.info(f'Logger initialized: {cfg.log_dir}/{cfg.log_file}')

    device_ctx, mouse, keyboard = init_backend(cfg)
    assert device_ctx and mouse and keyboard
    if not cfg.screen_width or not cfg.screen_height:
        device_ctx.update_screen_info()
        logger.info(
            f'Auto-detected screen size: {device_ctx.screen_size[0]}x{device_ctx.screen_size[1]}'
        )

    handler = PynergyHandler(cfg, device_ctx, mouse, keyboard)
    dispatcher = MessageDispatcher(handler)
    parser = PynergyParser()
    client = PynergyClient(
        cfg=cfg,
        parser=parser,
        dispatcher=dispatcher,
    )

    # 1. Start Worker
    # It will run all the time, waiting for messages in the queue
    worker_task = asyncio.create_task(dispatcher.worker(0))

    # 2. Start Client listening
    client.listen_task = asyncio.create_task(client.run())

    try:
        await client.listen_task
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info('Received interrupt signal, exiting...')
    except Exception as e:
        logger.error(f'Client error: {e}')
        sys.exit(1)
    finally:
        # 3. Stop all tasks
        await client.stop()
        worker_task.cancel()
