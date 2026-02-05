"""
主客户端模块

实现 Synergy 客户端主逻辑，包括网络连接、消息处理循环和命令行参数解析。
"""

import logging
import socket
import sys
from typing import Optional

import click
from evdev import ecodes

from src.device import VirtualDevice
from src.protocol import SynergyProtocol
from src.protocol_types import MessageType

logger = logging.getLogger(__name__)


class SynergyClient:
    """Synergy 客户端类

    负责连接服务器、接收消息并将输入事件注入系统。
    """

    def __init__(
        self,
        server: str,
        port: int = 24800,
        coords_mode: str = 'relative',
        screen_width: int = 1920,
        screen_height: int = 1080,
        device: Optional[VirtualDevice] = None,
    ):
        """初始化客户端

        Args:
            server: 服务器 IP 地址
            port: 端口号 (默认: 24800)
            coords_mode: 坐标模式 ('relative' 或 'absolute')
            screen_width: 屏幕宽度 (用于相对位移计算)
            screen_height: 屏幕高度 (用于相对位移计算)
            device: 虚拟设备实例 (可选，默认自动创建)
        """
        self._server = server
        self._port = port
        self._coords_mode = coords_mode
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._device = device
        self._protocol = SynergyProtocol()
        self._sock: Optional[socket.socket] = None
        self._running = False
        self._last_x: Optional[int] = None
        self._last_y: Optional[int] = None

    @property
    def device(self) -> VirtualDevice:
        """获取虚拟设备"""
        if self._device is None:
            self._device = VirtualDevice()
        return self._device

    def connect(self) -> None:
        """连接 Synergy 服务器"""
        logger.info(f'正在连接到 {self._server}:{self._port}...')
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._server, self._port))
        logger.info('已连接，发送握手协议...')
        self._protocol.handshake(self._sock)
        logger.info('握手成功')

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
        device = self.device
        if msg_type == MessageType.DMMV:
            x, y = params['x'], params['y']
            if self._coords_mode == 'relative':
                dx, dy = self._abs_to_rel(x, y)
                device.write_mouse_move(dx, dy)
            else:
                self._write_mouse_abs(x, y)
        elif msg_type == MessageType.DKDN:
            device.write_key(params['key_code'], True)
        elif msg_type == MessageType.DKUP:
            device.write_key(params['key_code'], False)
        elif msg_type == MessageType.DMDN:
            device.write_key(params['button'], True)
        elif msg_type == MessageType.DMUP:
            device.write_key(params['button'], False)

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


@click.command()
@click.option(
    '--server',
    '-s',
    required=True,
    help='Synergy 服务器 IP 地址',
)
@click.option(
    '--port',
    '-p',
    default=24800,
    help='端口号 (默认: 24800)',
)
@click.option(
    '--coords-mode',
    type=click.Choice(['relative', 'absolute']),
    default='relative',
    help='坐标模式: relative=相对位移, absolute=绝对坐标',
)
@click.option(
    '--screen-width',
    type=int,
    default=1920,
    help='屏幕宽度 (用于相对位移计算, 默认: 1920)',
)
@click.option(
    '--screen-height',
    type=int,
    default=1080,
    help='屏幕高度 (用于相对位移计算, 默认: 1080)',
)
@click.option(
    '--verbose',
    '-v',
    count=True,
    help='详细输出 (可多次使用增加详细程度)',
)
def main(
    server: str,
    port: int,
    coords_mode: str,
    screen_width: int,
    screen_height: int,
    verbose: int,
) -> None:
    """PyDeskFlow - Synergy 客户端

    连接 Synergy 服务器并将输入事件注入系统。
    """
    log_level = logging.WARNING - verbose * 10
    logging.basicConfig(
        level=max(log_level, logging.DEBUG),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr,
    )

    logger.info(f'启动客户端，服务器: {server}:{port}, 坐标模式: {coords_mode}')

    try:
        client = SynergyClient(
            server=server,
            port=port,
            coords_mode=coords_mode,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        client.run()
    except KeyboardInterrupt:
        logger.info('收到中断信号，正在退出...')
    except Exception as e:
        logger.error(f'客户端错误: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
