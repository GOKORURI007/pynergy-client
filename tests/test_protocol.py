"""
协议模块测试

测试 SynergyProtocol 类的功能。
"""

import struct
from unittest.mock import MagicMock

import pytest

from src.protocol import SynergyProtocol
from src.protocol_types import MessageType


class TestHandshake:
    """握手测试"""

    def test_build_handshake(self):
        """测试握手消息构建"""
        protocol = SynergyProtocol(protocol_version=1, major_version=6)
        msg = protocol.build_handshake()

        header = msg[:4]
        body = msg[4:]

        msg_len = struct.unpack('>I', header)[0]
        assert msg_len == len(body)

        assert body[:7] == b'Synergy'
        version, major = struct.unpack('>HH', body[7:])
        assert version == 1
        assert major == 6

    def test_handshake_sends_data(self):
        """测试握手消息发送"""
        protocol = SynergyProtocol()
        mock_sock = MagicMock()

        protocol.handshake(mock_sock)

        mock_sock.send.assert_called_once()
        sent_data = mock_sock.send.call_args[0][0]
        assert sent_data.startswith(b'\x00\x00\x00\x0b')  # 长度头部 (11 bytes)
        assert b'Synergy' in sent_data


class TestParseMessage:
    """消息解析测试"""

    def test_parse_dmmv(self):
        """测试鼠标移动消息解析"""
        protocol = SynergyProtocol()

        x, y = 32768, 16384
        msg = b'DMMV' + struct.pack('>HH', x, y)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DMMV
        assert params['x'] == x
        assert params['y'] == y

    def test_parse_dkdn(self):
        """测试按键按下消息解析"""
        protocol = SynergyProtocol()

        key_code = 30  # KEY_A
        msg = b'DKDN' + struct.pack('>H', key_code)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DKDN
        assert params['key_code'] == key_code

    def test_parse_dkup(self):
        """测试按键释放消息解析"""
        protocol = SynergyProtocol()

        key_code = 30  # KEY_A
        msg = b'DKUP' + struct.pack('>H', key_code)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DKUP
        assert params['key_code'] == key_code

    def test_parse_dmdn(self):
        """测试鼠标按下消息解析"""
        protocol = SynergyProtocol()

        button = 272  # BTN_LEFT
        msg = b'DMDN' + struct.pack('>H', button)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DMDN
        assert params['button'] == button

    def test_parse_dmup(self):
        """测试鼠标释放消息解析"""
        protocol = SynergyProtocol()

        button = 272  # BTN_LEFT
        msg = b'DMUP' + struct.pack('>H', button)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DMUP
        assert params['button'] == button

    def test_parse_unknown_message(self):
        """测试未知消息类型解析"""
        protocol = SynergyProtocol()

        msg = b'UNKNOWN' + b'\x00\x00\x00\x00'

        with pytest.raises(ValueError, match='未知消息类型'):
            protocol.parse_message(msg)

    def test_parse_message_too_short(self):
        """测试消息过短解析"""
        protocol = SynergyProtocol()

        msg = b'DMMV'  # 只有4字节，不足8字节

        with pytest.raises(ValueError, match='消息长度不足'):
            protocol.parse_message(msg)


class TestRecvMessage:
    """消息接收测试"""

    def test_recv_message(self):
        """测试消息接收"""
        protocol = SynergyProtocol()
        mock_sock = MagicMock()

        expected_msg = b'DMMV' + struct.pack('>HH', 100, 200)
        mock_sock.recv.side_effect = [
            struct.pack('>I', len(expected_msg)),  # 长度头部
            expected_msg,  # 消息体
        ]

        msg = protocol.recv_message(mock_sock)

        assert msg == expected_msg
        assert mock_sock.recv.call_count == 2
