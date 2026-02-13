import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ..pynergy_protocol import MsgBase, PynergyParser


class ClientState(Enum):
    """客户端状态枚举"""

    DISCONNECTED = 0
    CONNECTING = 1
    HANDSHAKE = 2
    CONNECTED = 3
    ACTIVE = 4
    INACTIVE = 5


class ClientProtocol(Protocol):
    server: str
    port: int
    name: str
    abs_mouse_move: bool

    state: ClientState
    listen_task: asyncio.Task | None
    running: bool

    reader: asyncio.StreamReader | None
    writer: asyncio.StreamWriter | None

    parser: PynergyParser
    dispatcher: 'DispatcherProtocol'

    async def _connect(self) -> None: ...

    async def run(self) -> None: ...

    async def send_message(self, data: bytes): ...

    async def close(self): ...

    async def stop(self): ...


class HandlerMethod(Protocol):
    async def __call__(self, msg: MsgBase, client: ClientProtocol) -> None: ...


@dataclass
class MessageTask:
    handler: HandlerMethod
    msg: MsgBase
    client: ClientProtocol  # 注入 Client 引用，方便回传


class DispatcherProtocol(Protocol):
    queue: asyncio.Queue[MessageTask]

    async def enqueue(self, msg: MsgBase, client: ClientProtocol) -> MessageTask: ...

    async def worker(self, worker_id): ...
