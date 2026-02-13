"""
主客户端模块

实现 Deskflow 客户端主逻辑，包括网络连接、消息处理循环和命令行参数解析。
"""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from ..pynergy_protocol import HelloBackMsg, HelloMsg, MsgID, PynergyParser
from .protocols import ClientProtocol, ClientState

if TYPE_CHECKING:
    from .dispatcher import MessageDispatcher


class PynergyClient(ClientProtocol):
    """Deskflow 客户端类

    负责连接服务器、接收消息并将输入事件注入系统。
    """

    def __init__(
        self,
        server: str,
        port: int = 24800,
        client_name: str = 'Pynergy',
        abs_mouse_move: bool = True,
        *,
        parser: PynergyParser,
        dispatcher: 'MessageDispatcher',
    ):
        """初始化客户端

        Args:
            server: 服务器 IP 地址
            port: 端口号 (默认: 24800)
            client_name: 客户端名称
        """
        self.server: str = server
        self.port: int = port
        self.name: str = client_name
        self.abs_mouse_move: bool = abs_mouse_move

        self.state: ClientState = ClientState.DISCONNECTED
        self.listen_task = None
        self.running = False

        self.reader = None
        self.writer = None

        self.parser: PynergyParser = parser
        self.dispatcher: 'MessageDispatcher' = dispatcher

    async def _connect(self) -> None:
        """连接 Deskflow 服务器并进行握手"""
        self.state = ClientState.CONNECTING
        logger.info(f'正在连接到 {self.server}:{self.port}...')
        # 1. 建立异步连接
        self.reader, self.writer = await asyncio.open_connection(self.server, self.port)

        # 2. 等待服务器 Hello (异步读取)
        logger.debug('等待服务器 Hello 消息...')
        data = await self.reader.read(1024)
        self.parser.feed(data)
        msg: HelloMsg | None = self.parser.next_handshake_msg(MsgID.Hello)
        logger.debug(f'服务器协议: {msg.protocol_name} {msg.major}.{msg.minor}')

        # 3. 发送 HelloBack (异步写入)
        logger.debug(f'发送 HelloBack，客户端名称: {self.name}')
        back_msg: HelloBackMsg = HelloBackMsg(msg.protocol_name, msg.major, msg.minor, self.name)
        self.writer.write(back_msg.pack_for_socket())
        await self.writer.drain()  # 确保数据真正发送出去了

        self.state = ClientState.CONNECTED
        logger.success(f'连接 Server {msg.protocol_name} {msg.major}.{msg.minor} 成功')

    async def run(self) -> None:
        """运行主事件循环"""
        await self._connect()

        self.running = True

        try:
            while self.running:
                # 这里的 read 也是非阻塞的
                data = await self.reader.read(4096)
                if not data:
                    break
                self.parser.feed(data)
                while True:
                    msg = self.parser.next_msg()
                    if msg is None:
                        break
                    await self.dispatcher.enqueue(msg, self)
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError) as e:
            logger.error(f'连接断开: {e}')
        except Exception as e:
            logger.error(f'处理消息时出错: {e}')
            raise
        finally:
            await self.close()

    async def send_message(self, data: bytes):
        """供 Handler 调用的回传方法"""
        if self.writer:
            self.writer.write(data)
            await self.writer.drain()

    async def close(self):
        # 1. 停止标志位
        self.running = False
        self.state = ClientState.DISCONNECTED

        # 1. 先断开网络流，停止“生产”
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f'关闭网络流时出错: {e}')
            self.writer = None
            self.reader = None

        self.dispatcher.handler.mouse.release_all_button()
        self.dispatcher.handler.mouse.close()
        self.dispatcher.handler.keyboard.close()

        logger.info('客户端资源已释放')

    async def stop(self):
        """优雅停止客户端"""
        logger.info('正在停止客户端...')
        self.running = False

        # 核心：关闭 writer 会导致 reader.read 立即从阻塞中恢复并返回 b''
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except ConnectionError:
                pass

        # 如果你希望立即杀死任务而不等 read 返回：
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
