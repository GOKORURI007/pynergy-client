import asyncio
import inspect

from loguru import logger

from ..pynergy_protocol import MsgBase, MsgID
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
        self.throttle_interval = 0.016  # 约 60fps 的采样率

    def _build_handler_map(self) -> dict:
        """扫描 handler 实例中所有以 on_ 开头的方法"""
        mapping = {}
        for name, method in inspect.getmembers(self.handler, predicate=callable):
            if name.startswith('on_'):
                # 提取协议代码部分，例如 "on_hello" -> "hello"
                msg_code = name[3:].upper()
                if msg_code == 'HELLO':
                    msg_code = 'Hello'
                if msg_code == 'HELLOBACK':
                    msg_code = 'HelloBack'
                assert msg_code in MsgID.__members__, f'{msg_code} 不是一个有效的消息代码'
                mapping[msg_code] = method

        logger.debug(f'f{self.__class__} 已加载 {len(mapping)} 个处理函数: {list(mapping.keys())}')
        return mapping

    async def enqueue(self, msg: MsgBase, client: ClientProtocol):
        handler = self._handler_map.get(msg.CODE)
        task = MessageTask(handler, msg, client)
        await self.queue.put(task)

    async def worker(self, worker_id):
        """消费者：从队列取任务并执行"""
        while True:
            task = await self.queue.get()
            try:
                # 执行 Handler，并将 client 传入
                await task.handler(task.msg, task.client)
            except Exception as e:
                print(f'Worker-{worker_id} Error: {e}')
            finally:
                self.queue.task_done()
