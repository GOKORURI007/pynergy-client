import pytest
from pynergy_client.pynergy_protocol import HelloBackMsg, HelloMsg


class TestHelloMsg:
    @pytest.mark.parametrize(
        'msg_raw, expected_protocol, expected_major, expected_minor',
        [
            (b'Barrier\x00\x01\x00\x08', 'Barrier', 1, 8),
            (b'Synergy\x00\x01\x00\x03', 'Synergy', 1, 3),
            (b'Pynergy\x00\x01\x00\x00', 'Pynergy', 1, 0),
        ],
    )
    def test_pack_success(self, msg_raw, expected_protocol, expected_major, expected_minor):
        """测试正常打包的情况"""
        msg = HelloMsg(expected_protocol, expected_major, expected_minor)
        assert msg.pack() == msg_raw

    @pytest.mark.parametrize(
        'msg_raw, expected_protocol, expected_major, expected_minor',
        [
            (b'Barrier\x00\x01\x00\x08', 'Barrier', 1, 8),
            (b'Synergy\x00\x01\x00\x03', 'Synergy', 1, 3),
            (b'Pynergy\x00\x01\x00\x00', 'Pynergy', 1, 0),
        ],
    )
    def test_unpack_success(self, msg_raw, expected_protocol, expected_major, expected_minor):
        """测试正常解包的情况"""
        msg = HelloMsg.unpack(msg_raw)
        assert msg.protocol_name == expected_protocol
        assert msg.major == expected_major
        assert msg.minor == expected_minor

    @pytest.mark.parametrize(
        'msg_raw, expected_protocol, expected_major, expected_minor, trailing_num',
        [
            (b'Barrier\x00\x01\x00\x07\x09\xff\x00', 'Barrier', 1, 7, 3),
            (b'Barrier\x00\x01\x00\x07\x09\xff', 'Barrier', 1, 7, 2),
            (b'Barrier\x00\x01\x00\x07\x09', 'Barrier', 1, 7, 1),
        ],
    )
    def test_unpack_with_trailing_data(
        self,
        msg_raw,
        expected_protocol,
        expected_major,
        expected_minor,
        trailing_num,
        propagate_logs,
    ):
        propagate_logs.set_level('WARNING')
        msg = HelloMsg.unpack(msg_raw)

        assert msg.protocol_name == expected_protocol
        assert msg.major == expected_major
        assert msg.minor == expected_minor

        assert f'解包后剩余 {trailing_num} 字节未处理的数据' in propagate_logs.text

    @pytest.mark.parametrize(
        'msg_raw, expected_exception, match_text',
        [
            (b'', ValueError, '数据不足'),
            (b'   ', ValueError, '结构体解包失败'),
            (b'\n', ValueError, '结构体解包失败'),
            (None, TypeError, 'NoneType'),
            (b'False\x00\x01\x00\x08', ValueError, '数据不足'),
        ],
    )
    def test_unpack_error(self, msg_raw, expected_exception, match_text):
        """测试应该触发 raise 的情况"""
        with pytest.raises(expected_exception, match=match_text):
            HelloMsg.unpack(msg_raw)


class TestHelloBackMsg:
    @pytest.mark.parametrize(
        'msg_raw, expected_protocol, expected_major, expected_minor, expected_name',
        [
            (b'Barrier\x00\x01\x00\x08\x00\x00\x00\x07abcdefg', 'Barrier', 1, 8, 'abcdefg'),
            (b'Synergy\x00\x01\x00\x03\x00\x00\x00\x05c__fg', 'Synergy', 1, 3, 'c__fg'),
            (b'Pynergy\x00\x01\x00\x00\x00\x00\x00\x03abc', 'Pynergy', 1, 0, 'abc'),
        ],
    )
    def test_pack_success(
        self, msg_raw, expected_protocol, expected_major, expected_minor, expected_name
    ):
        """测试正常打包的情况"""
        msg = HelloBackMsg(expected_protocol, expected_major, expected_minor, expected_name)
        assert msg.pack() == msg_raw

    @pytest.mark.parametrize(
        'msg_raw, expected_protocol, expected_major, expected_minor, expected_name',
        [
            (b'Barrier\x00\x01\x00\x08\x00\x00\x00\x07abcdefg', 'Barrier', 1, 8, 'abcdefg'),
            (b'Synergy\x00\x01\x00\x03\x00\x00\x00\x05c__fg', 'Synergy', 1, 3, 'c__fg'),
            (b'Pynergy\x00\x01\x00\x00\x00\x00\x00\x03abc', 'Pynergy', 1, 0, 'abc'),
        ],
    )
    def test_unpack_success(
        self, msg_raw, expected_protocol, expected_major, expected_minor, expected_name
    ):
        """测试正常解包的情况"""
        msg = HelloBackMsg.unpack(msg_raw)
        assert msg.protocol_name == expected_protocol
        assert msg.major == expected_major
        assert msg.minor == expected_minor
        assert msg.name == expected_name

    @pytest.mark.parametrize(
        'msg_raw, expected_protocol, expected_major, expected_minor, expected_name, trailing_num',
        [
            (b'Barrier\x00\x01\x00\x08\x00\x00\x00\x04abcd\x00', 'Barrier', 1, 8, 'abcd', 1),
            (b'Synergy\x00\x01\x00\x03\x00\x00\x00\x05c__fg__', 'Synergy', 1, 3, 'c__fg', 2),
            (b'Pynergy\x00\x01\x00\x00\x00\x00\x00\x03abc\x0488', 'Pynergy', 1, 0, 'abc', 3),
        ],
    )
    def test_unpack_with_trailing_data(
        self,
        msg_raw,
        expected_protocol,
        expected_major,
        expected_minor,
        expected_name,
        trailing_num,
        propagate_logs,
    ):
        propagate_logs.set_level('WARNING')
        msg = HelloBackMsg.unpack(msg_raw)

        assert msg.protocol_name == expected_protocol
        assert msg.major == expected_major
        assert msg.minor == expected_minor
        assert msg.name == expected_name

        assert f'解包后剩余 {trailing_num} 字节未处理的数据' in propagate_logs.text

    @pytest.mark.parametrize(
        'msg_raw, expected_exception, match_text',
        [
            (b'', ValueError, '数据不足'),
            (b'   ', ValueError, '结构体解包失败'),
            (b'\n', ValueError, '结构体解包失败'),
            (None, TypeError, 'NoneType'),
            (b'False\x00\x01\x00\x08', ValueError, '数据不足'),
        ],
    )
    def test_unpack_error(self, msg_raw, expected_exception, match_text):
        """测试应该触发 raise 的情况"""
        with pytest.raises(expected_exception, match=match_text):
            HelloBackMsg.unpack(msg_raw)
