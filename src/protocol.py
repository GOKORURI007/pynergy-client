"""
Synergy 协议解析模块

实现 Synergy/Barrier 协议消息的接收、解析和封装。
"""

import socket
import struct

from src.protocol_types import MessageType, ParsedMessage


class SynergyProtocol:
    """Synergy 协议解析类

    负责 Synergy 协议消息的收发和解析。
    """

    def __init__(self, protocol_version: int = 1, major_version: int = 6):
        """初始化协议

        Args:
            protocol_version: 协议版本号
            major_version: 主版本号
        """
        self._protocol_version = protocol_version
        self._major_version = major_version

    def build_handshake(self) -> bytes:
        """构建握手消息

        Returns:
            握手消息字节
        """
        msg = b'Synergy' + struct.pack('>HH', self._protocol_version, self._major_version)
        header = struct.pack('>I', len(msg))
        return header + msg

    def handshake(self, sock: socket.socket) -> None:
        """发送握手协议

        Args:
            sock: TCP 套接字
        """
        msg = self.build_handshake()
        sock.send(msg)

    def recv_message(self, sock: socket.socket) -> bytes:
        """接收消息

        先读取 4 字节长度头部，再读取对应长度的消息体。

        Args:
            sock: TCP 套接字

        Returns:
            完整消息字节
        """
        len_data = sock.recv(4)
        msg_len = struct.unpack('>I', len_data)[0]
        msg = sock.recv(msg_len)
        return msg

    def parse_message(self, msg: bytes) -> ParsedMessage:
        """解析消息

        Args:
            msg: 原始消息字节

        Returns:
            解析后的消息 (类型, 参数字典)
        """
        if len(msg) < 4:
            raise ValueError(f'消息长度不足: {len(msg)}')

        cmd = msg[:4]

        if cmd == b'DMMV':
            return self._parse_dmmv(msg)
        elif cmd == b'DKDN':
            return self._parse_dkdn(msg)
        elif cmd == b'DKUP':
            return self._parse_dkup(msg)
        elif cmd == b'DMDN':
            return self._parse_dmdn(msg)
        elif cmd == b'DMUP':
            return self._parse_dmup(msg)
        else:
            raise ValueError(f'未知消息类型: {cmd}')

    def _parse_dmmv(self, msg: bytes) -> ParsedMessage:
        """解析鼠标移动消息

        DMMV: x, y 绝对坐标 (0-65535)

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 8:
            raise ValueError(f'DMMV 消息长度不足: {len(msg)}')
        x, y = struct.unpack('>HH', msg[4:8])
        return MessageType.DMMV, {'x': x, 'y': y}

    def _parse_dkdn(self, msg: bytes) -> ParsedMessage:
        """解析按键按下消息

        DKDN: key_code 按键代码

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 6:
            raise ValueError(f'DKDN 消息长度不足: {len(msg)}')
        key_code = struct.unpack('>H', msg[4:6])[0]
        return MessageType.DKDN, {'key_code': key_code}

    def _parse_dkup(self, msg: bytes) -> ParsedMessage:
        """解析按键释放消息

        DKUP: key_code 按键代码

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 6:
            raise ValueError(f'DKUP 消息长度不足: {len(msg)}')
        key_code = struct.unpack('>H', msg[4:6])[0]
        return MessageType.DKUP, {'key_code': key_code}

    def _parse_dmdn(self, msg: bytes) -> ParsedMessage:
        """解析鼠标按键按下消息

        DMDN: button 鼠标按钮代码 (假设与 Linux BTN_* 一致)

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 6:
            raise ValueError(f'DMDN 消息长度不足: {len(msg)}')
        button = struct.unpack('>H', msg[4:6])[0]
        return MessageType.DMDN, {'button': button}

    def _parse_dmup(self, msg: bytes) -> ParsedMessage:
        """解析鼠标按键释放消息

        DMUP: button 鼠标按钮代码

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 6:
            raise ValueError(f'DMUP 消息长度不足: {len(msg)}')
        button = struct.unpack('>H', msg[4:6])[0]
        return MessageType.DMUP, {'button': button}
