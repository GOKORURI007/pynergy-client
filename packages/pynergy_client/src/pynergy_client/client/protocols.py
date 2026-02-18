import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from pynergy_protocol import MsgBase, PynergyParser

if TYPE_CHECKING:
    from ..client.handlers import PynergyHandler


class ClientState(Enum):
    """Client state enumeration"""

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
    client: ClientProtocol  # Inject Client reference for easy callback


class DispatcherProtocol(Protocol):
    handler: 'PynergyHandler'
    queue: asyncio.Queue[MessageTask]

    async def enqueue(self, msg: MsgBase, client: ClientProtocol): ...

    async def worker(self, worker_id): ...
