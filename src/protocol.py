"""
Deskflow 协议解析模块

实现 Deskflow/Synergy 协议消息的接收、解析和封装。
"""

import socket
import struct

from src.protocol_types import MessageType, ParsedMessage


class SynergyProtocol:
    """Deskflow 协议解析类

    负责协议消息的收发和解析。
    """

    def __init__(self, major_version: int = 1, minor_version: int = 6):
        """初始化协议

        Args:
            major_version: 主版本号
            minor_version: 次版本号
        """
        self._major_version = major_version
        self._minor_version = minor_version

    def build_hello(self) -> bytes:
        """构建 Hello 消息（服务器发送给客户端）

        Returns:
            Hello 消息字节
        """
        msg = b'Deskflow' + struct.pack('>HH', self._major_version, self._minor_version)
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_hello(self, msg: bytes) -> tuple[int, int]:
        """解析 Hello 消息

        Hello: "Deskflow" + major(2) + minor(2)

        Args:
            msg: 原始消息字节

        Returns:
            (major, version) 版本号元组
        """
        if len(msg) < 11:
            raise ValueError(f'Hello 消息长度不足: {len(msg)}')
        if msg[:8] != b'Deskflow':
            raise ValueError(f'Hello 消息标识错误: {msg[:8]}')
        major, minor = struct.unpack('>HH', msg[8:12])
        return major, minor

    def build_hello_back(self, major: int, minor: int, name: str) -> bytes:
        """构建 HelloBack 消息（客户端发送给服务器）

        HelloBack: "Deskflow" + major(2) + minor(2) + name(UTF-8字符串, null结尾)

        Args:
            major: 主版本号
            minor: 次版本号
            name: 客户端名称

        Returns:
            HelloBack 消息字节
        """
        name_bytes = name.encode('utf-8') + b'\x00'
        msg = b'Deskflow' + struct.pack('>HH', major, minor) + name_bytes
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_hello_back(self, msg: bytes) -> tuple[int, int, str]:
        """解析 HelloBack 消息

        Args:
            msg: 原始消息字节

        Returns:
            (major, minor, name) 版本号和名称
        """
        if len(msg) < 12:
            raise ValueError(f'HelloBack 消息长度不足: {len(msg)}')
        if msg[:8] != b'Deskflow':
            raise ValueError(f'HelloBack 消息标识错误: {msg[:8]}')
        major, minor = struct.unpack('>HH', msg[8:12])
        name_end = msg.find(b'\x00', 12)
        if name_end == -1:
            raise ValueError('HelloBack 消息缺少 null 结尾')
        name = msg[12:name_end].decode('utf-8')
        return major, minor, name

    def build_dinf(self, width: int, height: int, x: int = 0, y: int = 0) -> bytes:
        """构建屏幕信息消息

        DINF: w(2) + h(2) + x(2) + y(2)

        Args:
            width: 屏幕宽度
            height: 屏幕高度
            x: X 偏移
            y: Y 偏移

        Returns:
            DINF 消息字节
        """
        msg = b'DINF' + struct.pack('>HHHH', width, height, x, y)
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_dinf(self, msg: bytes) -> dict:
        """解析屏幕信息消息

        Args:
            msg: 原始消息字节

        Returns:
            {'width': w, 'height': h, 'x': x, 'y': y}
        """
        if len(msg) < 12:
            raise ValueError(f'DINF 消息长度不足: {len(msg)}')
        width, height, x, y = struct.unpack('>HHHH', msg[4:12])
        return {'width': width, 'height': height, 'x': x, 'y': y}

    def build_cinn(self, x: int, y: int, sequence: int = 0, modifiers: int = 0) -> bytes:
        """构建进入屏幕消息

        CINN: x(2) + y(2) + seq(4) + modifiers(2)

        Args:
            x: X 坐标
            y: Y 坐标
            sequence: 序列号
            modifiers: 修饰键状态

        Returns:
            CINN 消息字节
        """
        msg = b'CINN' + struct.pack('>HHIH', x, y, sequence, modifiers)
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_cinn(self, msg: bytes) -> dict:
        """解析进入屏幕消息

        Args:
            msg: 原始消息字节

        Returns:
            {'x': x, 'y': y, 'sequence': seq, 'modifiers': modifiers}
        """
        if len(msg) < 14:
            raise ValueError(f'CINN 消息长度不足: {len(msg)}')
        x, y, sequence, modifiers = struct.unpack('>HHIH', msg[4:14])
        return {'x': x, 'y': y, 'sequence': sequence, 'modifiers': modifiers}

    def build_cout(self, sequence: int = 0) -> bytes:
        """构建离开屏幕消息

        COUT: seq(4)

        Args:
            sequence: 序列号

        Returns:
            COUT 消息字节
        """
        msg = b'COUT' + struct.pack('>I', sequence)
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_cout(self, msg: bytes) -> dict:
        """解析离开屏幕消息

        Args:
            msg: 原始消息字节

        Returns:
            {'sequence': seq}
        """
        if len(msg) < 8:
            raise ValueError(f'COUT 消息长度不足: {len(msg)}')
        sequence = struct.unpack('>I', msg[4:8])[0]
        return {'sequence': sequence}

    def build_calv(self) -> bytes:
        """构建心跳消息

        Returns:
            CALV 消息字节
        """
        msg = b'CALV'
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_calv(self, msg: bytes) -> dict:
        """解析心跳消息

        Args:
            msg: 原始消息字节

        Returns:
            空字典
        """
        if len(msg) < 4:
            raise ValueError(f'CALV 消息长度不足: {len(msg)}')
        return {}

    def build_cbye(self) -> bytes:
        """构建关闭连接消息

        Returns:
            CBYE 消息字节
        """
        msg = b'CBYE'
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_cbye(self, msg: bytes) -> dict:
        """解析关闭连接消息

        Args:
            msg: 原始消息字节

        Returns:
            空字典
        """
        if len(msg) < 4:
            raise ValueError(f'CBYE 消息长度不足: {len(msg)}')
        return {}

    def build_qinf(self) -> bytes:
        """构建查询屏幕信息消息

        Returns:
            QINF 消息字节
        """
        msg = b'QINF'
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_qinf(self, msg: bytes) -> dict:
        """解析查询屏幕信息消息

        Args:
            msg: 原始消息字节

        Returns:
            空字典
        """
        if len(msg) < 4:
            raise ValueError(f'QINF 消息长度不足: {len(msg)}')
        return {}

    def build_ciak(self) -> bytes:
        """构建信息确认消息

        Returns:
            CIAK 消息字节
        """
        msg = b'CIAK'
        header = struct.pack('>I', len(msg))
        return header + msg

    def parse_ciak(self, msg: bytes) -> dict:
        """解析信息确认消息

        Args:
            msg: 原始消息字节

        Returns:
            空字典
        """
        if len(msg) < 4:
            raise ValueError(f'CIAK 消息长度不足: {len(msg)}')
        return {}

    def parse_eicv(self, msg: bytes) -> dict:
        """解析版本不兼容错误消息

        Args:
            msg: 原始消息字节

        Returns:
            {'reason': reason}
        """
        if len(msg) < 8:
            raise ValueError(f'EICV 消息长度不足: {len(msg)}')
        reason = struct.unpack('>I', msg[4:8])[0]
        return {'reason': reason}

    def parse_ebsy(self, msg: bytes) -> dict:
        """解析服务器忙错误消息

        Args:
            msg: 原始消息字节

        Returns:
            空字典
        """
        if len(msg) < 4:
            raise ValueError(f'EBSY 消息长度不足: {len(msg)}')
        return {}

    def handshake(self, sock: socket.socket) -> None:
        """发送握手协议（保留兼容接口）

        Args:
            sock: TCP 套接字
        """
        msg = self.build_hello()
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
        elif cmd == b'DMRM':
            return self._parse_dmrm(msg)
        elif cmd == b'DMWM':
            return self._parse_dmwm(msg)
        elif cmd == b'DKRP':
            return self._parse_dkrp(msg)
        elif cmd == b'Hello':
            return self._parse_hello_msg(msg)
        elif cmd == b'CINN':
            return self._parse_cinn_msg(msg)
        elif cmd == b'COUT':
            return self._parse_cout_msg(msg)
        elif cmd == b'CALV':
            return self._parse_calv_msg(msg)
        elif cmd == b'QINF':
            return self._parse_qinf_msg(msg)
        elif cmd == b'CBYE':
            return self._parse_cbye_msg(msg)
        elif cmd == b'EICV':
            return self._parse_eicv_msg(msg)
        elif cmd == b'EBSY':
            return self._parse_ebsy_msg(msg)
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

        DMDN: button 鼠标按钮代码

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

    def _parse_dmrm(self, msg: bytes) -> ParsedMessage:
        """解析相对鼠标移动消息

        DMRM: dx, dy 相对位移

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 8:
            raise ValueError(f'DMRM 消息长度不足: {len(msg)}')
        dx, dy = struct.unpack('>hh', msg[4:8])
        return MessageType.DMRM, {'dx': dx, 'dy': dy}

    def _parse_dmwm(self, msg: bytes) -> ParsedMessage:
        """解析鼠标滚轮消息

        DMWM: x(2) + y(2)

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 8:
            raise ValueError(f'DMWM 消息长度不足: {len(msg)}')
        x, y = struct.unpack('>hh', msg[4:8])
        return MessageType.DMWM, {'x': x, 'y': y}

    def _parse_dkrp(self, msg: bytes) -> ParsedMessage:
        """解析按键重复消息

        DKRP: key_code(2) + repeat(2) + modifiers(2) + button(2)

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        if len(msg) < 12:
            raise ValueError(f'DKRP 消息长度不足: {len(msg)}')
        key_code, repeat, modifiers, button = struct.unpack('>HHHH', msg[4:12])
        return MessageType.DKRP, {
            'key_code': key_code,
            'repeat': repeat,
            'modifiers': modifiers,
            'button': button,
        }

    def _parse_hello_msg(self, msg: bytes) -> ParsedMessage:
        """解析 Hello 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        major, minor = self.parse_hello(msg)
        return MessageType.Hello, {'major': major, 'minor': minor}

    def _parse_cinn_msg(self, msg: bytes) -> ParsedMessage:
        """解析 CINN 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_cinn(msg)
        return MessageType.CINN, params

    def _parse_cout_msg(self, msg: bytes) -> ParsedMessage:
        """解析 COUT 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_cout(msg)
        return MessageType.COUT, params

    def _parse_calv_msg(self, msg: bytes) -> ParsedMessage:
        """解析 CALV 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_calv(msg)
        return MessageType.CALV, params

    def _parse_qinf_msg(self, msg: bytes) -> ParsedMessage:
        """解析 QINF 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_qinf(msg)
        return MessageType.QINF, params

    def _parse_cbye_msg(self, msg: bytes) -> ParsedMessage:
        """解析 CBYE 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_cbye(msg)
        return MessageType.CBYE, params

    def _parse_eicv_msg(self, msg: bytes) -> ParsedMessage:
        """解析 EICV 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_eicv(msg)
        return MessageType.EICV, params

    def _parse_ebsy_msg(self, msg: bytes) -> ParsedMessage:
        """解析 EBSY 消息

        Args:
            msg: 原始消息

        Returns:
            解析结果
        """
        params = self.parse_ebsy(msg)
        return MessageType.EBSY, params
