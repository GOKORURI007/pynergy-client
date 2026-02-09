我为你设计一个 **Backend-agnostic 的输入控制架构 **，支持策略模式（Strategy Pattern）+ 工厂模式，便于后续扩展
Hyprland、X11、Windows、Darwin (macOS)、uinput 等后端。

## 目录结构

```text
input_control/
├── __init__.py              # 公开 API
├── abc.py                   # 抽象接口 (MouseBackend, KeyboardBackend)
├── types.py                 # 共享类型定义 (Point, Key, Button)
├── exceptions.py            # 自定义异常层级
├── config.py                # 配置管理 (Pydantic/BaseModel)
├── context.py               # 运行时上下文 (自动检测 / 手动指定后端)
└── backends/
    ├── __init__.py          # 后端注册表
    ├── base.py              # 后端基类 (共享工具方法)
    ├── hyprland.py          # Hyprland IPC 实现
    ├── x11.py               # X11/XTest 实现
    ├── windows.py           # Windows SendInput/win32api
    ├── evdev.py             # Linux evdev/uinput (仅键盘 / 绝对设备)
    └── dummy.py             # 测试用的空实现
```

## 核心代码实现

### 1. 抽象接口与类型 (`abc.py`, `types.py`)

```python
# types.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Point:
    x: int
    y: int


class MouseButton(Enum):
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()
    BACK = auto()
    FORWARD = auto()


class InputModifier(Enum):
    SHIFT = auto()
    CTRL = auto()
    ALT = auto()
    META = auto()  # Win/Cmd


# abc.py
from abc import ABC, abstractmethod
from typing import List, Optional
from .types import Point, MouseButton, InputModifier


class BackendCapabilities:
    """声明后端能力，用于运行时检查"""

    def __init__(self,
                 absolute_move: bool = False,
                 relative_move: bool = True,
                 scroll: bool = True,
                 keyboard: bool = True):
        self.absolute_move = absolute_move
        self.relative_move = relative_move
        self.scroll = scroll
        self.keyboard = keyboard


class BaseBackend(ABC):
    def __init__(self, config: dict):
        self.config = config
        self._caps = BackendCapabilities()

    @property
    def capabilities(self) -> BackendCapabilities:
        return self._caps

    @abstractmethod
    def initialize(self) -> None:
        """初始化连接/句柄"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """释放资源"""
        pass


class MouseBackend(BaseBackend):
    @abstractmethod
    def move_to(self, pos: Point, screen_id: Optional[int] = None) -> None:
        """绝对定位。screen_id 用于多显示器指定"""
        raise NotImplementedError("Absolute positioning not supported")

    @abstractmethod
    def move_rel(self, dx: int, dy: int) -> None:
        """相对移动"""
        pass

    @abstractmethod
    def click(self, button: MouseButton, duration_ms: float = 0) -> None:
        """duration_ms > 0 时模拟按住"""
        pass

    @abstractmethod
    def scroll(self, dx: int, dy: int) -> None:
        pass


class KeyboardBackend(BaseBackend):
    @abstractmethod
    def press(self, key: str, modifiers: List[InputModifier] = None) -> None:
        """key: 标准化名称如 'a', 'enter', 'f1'"""
        pass

    @abstractmethod
    def release(self, key: str) -> None:
        pass

    @abstractmethod
    def type_text(self, text: str, interval_ms: float = 0) -> None:
        """模拟逐字输入"""
        pass
```

### 2. Hyprland 实现 (`backends/hyprland.py`)

