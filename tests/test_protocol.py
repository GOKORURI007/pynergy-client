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

    def test_build_hello(self):
        """测试 Hello 消息构建"""
        protocol = SynergyProtocol(major_version=1, minor_version=6)
        msg = protocol.build_hello()

        header = msg[:4]
        body = msg[4:]

        msg_len = struct.unpack('>I', header)[0]
        assert msg_len == len(body)

        assert body[:8] == b'Deskflow'
        major, minor = struct.unpack('>HH', body[8:])
        assert major == 1
        assert minor == 6

    def test_handshake_sends_data(self):
        """测试握手消息发送"""
        protocol = SynergyProtocol()
        mock_sock = MagicMock()

        protocol.handshake(mock_sock)

        mock_sock.send.assert_called_once()
        sent_data = mock_sock.send.call_args[0][0]
        assert sent_data.startswith(b'\x00\x00\x00\x0c')  # 长度头部 (12 bytes)
        assert b'Deskflow' in sent_data

    def test_parse_hello(self):
        """测试 Hello 消息解析"""
        protocol = SynergyProtocol()
        hello_msg = b'Deskflow' + struct.pack('>HH', 1, 6)

        major, minor = protocol.parse_hello(hello_msg)

        assert major == 1
        assert minor == 6

    def test_parse_hello_invalid_identifier(self):
        """测试 Hello 消息标识错误"""
        protocol = SynergyProtocol()
        wrong_msg = b'SynergyX' + struct.pack('>HH', 1, 6)

        with pytest.raises(ValueError, match='Hello 消息标识错误'):
            protocol.parse_hello(wrong_msg)

    def test_parse_hello_too_short(self):
        """测试 Hello 消息过短"""
        protocol = SynergyProtocol()
        short_msg = b'Desk'  # 只有 4 字节

        with pytest.raises(ValueError, match='Hello 消息长度不足'):
            protocol.parse_hello(short_msg)

    def test_build_hello_back(self):
        """测试 HelloBack 消息构建"""
        protocol = SynergyProtocol(major_version=1, minor_version=6)
        msg = protocol.build_hello_back(1, 6, 'Pynergy')

        header = msg[:4]
        body = msg[4:]

        msg_len = struct.unpack('>I', header)[0]
        assert msg_len == len(body)

        assert body[:8] == b'Deskflow'
        major, minor = struct.unpack('>HH', body[8:12])
        assert major == 1
        assert minor == 6
        assert b'Pynergy' in body[12:]
        assert body[-1] == 0  # null 结尾

    def test_parse_hello_back(self):
        """测试 HelloBack 消息解析"""
        protocol = SynergyProtocol()
        hello_back_msg = b'Deskflow' + struct.pack('>HH', 1, 6) + b'Pynergy\x00'

        major, minor, name = protocol.parse_hello_back(hello_back_msg)

        assert major == 1
        assert minor == 6
        assert name == 'Pynergy'


class TestDinf:
    """DINF 消息测试"""

    def test_build_dinf(self):
        """测试 DINF 消息构建"""
        protocol = SynergyProtocol()
        msg = protocol.build_dinf(1920, 1080, 0, 0)

        header = msg[:4]
        body = msg[4:]

        msg_len = struct.unpack('>I', header)[0]
        assert msg_len == len(body)

        assert body[:4] == b'DINF'
        width, height, x, y = struct.unpack('>HHHH', body[4:])
        assert width == 1920
        assert height == 1080
        assert x == 0
        assert y == 0

    def test_parse_dinf(self):
        """测试 DINF 消息解析"""
        protocol = SynergyProtocol()
        dinf_msg = b'DINF' + struct.pack('>HHHH', 1920, 1080, 0, 0)

        params = protocol.parse_dinf(dinf_msg)

        assert params['width'] == 1920
        assert params['height'] == 1080
        assert params['x'] == 0
        assert params['y'] == 0


