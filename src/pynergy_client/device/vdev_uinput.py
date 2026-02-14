from typing import Tuple

import evdev
from evdev import AbsInfo
from evdev import ecodes as e
from loguru import logger

from ..pynergy_protocol import ModifierKeyMask
from .base import BaseKeyboardVirtualDevice, BaseMouseVirtualDevice


class UInputMouseDevice(BaseMouseVirtualDevice):
    def __init__(
        self,
        name: str = 'Pynergy UInput vMouse',
        vendor: int = 0x1234,
        product: int = 0x5678,
        version: int = 1,
        screen_size: Tuple[int, int] = (1920, 1080),
    ):
        """初始化虚拟设备

        Args:
            name: 设备名称
            vendor: 厂商 ID
            product: 产品 ID
            version: 版本号
        """
        super().__init__()
        capabilities = {
            e.EV_KEY: [
                e.BTN_LEFT,
                e.BTN_RIGHT,
                e.BTN_MIDDLE,
                e.BTN_SIDE,
                e.BTN_EXTRA,
                e.BTN_FORWARD,
                e.BTN_BACK,
                e.BTN_TASK,
            ],
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            e.EV_ABS: [
                (
                    e.ABS_X,
                    AbsInfo(value=0, min=0, max=screen_size[0], fuzz=0, flat=0, resolution=0),
                ),
                (
                    e.ABS_Y,
                    AbsInfo(value=0, min=0, max=screen_size[1], fuzz=0, flat=0, resolution=0),
                ),
            ],
        }

        self._ui = evdev.UInput(
            events=capabilities,
            name=name,
            vendor=vendor,
            product=product,
            version=version,
        )

    def move_absolute(self, x: int, y: int) -> None:
        self._ui.write(e.EV_ABS, e.ABS_X, x)
        self._ui.write(e.EV_ABS, e.ABS_Y, y)

    def move_relative(self, dx: int, dy: int) -> None:
        self._ui.write(e.EV_REL, e.REL_X, dx)
        self._ui.write(e.EV_REL, e.REL_Y, dy)

    def wheel_relative(self, dy: int = 0, dx: int = 0) -> None:
        if dy != 0:
            self._ui.write(e.EV_REL, e.REL_WHEEL, dy)
        if dx != 0:
            self._ui.write(e.EV_REL, e.REL_HWHEEL, dx)

    def wheel_absolute(self, degree: int = 0) -> None:
        self._ui.write(e.EV_ABS, e.ABS_WHEEL, degree)

    def send_button(self, button_id: int, down: bool) -> None:
        if down:
            self.pressed_btns.add(button_id)
            value = 1
        else:
            self.pressed_btns.discard(button_id)
            value = 0
        self._ui.write(e.EV_KEY, button_id, value)

    def release_all_button(self) -> None:
        for button_id in self.pressed_btns:
            self.send_button(button_id, False)

    def syn(self) -> None:
        self._ui.syn()

    def close(self) -> None:
        self._ui.close()


class UInputKeyboardDevice(BaseKeyboardVirtualDevice):
    def __init__(
        self,
        name: str = 'Pynergy UInput vKeyboard',
        vendor: int = 0x1234,
        product: int = 0x5678,
        version: int = 1,
    ):
        """创建虚拟键盘设备

        Args:
            name: 设备名称
            vendor: 厂商 ID
            product: 产品 ID
            version: 版本号
        """
        super().__init__()
        capabilities = {
            e.EV_KEY: range(1, 256),
            e.EV_LED: [e.LED_CAPSL, e.LED_NUML, e.LED_SCROLLL],  # 声明 LED 灯
        }
        self._ui = evdev.UInput(
            events=capabilities,  # type: ignore[arg-type]
            name=name,
            vendor=vendor,
            product=product,
            version=version,
        )

    def send_key(self, key_code: int, down: bool) -> None:
        if down:
            self.pressed_keys.add(key_code)
            value = 1
        else:
            self.pressed_keys.discard(key_code)
            value = 0

        self._ui.write(e.EV_KEY, key_code, value)

    def release_all_key(self) -> None:
        for key_code in self.pressed_keys:
            self.send_key(key_code, False)

    def sync_modifiers(self, modifiers: int) -> None:
        """同步修饰键状态，使用 sysfs 规避 uinput 阻塞问题"""

        # 1. 定义 Lock 键映射 (Mask, Sysfs 名称, 按键 Ecode)
        lock_keys = [
            (ModifierKeyMask.CapsLock, 'capslock', e.KEY_CAPSLOCK),
            (ModifierKeyMask.NumLock, 'numlock', e.KEY_NUMLOCK),
            (ModifierKeyMask.ScrollLock, 'scrolllock', e.KEY_SCROLLLOCK),
        ]

        for mask, sysfs_name, key_code in lock_keys:
            target_state = bool(modifiers & mask)
            # 通过 sysfs 获取物理 / 系统真实的锁定状态
            local_state = get_led_state_sysfs(sysfs_name)

            if target_state != local_state:
                logger.debug(
                    f'[Modifier] {sysfs_name} 状态不一致: '
                    f'Remote={target_state}, Local={local_state}. 发送翻转按键.'
                )
                # 模拟敲击以同步状态
                self.send_key(key_code, True)
                self.send_key(key_code, False)
            else:
                # 只有在调试高频问题时才开启这一行，否则日志会很多
                # logger.debug(f"[Modifier] {sysfs_name} 已同步: {local_state}")
                pass

        # 2. 处理普通修饰键 is this neccasry?
        normal_mods = [
            (ModifierKeyMask.Shift, e.KEY_LEFTSHIFT),
            (ModifierKeyMask.Control, e.KEY_LEFTCTRL),
            (ModifierKeyMask.Alt, e.KEY_LEFTALT),
            (ModifierKeyMask.AltGr, e.KEY_RIGHTALT),
            (ModifierKeyMask.Meta, e.KEY_LEFTMETA),
            (ModifierKeyMask.Super, e.KEY_LEFTMETA),
            (ModifierKeyMask.Level5Lock, e.KEY_RIGHTCTRL),
        ]

        changed = self.current_modifiers ^ modifiers
        if changed:
            for mask, key_code in normal_mods:
                if changed & mask:
                    is_pressed = bool(modifiers & mask)
                    logger.debug(
                        f'[Modifier] 普通键位变化: {mask.name} -> '
                        f'{"Press" if is_pressed else "Release"} (code={key_code})'
                    )
                    self.send_key(key_code, is_pressed)

        # 3. 更新当前记录的状态
        self.current_modifiers = modifiers

    def syn(self) -> None:
        self._ui.syn()

    def close(self) -> None:
        self._ui.close()


def get_led_state_sysfs(led_name: str) -> bool:
    """
    led_name 可能是: 'input3::capslock' 或 '*::capslock'
    NixOS 下路径通常在 /sys/class/leds/
    """
    import glob

    # 匹配所有注册为 capslock 的 LED
    paths = glob.glob(f'/sys/class/leds/*::{led_name}/brightness')
    for path in paths:
        try:
            with open(path, 'r') as f:
                if f.read().strip() != '0':
                    return True
        except Exception as e:
            logger.warning(f'Error reading LED state: {e}')
            continue
    return False
