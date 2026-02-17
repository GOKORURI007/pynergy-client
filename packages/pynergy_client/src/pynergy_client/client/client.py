"""
Main client module

Implements the main logic of the Pynergy client, including network connection,
message processing loop, and command-line argument parsing.
"""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from packages.pynergy_protocol.src.pynergy_protocol import (
    HelloBackMsg,
    HelloMsg,
    MsgID,
    PynergyParser,
)

from .. import config
from ..utils import setup_ssl_context, validate_cert
from .protocols import ClientProtocol, ClientState, DispatcherProtocol

if TYPE_CHECKING:
    from .dispatcher import MessageDispatcher


class PynergyClient(ClientProtocol):
    """Deskflow client class

    Responsible for connecting to the server, receiving messages,
    and injecting input events into the system.
    """

    def __init__(
        self,
        cfg: config.Config,
        *,
        parser: PynergyParser,
        dispatcher: 'MessageDispatcher',
    ):
        """Initialize the client"""
        self.cfg = cfg

        self.state: ClientState = ClientState.DISCONNECTED
        self.listen_task = None
        self.running = False

        self.reader = None
        self.writer = None

        self.parser: PynergyParser = parser
        self.dispatcher: DispatcherProtocol = dispatcher

    async def _connect(self) -> None:
        """Connect to Deskflow server and perform handshake"""
        self.state = ClientState.CONNECTING
        logger.info(f'Connecting to {self.cfg.server}:{self.cfg.port}...')
        # 1. Establish async connection
        context = setup_ssl_context(self.cfg)
        self.reader, self.writer = await asyncio.open_connection(
            self.cfg.server, self.cfg.port, ssl=context
        )
        await validate_cert(self.writer, self.cfg)
        # 2. Wait for server Hello (async read)
        logger.debug('Waiting for server Hello message...')
        data = await asyncio.wait_for(self.reader.read(1024), timeout=10.0)
        self.parser.feed(data)
        msg: HelloMsg | None = self.parser.next_handshake_msg(MsgID.Hello)
        assert msg, 'Did not receive server Hello message'
        logger.debug(f'Server protocol: {msg.protocol_name} {msg.major}.{msg.minor}')

        # 3. Send HelloBack (async write)
        logger.debug(f'Sending HelloBack, client name: {self.cfg.client_name}')
        back_msg: HelloBackMsg = HelloBackMsg(
            msg.protocol_name, msg.major, msg.minor, self.cfg.client_name
        )
        self.writer.write(back_msg.pack_for_socket())
        await self.writer.drain()  # Ensure data is actually sent

        self.state = ClientState.CONNECTED
        logger.success(
            f'Connected to Server {msg.protocol_name} {msg.major}.{msg.minor} successfully'
        )

    async def run(self) -> None:
        """Run the main event loop"""
        await self._connect()
        self.running = True

        try:
            assert self.reader, 'Reader not initialized'
            while self.running:
                # The read here is also non-blocking
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
            logger.error(f'Connection lost: {e}')
        except Exception as e:
            logger.error(f'Error processing message: {e}')
            raise
        finally:
            await self.close()

    async def send_message(self, data: bytes):
        """Callback method for handlers to send messages back"""
        if self.writer:
            self.writer.write(data)
            await self.writer.drain()

    async def close(self):
        # 1. Stop flags
        self.running = False
        self.state = ClientState.DISCONNECTED

        # 2. Disconnect network stream first, stop "production"
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f'Error closing network stream: {e}')
            self.writer = None
            self.reader = None

        self.dispatcher.handler.mouse.release_all_button()
        self.dispatcher.handler.mouse.close()
        self.dispatcher.handler.keyboard.close()

        logger.info('Client resources released')

    async def stop(self):
        """Gracefully stop the client"""
        logger.info('Stopping client...')
        self.running = False

        # Key: closing writer causes reader.read to immediately return from blocking with b''
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except ConnectionError:
                pass

        # If you want to kill the task immediately without waiting for read to return:
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
