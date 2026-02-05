"""
主客户端模块

实现 Deskflow 客户端主逻辑，包括网络连接、消息处理循环和命令行参数解析。
"""

import os
import socket
import struct
from typing import Optional

from evdev import ecodes
from loguru import logger

from src.device import VirtualDevice
from src.protocol import SynergyProtocol
from src.protocol_types import ClientState, MessageType


# from loguru import logger


def get_screen_size() -> tuple[int, int]:
    """获取屏幕尺寸

    尝试从环境变量或 X11 获取屏幕尺寸，如果都失败则使用默认值。

    Returns:
        (width, height) 屏幕宽度和高度
    """
    try:
        import subprocess

        result = subprocess.run(
            ['xrandr', '--current', '--query'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.split('\n'):
            if '*' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == '*':
                        continue
                    try:
                        width, height = part.split('x')
                        return int(width), int(height)
                    except (ValueError, IndexError):
                        continue
    except (FileNotFoundError, Exception):
        pass

    env_width = os.environ.get('SCREEN_WIDTH')
    env_height = os.environ.get('SCREEN_HEIGHT')
    if env_width and env_height:
        return int(env_width), int(env_height)

    return 1920, 1080


class SynergyClient:
    """Deskflow 客户端类

    负责连接服务器、接收消息并将输入事件注入系统。
    """

    def __init__(
        self,
        server: str,
        port: int = 24800,
        coords_mode: str = 'relative',
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        client_name: str = 'Pynergy',
        device: Optional[VirtualDevice] = None,
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
        self._server = server
        self._port = port
        self._coords_mode = coords_mode
        self._client_name = client_name

        if screen_width is None or screen_height is None:
            screen_width, screen_height = get_screen_size()
        self._screen_width = screen_width
        self._screen_height = screen_height

        self._device = device
        self._protocol = SynergyProtocol()
        self._sock: Optional[socket.socket] = None
        self._running = False
        self._state = ClientState.DISCONNECTED
        self._last_x: Optional[int] = None
        self._last_y: Optional[int] = None
        self._pressed_keys: set[int] = set()

    @property
    def device(self) -> VirtualDevice:
        """获取虚拟设备"""
        if self._device is None:
            self._device = VirtualDevice()
        return self._device

    def connect(self) -> None:
        """连接 Deskflow 服务器并进行握手"""
        self._state = ClientState.CONNECTING
        logger.info(f'正在连接到 {self._server}:{self._port}...')
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._server, self._port))

        self._state = ClientState.HANDSHAKE
        logger.info('等待服务器 Hello 消息...')
        msg = self._protocol.recv_message(self._sock)

        server_major, server_minor, protocol_name = self._parse_hello_message(msg)
        logger.info(f'服务器协议: {protocol_name} {server_major}.{server_minor}')

        logger.info(f'发送 HelloBack，客户端名称: {self._client_name}')
        hello_back = self._build_hello_back(protocol_name, server_major, server_minor)
        self._sock.send(hello_back)

        self._state = ClientState.CONNECTED
        logger.info('握手完成，进入 Connected 状态')

    def _parse_hello_message(self, msg: bytes) -> tuple[int, int, str]:
        """解析 Hello 消息

        Hello 消息格式: ProtocolName + major(2) + minor(2)
        例如: b'Barrier\x00\x01\x00\x08' 或 b'Deskflow\x00\x01\x00\x06'

        Args:
            msg: 原始消息字节

        Returns:
            (major, minor, protocol_name) 版本号和协议名称
        """
        if len(msg) < 11:
            raise ValueError(f'Hello 消息长度不足: {len(msg)}')

        protocol_names = [b'Deskflow', b'Barrier', b'Synergy']
        protocol_name = None
        protocol_len = 0
        for name in protocol_names:
            if msg.startswith(name):
                protocol_name = name.decode('utf-8')
                protocol_len = len(name)
                break

        if protocol_name is None:
            raise ValueError(f'未知的协议名称: {msg[:8]}')

        major, minor = struct.unpack('>HH', msg[protocol_len: protocol_len + 4])
        return major, minor, protocol_name

    def _build_hello_back(self, protocol_name: str, major: int, minor: int) -> bytes:
        """构建 HelloBack 消息

        HelloBack 格式: ProtocolName + major(2) + minor(2) + nameLen(4) + name
        例如: b'Barrier\x00\x01\x00\x08\x00\x00\x00\x0bworkstation'

        Args:
            protocol_name: 协议名称
            major: 主版本号
            minor: 次版本号

        Returns:
            HelloBack 消息字节
        """
        name_bytes = self._client_name.encode('utf-8')
        name_len = struct.pack('>I', len(name_bytes))
        msg = (
            protocol_name.encode('utf-8') + struct.pack('>HH', major, minor) + name_len + name_bytes
        )
        header = struct.pack('>I', len(msg))
        return header + msg

    def run(self) -> None:
        """运行主事件循环"""
        if self._sock is None:
            self.connect()
        assert self._sock is not None

        self._running = True
        logger.info('开始处理消息...')

        try:
            while self._running:
                msg = self._protocol.recv_message(self._sock)
                msg_type, params = self._protocol.parse_message(msg)
                self._handle_message(msg_type, params)
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.error(f'连接断开: {e}')
        except Exception as e:
            logger.error(f'处理消息时出错: {e}')
            raise
        finally:
            self.close()

    def _handle_message(self, msg_type: MessageType, params: dict) -> None:
        """处理消息

        Args:
            msg_type: 消息类型
            params: 消息参数
        """
        if msg_type == MessageType.QINF:
            logger.info('收到 QINF 查询屏幕信息，发送 DINF')
            dinf = self._protocol.build_dinf(
                self._screen_width,
                self._screen_height,
                0,
                0,
            )
            assert self._sock is not None
            self._sock.send(dinf)
            return

        elif msg_type == MessageType.CINN:
            logger.info(f'进入屏幕，位置: ({params["x"]}, {params["y"]})')
            self._state = ClientState.ACTIVE
            modifiers = params.get('modifiers', 0)
            self._sync_modifiers(modifiers)
            self._last_x = None
            self._last_y = None
            return

        elif msg_type == MessageType.COUT:
            logger.info('离开屏幕')
            self._state = ClientState.CONNECTED
            self._release_all_keys()
            return

        elif msg_type == MessageType.CALV:
            logger.debug('收到心跳，响应 CALV')
            assert self._sock is not None
            self._sock.send(self._protocol.build_calv())
            return

        elif msg_type == MessageType.CBYE:
            logger.info('收到关闭连接消息')
            self._running = False
            return

        elif msg_type == MessageType.EICV:
            reason = params.get('reason', 0)
            logger.error(f'版本不兼容错误: {reason}')
            self._running = False
            return

        elif msg_type == MessageType.EBSY:
            logger.error('服务器忙')
            self._running = False
            return

        if self._state != ClientState.ACTIVE:
            logger.debug(f'忽略消息 {msg_type}，当前状态: {self._state}')
            return

        device = self.device

        if msg_type == MessageType.DMMV:
            x, y = params['x'], params['y']
            if self._coords_mode == 'relative':
                dx, dy = self._abs_to_rel(x, y)
                if dx != 0 or dy != 0:
                    device.write_mouse_move(dx, dy)
            else:
                self._write_mouse_abs(x, y)

        elif msg_type == MessageType.DMRM:
            dx, dy = params['dx'], params['dy']
            if dx != 0 or dy != 0:
                device.write_mouse_move(dx, dy)

        elif msg_type == MessageType.DKDN:
            key_code = params['key_code']
            self._pressed_keys.add(key_code)
            device.write_key(key_code, True)

        elif msg_type == MessageType.DKUP:
            key_code = params['key_code']
            self._pressed_keys.discard(key_code)
            device.write_key(key_code, False)

        elif msg_type == MessageType.DMDN:
            button = params['button']
            device.write_key(button, True)

        elif msg_type == MessageType.DMUP:
            button = params['button']
            device.write_key(button, False)

        elif msg_type == MessageType.DMWM:
            x = params.get('x', 0)
            y = params.get('y', 0)
            if y != 0:
                device.write(ecodes.EV_REL, ecodes.REL_WHEEL, y)
            if x != 0:
                device.write(ecodes.EV_REL, ecodes.REL_HWHEEL, x)

        elif msg_type == MessageType.DKRP:
            key_code = params['key_code']
            if key_code not in self._pressed_keys:
                self._pressed_keys.add(key_code)
                device.write_key(key_code, True)

        device.syn()

    def _sync_modifiers(self, modifiers: int) -> None:
        """同步修饰键状态

        Args:
            modifiers: 修饰键位掩码
        """
        pass

    def _release_all_keys(self) -> None:
        """释放所有按下的键"""
        device = self.device
        for key_code in list(self._pressed_keys):
            device.write_key(key_code, False)
            self._pressed_keys.discard(key_code)
        device.syn()

    def _abs_to_rel(self, x: int, y: int) -> tuple[int, int]:
        """将 Synergy 绝对坐标转换为相对位移

        Args:
            x: 0-65535 范围的绝对坐标
            y: 0-65535 范围的绝对坐标

        Returns:
            (dx, dy) 相对位移
        """
        if self._last_x is None or self._last_y is None:
            self._last_x, self._last_y = x, y
            return 0, 0

        dx = int((x - self._last_x) * (self._screen_width / 65535))
        dy = int((y - self._last_y) * (self._screen_height / 65535))

        self._last_x, self._last_y = x, y
        return dx, dy

    def _write_mouse_abs(self, x: int, y: int) -> None:
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
        self._running = False
        self._state = ClientState.DISCONNECTED
        if self._sock:
            self._sock.close()
            self._sock = None
        if self._device:
            self._device.close()
            self._device = None
        logger.info('客户端已关闭')

    def stop(self) -> None:
        """停止客户端"""
        self._running = False