```python
import os
import socket
import json
from typing import List, Optional
from ..abc import MouseBackend, KeyboardBackend, BackendCapabilities
from ..types import Point, MouseButton, InputModifier
from ..exceptions import BackendError


class HyprlandBackend(MouseBackend, KeyboardBackend):
    """通过 Hyprland IPC 控制"""

    def __init__(self, config: dict):
        super().__init__(config)
        self._socket_path: Optional[str] = None
        self._caps = BackendCapabilities(
            absolute_move=True,  # 支持 movecursor
            relative_move=True,
            scroll=True,
            keyboard=True
        )
        # 按键映射表 Hyprland -> 标准名
        self._key_map = {
            'return': 'return', 'enter': 'return',
            'ctrl': 'CONTROL_L', 'alt': 'ALT_L',
            # ... 扩展映射
        }

    def initialize(self):
        runtime = os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
        sig = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
        if not sig:
            raise BackendError("Hyprland environment not detected")
        self._socket_path = f"{runtime}/hypr/{sig}/.socket.sock"

    def _send_command(self, cmd: str) -> str:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(self._socket_path)
                s.send(cmd.encode())
                return s.recv(4096).decode()
        except Exception as e:
            raise BackendError(f"Hyprland IPC error: {e}")

    def move_to(self, pos: Point, screen_id: Optional[int] = None):
        if not self._caps.absolute_move:
            raise NotImplementedError
        # Hyprland 使用全局坐标，无需处理 screen_id 转换
        self._send_command(f"dispatch movecursor {pos.x} {pos.y}")

    def move_rel(self, dx: int, dy: int):
        # Hyprland 没有原生相对 move，通过查询当前位置计算
        # 实际生产代码应缓存位置或解析 hyprctl 输出
        raise NotImplementedError("Hyprland prefers absolute coordinates")

    def click(self, button: MouseButton, duration_ms: float = 0):
        btn_map = {
            MouseButton.LEFT: "mouse:272",
            MouseButton.RIGHT: "mouse:273",
            MouseButton.MIDDLE: "mouse:274"
        }
        hypr_btn = btn_map.get(button, "mouse:272")
        self._send_command(f"dispatch sendshortcut , {hypr_btn}")  # 模拟按键
        # duration 处理需结合 sleep 和 release 命令

    def press(self, key: str, modifiers: List[InputModifier] = None):
        mod_str = self._translate_mods(modifiers)
        mapped = self._key_map.get(key.lower(), key)
        self._send_command(f"dispatch sendshortcut {mod_str}, {mapped}")

    def _translate_mods(self, mods: List[InputModifier]) -> str:
        # Hyprland 格式: SUPER_SHIFT_CTRL
        mapping = {
            InputModifier.CTRL: "CONTROL",
            InputModifier.ALT: "ALT",
            InputModifier.SHIFT: "SHIFT",
            InputModifier.META: "SUPER"
        }
        return "_".join(mapping[m] for m in mods) if mods else ""

    def cleanup(self):
        pass  # Unix socket 无需显式关闭
```

### 3. Windows 实现 (`backends/windows.py`)

```python
import ctypes
import time
from typing import List, Optional
from ..abc import MouseBackend, KeyboardBackend, BackendCapabilities
from ..types import Point, MouseButton, InputModifier
from ..exceptions import BackendError


class WindowsBackend(MouseBackend, KeyboardBackend):
    """基于 win32api SendInput"""

    def __init__(self, config: dict):
        super().__init__(config)
        self._caps = BackendCapabilities(absolute_move=True, relative_move=True)
        self.user32 = ctypes.windll.user32
        self._setup_constants()

    def _setup_constants(self):
        self.INPUT_MOUSE = 0
        self.INPUT_KEYBOARD = 1
        # ... 其他 Windows 常量定义

    def initialize(self):
        # 检查权限（可选）
        pass

    def move_to(self, pos: Point, screen_id: Optional[int] = None):
        # Convert to normalized coordinates (0-65535) for absolute input
        width = self.user32.GetSystemMetrics(0)
        height = self.user32.GetSystemMetrics(1)
        abs_x = int(pos.x * 65535 / width)
        abs_y = int(pos.y * 65535 / height)

        # 构造 INPUT 结构体发送
        # ... (具体 win32api 调用)

    def move_rel(self, dx: int, dy: int):
        # 使用 MOUSEEVENTF_MOVE
        pass

    def click(self, button: MouseButton, duration_ms: float = 0):
        # MOUSEEVENTF_LEFTDOWN/UP
        pass

    def cleanup(self):
        pass
```

### 4. 工厂与配置 (`factory.py`, `config.py`)

