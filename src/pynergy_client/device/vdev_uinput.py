from typing import Tuple

import evdev
from evdev import AbsInfo
from evdev import ecodes as e

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

        self.pressed_btns: set[int] = set()

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
            self.pressed_btns.remove(button_id)
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
        capabilities = {
            e.EV_KEY: range(1, 256),
        }
        self._ui = evdev.UInput(
            events=capabilities,  # type: ignore[arg-type]
            name=name,
            vendor=vendor,
            product=product,
            version=version,
        )

        self.pressed_keys = set()

    def send_key(self, key_code: int, down: bool) -> None:
        if down:
            self.pressed_keys.add(key_code)
            value = 1
        else:
            self.pressed_keys.remove(key_code)
            value = 0

        self._ui.write(e.EV_KEY, key_code, value)

    def release_all_key(self) -> None:
        for key_code in self.pressed_keys:
            self.send_key(key_code, False)

    def syn(self) -> None:
        self._ui.syn()

    def close(self) -> None:
        self._ui.close()
