import asyncio
import inspect
from typing import Any

from loguru import logger

from packages.pynergy_protocol.src.pynergy_protocol import MsgID

from .handlers import PynergyHandler
from .protocols import ClientProtocol, DispatcherProtocol, MessageTask


class MessageDispatcher(DispatcherProtocol):
    def __init__(self, handler: PynergyHandler):
        self.handler = handler
        self.queue = asyncio.Queue(maxsize=100)

        self._handler_map = self._build_handler_map()
        self.default_handler = getattr(
            self.handler, 'default_handler', self.handler.default_handler
        )

        self.last_move_time = 0
        self.throttle_interval = 0.016  # Approximately 60fps sampling rate

    def _build_handler_map(self) -> dict:
        """Scan all methods in handler instance that start with on_"""
        mapping = {}
        for name, method in inspect.getmembers(self.handler, predicate=callable):
            if name.startswith('on_'):
                # Extract protocol code part, e.g. "on_hello" -> "hello"
                msg_code = name[3:].upper()
                if msg_code == 'HELLO':
                    msg_code = 'Hello'
                if msg_code == 'HELLOBACK':
                    msg_code = 'HelloBack'
                assert msg_code in MsgID.__members__, f'{msg_code} is not a valid message code'
                mapping[msg_code] = method

        logger.opt(lazy=True).debug(
            '{log}',
            log=lambda: (
                f'{self.__class__} loaded {len(mapping)} handler functions: {list(mapping.keys())}'
            ),
        )
        return mapping

    async def enqueue(self, msg: Any, client: ClientProtocol):
        handler = self._handler_map.get(msg.CODE, self.default_handler)
        task = MessageTask(handler, msg, client)
        await self.queue.put(task)

    async def worker(self, worker_id):
        """Consumer: Take tasks from queue and execute"""
        while True:
            task = await self.queue.get()
            try:
                # Execute Handler and pass client
                await task.handler(task.msg, task.client)
            except Exception as e:
                print(f'Worker-{worker_id} Error: {e}')
            finally:
                self.queue.task_done()