```python
# config.py
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class BackendConfig:
    backend_type: Literal["auto", "hyprland", "x11", "windows", "evdev", "dummy"]
    # 后端特定参数
    hyprland_socket: Optional[str] = None  # None 表示自动检测
    x11_display: Optional[str] = None  # :0.0
    evdev_mouse_device: Optional[str] = None
    evdev_kbd_device: Optional[str] = None


# factory.py
import os
import platform
from typing import Union
from .abc import MouseBackend, KeyboardBackend
from .config import BackendConfig
from .exceptions import NoSuitableBackend


def detect_platform_backend() -> str:
    """自动检测最佳后端"""
    if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        return "hyprland"
    elif os.environ.get('WAYLAND_DISPLAY'):
        return "wayland_generic"  # 未来实现
    elif os.environ.get('DISPLAY'):
        return "x11"
    elif platform.system() == "Windows":
        return "windows"
    elif platform.system() == "Linux":
        return "evdev"  # 兜底
    else:
        raise NoSuitableBackend("Unknown platform")


class InputController:
    """统一入口，聚合 Mouse + Keyboard"""

    def __init__(self, config: Optional[BackendConfig] = None):
        self.config = config or BackendConfig(backend_type="auto")
        self.mouse: MouseBackend
        self.keyboard: KeyboardBackend

        self._initialize_backends()

    def _initialize_backends(self):
        backend_type = self.config.backend_type
        if backend_type == "auto":
            backend_type = detect_platform_backend()

        # 根据类型导入并实例化（避免循环导入）
        if backend_type == "hyprland":
            from .backends.hyprland import HyprlandBackend
            self.mouse = HyprlandBackend(self.config.__dict__)
            self.keyboard = self.mouse  # Hyprland 同时实现两者
        elif backend_type == "windows":
            from .backends.windows import WindowsBackend
            self.mouse = WindowsBackend(self.config.__dict__)
            self.keyboard = self.mouse
        elif backend_type == "evdev":
            from .backends.evdev import EvdevMouseBackend, EvdevKeyboardBackend
            self.mouse = EvdevMouseBackend(self.config.__dict__)
            self.keyboard = EvdevKeyboardBackend(self.config.__dict__)
        # ... 其他后端

        # 统一初始化
        self.mouse.initialize()
        self.keyboard.initialize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mouse.cleanup()
        self.keyboard.cleanup()

    # 便捷方法代理
    def move_to(self, x: int, y: int):
        from .types import Point
        self.mouse.move_to(Point(x, y))

    def click(self):
        from .types import MouseButton
        self.mouse.click(MouseButton.LEFT)
```

## 使用示例

```python
from input_control import InputController, BackendConfig

# 1. 自动检测（在 Hyprland 上自动使用 IPC，Windows 上切 win32api）
with InputController() as ctrl:
    ctrl.move_to(500, 300)  # 绝对定位
    ctrl.click()
    ctrl.keyboard.type_text("Hello")

# 2. 显式指定后端（强制使用 evdev，无视环境）
config = BackendConfig(
    backend_type="evdev",
    evdev_kbd_device="/dev/input/event3"
)
with InputController(config) as ctrl:
    # 注意：evdev 鼠标通常不支持绝对定位，会抛 NotImplementedError
    pass

# 3. 运行时能力检查
if ctrl.mouse.capabilities.absolute_move:
    ctrl.move_to(100, 100)
else:
    # 回退到相对移动或报错
    pass
```

## 扩展建议

1. ** 坐标系转换器 **：在 `backends/base.py` 中加入 `CoordinateTransformer`，处理多显示器 DPI
   缩放（Windows）和 Wayland 输出布局（Hyprland 的 `monitors` 查询）。

2. ** 异步支持 **：将 `send_command` 改为 `async def`，使用 `asyncio.open_unix_connection` 处理
   Hyprland IPC，避免阻塞主循环。

3. ** 混入模式（Mixin）**：如果某后端只支持鼠标（如简单 evdev），可拆分为 `MouseBackend` +
   `KeyboardBackend` 两个独立实例，在 `InputController` 中组合。

4. **CLI 工具 **：打包为 `inputctl --backend hyprland move 100 100`，利用 `typer` 或 `click` 生成命令行接口。

这个结构确保你可以轻松添加新的后端（如 KDE KWin、macOS Quartz），而无需修改业务代码。
