"""
主客户端模块

实现 Deskflow 客户端主逻辑，包括网络连接、消息处理循环和命令行参数解析。
"""

import socket

from evdev import ecodes
from loguru import logger

from ..device import VirtualDevice
from ..protocol import HelloBackMsg, HelloMsg, MsgID, SynergyParser
from ..utils import get_screen_size
from .client_types import ClientProtocol, ClientState
from .handlers import MessageDispatcher, PynergyHandler


class SynergyClient(ClientProtocol):
    """Deskflow 客户端类

    负责连接服务器、接收消息并将输入事件注入系统。
    """

    def __init__(
        self,
        server: str,
        port: int = 24800,
        coords_mode: str = 'relative',
        screen_width: int | None = None,
        screen_height: int | None = None,
        client_name: str = 'Pynergy',
        device: VirtualDevice | None = None,
    ):
        """初始化客户端

        Args:
            server: 服务器 IP 地址
            port: 端口号 (默认: 24800)
            coords_mode: 坐标模式 ('relative' 或 'absolute')
            screen_width: 屏幕宽度 (可选，默认自动获取)
            screen_height: 屏幕高度 (可选，默认自动获取)
            client_name: 客户端名称
            device: 虚拟设备实例 (可选，默认自动创建)
        """
        self.server: str = server
        self.port: int = port
        self.coords_mode: str = coords_mode
        self.name: str = client_name

        if screen_width is None or screen_height is None:
            screen_width, screen_height = get_screen_size()
        self.screen_width: int = screen_width
        self.screen_height: int = screen_height

        self.sock: socket.socket | None = None
        self.state: ClientState = ClientState.DISCONNECTED
        self._device = device
        self.running = False
        self.last_x: int | None = None
        self.last_y: int | None = None
        self.pressed_keys: set[int] = set()

        self.parser: SynergyParser = SynergyParser()
        self.handler: PynergyHandler = PynergyHandler(self)
        self.dispatcher: MessageDispatcher = MessageDispatcher(self.handler)

    @property
    def device(self) -> VirtualDevice:
        """获取虚拟设备"""
        if self._device is None:
            self._device = VirtualDevice()
        return self._device

    def connect(self) -> None:
        """连接 Deskflow 服务器并进行握手"""
        self.state = ClientState.CONNECTING
        logger.info(f'正在连接到 {self.server}:{self.port}...')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server, self.port))

        self.state = ClientState.HANDSHAKE
        logger.debug('等待服务器 Hello 消息...')
        data: bytes = self.sock.recv(1024)
        self.parser.feed(data)
        msg: HelloMsg | None = self.parser.next_handshake_msg(MsgID.Hello)
        logger.debug(f'服务器协议: {msg.protocol_name} {msg.major}.{msg.minor}')

        logger.info(f'发送 HelloBack，客户端名称: {self.name}')
        back_msg: HelloBackMsg = HelloBackMsg(msg.protocol_name, msg.major, msg.minor, self.name)
        self.sock.sendall(back_msg.pack_for_socket())

        self.state = ClientState.CONNECTED
        logger.success('握手完成，进入 Connected 状态')

    def run(self) -> None:
        """运行主事件循环"""
        if self.sock is None:
            self.connect()
        assert self.sock is not None

        self.running = True
        logger.info('开始处理消息...')

        try:
            while self.running:
                data = self.sock.recv(4096)
                if not data:
                    break
                self.parser.feed(data)
                while True:
                    msg = self.parser.next_msg()
                    if msg is None:
                        break
                    logger.debug(f'收到消息: {msg}')
                    self.dispatcher.dispatch(msg)
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.error(f'连接断开: {e}')
        except Exception as e:
            logger.error(f'处理消息时出错: {e}')
            raise
        finally:
            self.close()

    def sync_modifiers(self, modifiers: int) -> None:
        """同步修饰键状态

        Args:
            modifiers: 修饰键位掩码
        """
        pass

    def release_all_keys(self) -> None:
        """释放所有按下的键"""
        device = self.device
        for key_code in list(self.pressed_keys):
            device.write_key(key_code, False)
            self.pressed_keys.discard(key_code)
        device.syn()

    def abs_to_rel(self, x: int, y: int) -> tuple[int, int]:
        """将 Synergy 绝对坐标转换为相对位移

        Args:
            x: 0-65535 范围的绝对坐标
            y: 0-65535 范围的绝对坐标

        Returns:
            (dx, dy) 相对位移
        """
        if self.last_x is None or self.last_y is None:
            self.last_x, self.last_y = x, y
            return 0, 0

        dx = int((x - self.last_x) * (self.screen_width / 65535))
        dy = int((y - self.last_y) * (self.screen_height / 65535))

        self.last_x, self.last_y = x, y
        return dx, dy

    def write_mouse_abs(self, x: int, y: int) -> None:
        """写入绝对坐标

        Args:
            x: X 坐标 (0-65535)
            y: Y 坐标 (0-65535)
        """
        device = self.device
        device.write(ecodes.EV_ABS, ecodes.ABS_X, x)
        device.write(ecodes.EV_ABS, ecodes.ABS_Y, y)

    def close(self) -> None:
        """关闭连接和设备"""
        self.running = False
        self.state = ClientState.DISCONNECTED
        if self.sock:
            self.sock.close()
            self.sock = None
        if self._device:
            self._device.close()
            self._device = None
        logger.info('客户端已关闭')

    def stop(self) -> None:
        """停止客户端"""
        self.running = False