class TestCinn:
    """CINN 消息测试"""

    def test_build_cinn(self):
        """测试 CINN 消息构建"""
        protocol = SynergyProtocol()
        msg = protocol.build_cinn(100, 200, 1, 0)

        header = msg[:4]
        body = msg[4:]

        msg_len = struct.unpack('>I', header)[0]
        assert msg_len == len(body)

        assert body[:4] == b'CINN'
        x, y, seq, modifiers = struct.unpack('>HHIH', body[4:])
        assert x == 100
        assert y == 200
        assert seq == 1
        assert modifiers == 0

    def test_parse_cinn(self):
        """测试 CINN 消息解析"""
        protocol = SynergyProtocol()
        cinn_msg = b'CINN' + struct.pack('>HHIH', 100, 200, 1, 0)

        params = protocol.parse_cinn(cinn_msg)

        assert params['x'] == 100
        assert params['y'] == 200
        assert params['sequence'] == 1
        assert params['modifiers'] == 0


class TestCalv:
    """CALV 消息测试"""

    def test_build_calv(self):
        """测试 CALV 消息构建"""
        protocol = SynergyProtocol()
        msg = protocol.build_calv()

        header = msg[:4]
        body = msg[4:]

        msg_len = struct.unpack('>I', header)[0]
        assert msg_len == len(body)

        assert body == b'CALV'

    def test_parse_calv(self):
        """测试 CALV 消息解析"""
        protocol = SynergyProtocol()
        calv_msg = b'CALV'

        params = protocol.parse_calv(calv_msg)

        assert params == {}


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

    def test_parse_dmrm(self):
        """测试相对鼠标移动消息解析"""
        protocol = SynergyProtocol()

        dx, dy = 10, -5
        msg = b'DMRM' + struct.pack('>hh', dx, dy)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DMRM
        assert params['dx'] == dx
        assert params['dy'] == dy

    def test_parse_dmwm(self):
        """测试鼠标滚轮消息解析"""
        protocol = SynergyProtocol()

        x, y = 0, 120
        msg = b'DMWM' + struct.pack('>hh', x, y)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DMWM
        assert params['x'] == x
        assert params['y'] == y

    def test_parse_dkrp(self):
        """测试按键重复消息解析"""
        protocol = SynergyProtocol()

        key_code, repeat, modifiers, button = 30, 2, 0, 0
        msg = b'DKRP' + struct.pack('>HHHH', key_code, repeat, modifiers, button)

        msg_type, params = protocol.parse_message(msg)

        assert msg_type == MessageType.DKRP
        assert params['key_code'] == key_code
        assert params['repeat'] == repeat
        assert params['modifiers'] == modifiers
        assert params['button'] == button

    def test_parse_hello_message(self):
        """测试 Hello 消息解析"""
        protocol = SynergyProtocol()

        hello_body = b'Deskflow' + struct.pack('>HH', 1, 6)
        hello_msg = struct.pack('>I', len(hello_body)) + hello_body

        msg_type, params = protocol.parse_message(hello_msg)

        assert msg_type == MessageType.Hello
        assert params['major'] == 1
        assert params['minor'] == 6

    def test_parse_cinn_message(self):
        """测试 CINN 消息解析"""
        protocol = SynergyProtocol()

        cinn_msg = b'CINN' + struct.pack('>HHIH', 100, 200, 1, 0)

        msg_type, params = protocol.parse_message(cinn_msg)

        assert msg_type == MessageType.CINN
        assert params['x'] == 100
        assert params['y'] == 200

    def test_parse_calv_message(self):
        """测试 CALV 消息解析"""
        protocol = SynergyProtocol()

        calv_msg = b'CALV'

        msg_type, params = protocol.parse_message(calv_msg)

        assert msg_type == MessageType.CALV
        assert params == {}

    def test_parse_qinf_message(self):
        """测试 QINF 消息解析"""
        protocol = SynergyProtocol()

        qinf_msg = b'QINF'

        msg_type, params = protocol.parse_message(qinf_msg)

        assert msg_type == MessageType.QINF
        assert params == {}

    def test_parse_cbye_message(self):
        """测试 CBYE 消息解析"""
        protocol = SynergyProtocol()

        cbye_msg = b'CBYE'

        msg_type, params = protocol.parse_message(cbye_msg)

        assert msg_type == MessageType.CBYE
        assert params == {}

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
