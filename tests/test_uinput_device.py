"""
虚拟设备模块测试

测试 VirtualDevice 类的功能。
"""

from unittest.mock import MagicMock, patch

from evdev import ecodes

from src.pynergy_client.device.vdev_uinput import UInputKeyboardDevice, UInputMouseDevice


class TestUIputDeviceCreation:
    """设备创建测试"""

    def test_default_initialization(self):
        """测试默认参数初始化"""
        with patch('evdev.UInput') as mock_ui:
            mouse = UInputMouseDevice()
            mock_ui.assert_called_once()
            call_kwargs = mock_ui.call_args[1]
            assert call_kwargs['name'] == 'Pynergy UInput vMouse'
            assert call_kwargs['vendor'] == 0x1234
            assert call_kwargs['product'] == 0x5678
            assert call_kwargs['version'] == 1

        with patch('evdev.UInput') as mock_ui:
            keyboard = UInputKeyboardDevice()
            mock_ui.assert_called_once()
            call_kwargs = mock_ui.call_args[1]
            assert call_kwargs['name'] == 'Pynergy UInput vKeyboard'
            assert call_kwargs['vendor'] == 0x1234
            assert call_kwargs['product'] == 0x5678
            assert call_kwargs['version'] == 1

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        with patch('evdev.UInput') as mock_ui:
            device = UInputMouseDevice(
                name='Test Device',
                vendor=0x9999,
                product=0x8888,
                version=2,
            )
            mock_ui.assert_called_once()
            call_kwargs = mock_ui.call_args[1]
            assert call_kwargs['name'] == 'Test Device'
            assert call_kwargs['vendor'] == 0x9999
            assert call_kwargs['product'] == 0x8888
            assert call_kwargs['version'] == 2

        with patch('evdev.UInput') as mock_ui:
            device = UInputKeyboardDevice(
                name='Test Device',
                vendor=0x9999,
                product=0x8888,
                version=2,
            )
            mock_ui.assert_called_once()
            call_kwargs = mock_ui.call_args[1]
            assert call_kwargs['name'] == 'Test Device'
            assert call_kwargs['vendor'] == 0x9999
            assert call_kwargs['product'] == 0x8888
            assert call_kwargs['version'] == 2

    def test_capabilities_contains_rel_events(self):
        """测试事件能力包含相对位移事件"""
        with patch('evdev.UInput') as mock_ui:
            device = UInputMouseDevice()
            call_kwargs = mock_ui.call_args[1]
            capabilities = call_kwargs['events']
            assert ecodes.EV_REL in capabilities
            rel_events = capabilities[ecodes.EV_REL]
            assert ecodes.REL_X in rel_events
            assert ecodes.REL_Y in rel_events
            assert ecodes.REL_WHEEL in rel_events
            assert ecodes.REL_HWHEEL in rel_events

    def test_capabilities_contains_key_events(self):
        """测试事件能力包含按键事件"""
        with patch('evdev.UInput') as mock_ui:
            device = UInputMouseDevice()
            call_kwargs = mock_ui.call_args[1]
            capabilities = call_kwargs['events']
            assert ecodes.EV_KEY in capabilities
            key_events = capabilities[ecodes.EV_KEY]
            assert ecodes.BTN_LEFT in key_events
            assert ecodes.BTN_RIGHT in key_events
            assert ecodes.BTN_MIDDLE in key_events
            assert ecodes.BTN_SIDE in key_events
            assert ecodes.BTN_EXTRA in key_events
            assert ecodes.BTN_FORWARD in key_events
            assert ecodes.BTN_BACK in key_events

        with patch('evdev.UInput') as mock_ui:
            device = UInputKeyboardDevice()
            call_kwargs = mock_ui.call_args[1]
            capabilities = call_kwargs['events']
            assert ecodes.EV_KEY in capabilities
            key_events = capabilities[ecodes.EV_KEY]
            for code in range(1, 256):
                assert code in key_events


class TestMouseEvents:
    """鼠标事件测试"""

    def test_write_mouse_move(self):
        """测试鼠标移动事件写入"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputMouseDevice()
            device.move_relative(10, 20)
            mock_instance.write.assert_any_call(ecodes.EV_REL, ecodes.REL_X, 10)
            mock_instance.write.assert_any_call(ecodes.EV_REL, ecodes.REL_Y, 20)

    def test_write_wheel_vertical(self):
        """测试垂直滚轮事件写入"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputMouseDevice()
            device.wheel_relative(dy=1)
            mock_instance.write.assert_called_with(ecodes.EV_REL, ecodes.REL_WHEEL, 1)

    def test_write_wheel_horizontal(self):
        """测试水平滚轮事件写入"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputMouseDevice()
            device.wheel_relative(dx=-1)
            mock_instance.write.assert_called_with(ecodes.EV_REL, ecodes.REL_HWHEEL, -1)

    def test_write_wheel_both(self):
        """测试双向滚轮事件写入"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputMouseDevice()
            device.wheel_relative(dx=1, dy=-1)
            assert mock_instance.write.call_count == 2


class TestKeyEvents:
    """键盘事件测试"""

    def test_key_press(self):
        """测试按键按下事件"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputKeyboardDevice()
            device.send_key(30, down=True)  # KEY_A = 30
            mock_instance.write.assert_called_with(ecodes.EV_KEY, 30, 1)

    def test_key_release(self):
        """测试按键释放事件"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputKeyboardDevice()
            device.pressed_keys.add(30)
            device.send_key(30, down=False)  # KEY_A = 30
            mock_instance.write.assert_called_with(ecodes.EV_KEY, 30, 0)


class TestSync:
    """同步测试"""

    def test_syn_calls_syn(self):
        """测试同步方法调用"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputMouseDevice()
            device.syn()
            mock_instance.syn.assert_called_once()

        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputKeyboardDevice()
            device.syn()
            mock_instance.syn.assert_called_once()


class TestClose:
    """关闭测试"""

    def test_close_calls_close(self):
        """测试关闭方法调用"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputMouseDevice()
            device.close()
            mock_instance.close.assert_called_once()

        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            device = UInputKeyboardDevice()
            device.close()
            mock_instance.close.assert_called_once()


class TestContextManager:
    """上下文管理器测试"""

    def test_context_manager(self):
        """测试 with 语句管理设备生命周期"""
        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            with UInputMouseDevice() as device:
                assert device is not None
            mock_instance.close.assert_called_once()

        with patch('evdev.UInput') as mock_ui:
            mock_instance = MagicMock()
            mock_ui.return_value = mock_instance
            with UInputKeyboardDevice() as device:
                assert device is not None
            mock_instance.close.assert_called_once()
