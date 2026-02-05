"""
客户端模块测试

测试 SynergyClient 类的功能。
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.client import main, SynergyClient
from src.device import VirtualDevice
from src.protocol_types import MessageType


class TestSynergyClientInit:
    """客户端初始化测试"""

    def test_default_initialization(self):
        """测试默认参数初始化"""
        client = SynergyClient('192.168.1.100')
        assert client._server == '192.168.1.100'
        assert client._port == 24800
        assert client._coords_mode == 'relative'
        assert client._screen_width == 1920
        assert client._screen_height == 1080

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        device = MagicMock(spec=VirtualDevice)
        client = SynergyClient(
            server='10.0.0.1',
            port=9999,
            coords_mode='absolute',
            screen_width=2560,
            screen_height=1440,
            device=device,
        )
        assert client._server == '10.0.0.1'
        assert client._port == 9999
        assert client._coords_mode == 'absolute'
        assert client._screen_width == 2560
        assert client._screen_height == 1440
        assert client._device is device

    def test_device_property(self):
        """测试设备属性"""
        with patch('src.client.VirtualDevice') as mock_device_class:
            mock_device = MagicMock()
            mock_device_class.return_value = mock_device
            client = SynergyClient('192.168.1.100')
            device = client.device
            assert device is mock_device
            mock_device_class.assert_called_once()

    def test_device_property_returns_same_instance(self):
        """测试设备属性返回同一实例"""
        with patch('src.client.VirtualDevice') as mock_device_class:
            mock_device = MagicMock()
            mock_device_class.return_value = mock_device
            client = SynergyClient('192.168.1.100')
            device1 = client.device
            device2 = client.device
            assert device1 is device2
            assert mock_device_class.call_count == 1


class TestConnect:
    """连接测试"""

    def test_connect(self):
        """测试 TCP 连接"""
        with patch('socket.socket') as mock_socket_class:
            mock_sock = MagicMock()
            mock_socket_class.return_value = mock_sock
            mock_protocol = MagicMock()
            client = SynergyClient('192.168.1.100')
            client._protocol = mock_protocol
            client.connect()
            mock_socket_class.assert_called_once()
            mock_sock.connect.assert_called_once_with(('192.168.1.100', 24800))
            mock_protocol.handshake.assert_called_once_with(mock_sock)


class TestAbsToRel:
    """坐标转换测试"""

    def test_first_position_returns_zero(self):
        """测试首次位置返回零位移"""
        client = SynergyClient('192.168.1.100')
        dx, dy = client._abs_to_rel(32768, 32768)
        assert dx == 0
        assert dy == 0

    def test_relative_move_calculation(self):
        """测试相对位移计算"""
        client = SynergyClient('192.168.1.100')
        client._abs_to_rel(0, 0)
        dx, dy = client._abs_to_rel(32768, 32768)
        assert dx == 960
        assert dy == 540

    def test_update_last_position(self):
        """测试更新最后位置"""
        client = SynergyClient('192.168.1.100')
        client._abs_to_rel(0, 0)
        client._abs_to_rel(32768, 32768)
        assert client._last_x == 32768
        assert client._last_y == 32768

    def test_custom_screen_size(self):
        """测试自定义屏幕尺寸"""
        client = SynergyClient('192.168.1.100', screen_width=1920, screen_height=1080)
        client._abs_to_rel(0, 0)
        dx, dy = client._abs_to_rel(32768, 32768)
        assert dx == 960
        assert dy == 540

    def test_negative_movement(self):
        """测试负向移动"""
        client = SynergyClient('192.168.1.100')
        client._abs_to_rel(32768, 32768)
        dx, dy = client._abs_to_rel(0, 0)
        assert dx == -960
        assert dy == -540


class TestHandleMessage:
    """消息处理测试"""

    def test_handle_dmmv_relative(self):
        """测试相对坐标模式处理鼠标移动"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', coords_mode='relative', device=device)
        client._abs_to_rel(0, 0)

        client._handle_message(MessageType.DMMV, {'x': 32768, 'y': 32768})

        device.write_mouse_move.assert_called_once()
        device.syn.assert_called_once()

    def test_handle_dmmv_absolute(self):
        """测试绝对坐标模式处理鼠标移动"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', coords_mode='absolute', device=device)

        client._handle_message(MessageType.DMMV, {'x': 32768, 'y': 32768})

        device.write.assert_called()
        device.syn.assert_called_once()

    def test_handle_dkdn(self):
        """测试按键按下处理"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', device=device)

        client._handle_message(MessageType.DKDN, {'key_code': 30})

        device.write_key.assert_called_once_with(30, True)
        device.syn.assert_called_once()

    def test_handle_dkup(self):
        """测试按键释放处理"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', device=device)

        client._handle_message(MessageType.DKUP, {'key_code': 30})

        device.write_key.assert_called_once_with(30, False)
        device.syn.assert_called_once()

    def test_handle_dmdn(self):
        """测试鼠标按下处理"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', device=device)

        client._handle_message(MessageType.DMDN, {'button': 272})

        device.write_key.assert_called_once_with(272, True)
        device.syn.assert_called_once()

    def test_handle_dmup(self):
        """测试鼠标释放处理"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', device=device)

        client._handle_message(MessageType.DMUP, {'button': 272})

        device.write_key.assert_called_once_with(272, False)
        device.syn.assert_called_once()


class TestClose:
    """关闭测试"""

    def test_close(self):
        """测试关闭连接和设备"""
        device = MagicMock()
        client = SynergyClient('192.168.1.100', device=device)
        client._sock = MagicMock()

        client.close()

        assert client._running is False
        assert client._sock is None
        assert client._device is None
        device.close.assert_called_once()

    def test_stop(self):
        """测试停止客户端"""
        client = SynergyClient('192.168.1.100')
        client.stop()
        assert client._running is False


class TestMain:
    """主函数测试"""

    def test_cli_help(self):
        """测试 CLI 帮助信息"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'Synergy 服务器 IP 地址' in result.output
        assert '--coords-mode' in result.output

    def test_cli_with_server(self):
        """测试 CLI 传递服务器参数"""
        with patch.object(SynergyClient, 'run') as mock_run:
            runner = CliRunner()
            result = runner.invoke(main, ['--server', '192.168.1.100', '-v'])
            mock_run.assert_called_once()

    def test_cli_with_all_options(self):
        """测试 CLI 传递所有参数"""
        with patch.object(SynergyClient, 'run') as mock_run:
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    '--server',
                    '10.0.0.1',
                    '--port',
                    '9999',
                    '--coords-mode',
                    'absolute',
                    '--screen-width',
                    '2560',
                    '--screen-height',
                    '1440',
                ],
            )
            mock_run.assert_called_once()
