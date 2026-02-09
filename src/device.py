"""
虚拟输入设备模块

使用 python-evdev 创建虚拟输入设备，向系统注入鼠标和键盘事件。
"""

from typing import Mapping, Sequence

import evdev
from evdev import ecodes

from src.keymaps.ecode_map import ECODE_TO_HID


class VirtualDevice:
    """虚拟输入设备类

    通过 UInput 向系统注入鼠标和键盘事件。
    用于模拟来自 Synergy/Barrier 服务器的输入。
    """

    def __init__(
        self,
        name: str = 'PyDeskFlow Virtual Input',
        vendor: int = 0x1234,
        product: int = 0x5678,
        version: int = 1,
    ):
        """初始化虚拟设备

        Args:
            name: 设备名称
            vendor: 厂商 ID
            product: 产品 ID
            version: 版本号
        """
        self.name = name
        self._capabilities = self._setup_capabilities()
        self._ui = evdev.UInput(
            events=self._capabilities,  # type: ignore[arg-type]
            name=name,
            vendor=vendor,
            product=product,
            version=version,
        )

    def _setup_capabilities(self) -> Mapping[int, Sequence[int]]:
        """配置设备事件能力

        Returns:
            事件能力字典
        """
        capabilities: dict[int, list[int]] = {
            ecodes.EV_REL: [
                ecodes.REL_X,
                ecodes.REL_Y,
                ecodes.REL_WHEEL,
                ecodes.REL_HWHEEL,
            ],
            ecodes.EV_KEY: self._get_key_codes(),
        }
        return capabilities

    @staticmethod
    def _get_key_codes() -> list[int]:
        """获取所有按键代码

        包含鼠标按钮和键盘按键。

        Returns:
            按键代码列表
        """
        key_codes = [
            ecodes.BTN_LEFT,
            ecodes.BTN_RIGHT,
            ecodes.BTN_MIDDLE,
            ecodes.BTN_SIDE,
            ecodes.BTN_EXTRA,
        ]
        for ecode in ECODE_TO_HID.keys():
            key_codes.append(ecode)
        return key_codes

    def write_mouse_move(self, dx: int, dy: int) -> None:
        """写入鼠标移动事件

        Args:
            dx: X 轴相对位移
            dy: Y 轴相对位移
        """
        self._ui.write(ecodes.EV_REL, ecodes.REL_X, dx)
        self._ui.write(ecodes.EV_REL, ecodes.REL_Y, dy)

    def write_wheel(self, dy: int = 0, dx: int = 0) -> None:
        """写入滚轮事件

        Args:
            dy: 垂直滚轮位移
            dx: 水平滚轮位移
        """
        if dy != 0:
            self._ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, dy)
        if dx != 0:
            self._ui.write(ecodes.EV_REL, ecodes.REL_HWHEEL, dx)

    def write_key(self, key_code: int, pressed: bool) -> None:
        """写入按键事件

        Args:
            key_code: Linux 按键代码
            pressed: True 为按下，False 为释放
        """
        value = 1 if pressed else 0
        self._ui.write(ecodes.EV_KEY, key_code, value)

    def write(self, event_type: int, event_code: int, value: int) -> None:
        """写入任意事件

        Args:
            event_type: 事件类型 (EV_REL, EV_KEY, EV_ABS 等)
            event_code: 事件代码
            value: 事件值
        """
        self._ui.write(event_type, event_code, value)

    def syn(self) -> None:
        """同步事件

        将所有待处理的事件提交给系统。
        """
        self._ui.syn()

    def close(self) -> None:
        """关闭设备

        释放 UInput 设备资源。
        """
        self._ui.close()

    def __enter__(self) -> 'VirtualDevice':
        """上下文管理器入口

        Returns:
            设备实例
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出

        自动关闭设备。
        """
        self.close()
