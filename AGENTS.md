# PyDeskFlow - Unsafe Client

**⚠️ 语言规范：本文档及所有代码注释、思考过程均使用中文书写。**

---

## 项目概述

一个基于 Python 的 Synergy/Barrier 客户端，通过 `/dev/uinput` 直接向 Hyprland 注入输入事件。

## 核心需求

### 功能要求

1. ** 网络连接 **：连接 Synergy/Barrier 服务器（TCP 24800 端口）
2. ** 协议解析 **：解析 Synergy 协议消息并分发
3. ** 虚拟设备 **：使用 python-evdev 创建虚拟输入设备
4. ** 事件注入 **：向 Hyprland Wayland 合成器注入鼠标 / 键盘事件

### 需要处理的协议消息

- `DMMV`：鼠标移动（绝对坐标）
- `DKDN` / `DKUP`：按键按下 / 释放
- `DMDN` / `DMUP`：鼠标按键按下 / 释放

## 实现步骤

### 第一阶段：虚拟输入设备

使用 `evdev.UInput` 创建虚拟键盘和鼠标：

```python
import evdev
from src.keymaps.ecode_map import ECODE_TO_HID

# Create a comprehensive set of capabilities to ensure the device is recognized as a mouse
events = {
    evdev.ecodes.EV_REL: [
        evdev.ecodes.REL_X,
        evdev.ecodes.REL_Y,
        evdev.ecodes.REL_WHEEL,
        evdev.ecodes.REL_HWHEEL,
    ],
    evdev.ecodes.EV_KEY: [
        # Mouse buttons
        evdev.ecodes.BTN_LEFT,
        evdev.ecodes.BTN_RIGHT,
        evdev.ecodes.BTN_MIDDLE,
        evdev.ecodes.BTN_SIDE,
        evdev.ecodes.BTN_EXTRA,
        # Keyboard keys
        *[code if code <= 0xFF else (code >> 8) for code in ECODE_TO_HID.keys()],
    ],
}

device = evdev.UInput(
    events=events,
    name='InputFlow Virtual Mouse',
    vendor=0x1234,  # Fake vendor ID
    product=0x5678,  # Fake product ID
    version=1,
)
```

### 第二阶段：协议实现

实现 Synergy 协议消息的解析和封装。

#### 握手阶段

```python
# 发送 Synergy 握手协议
msg = b'Synergy' + struct.pack('>HH', 1, 6)
header = struct.pack('>I', len(msg))
s.send(header + msg)
```

#### 消息接收与解析

```python
while True:
    # 读取 4 字节长度头部
    len_data = s.recv(4)
    msg_len = struct.unpack('>I', len_data)[0]

    # 读取消息体
    msg = s.recv(msg_len)
    cmd = msg[:4]  # 命令标识符

    if cmd == b'DMMV':  # 鼠标移动
        x, y = struct.unpack('>HH', msg[4:8])
        # 返回解析结果，由客户端决定如何处理坐标
        return ('DMMV', {'x': x, 'y': y})
    elif cmd == b'DKDN':  # 按键按下
        key_code = struct.unpack('>H', msg[4:6])[0]
        return ('DKDN', {'key_code': key_code})
    elif cmd == b'DKUP':  # 按键释放
        key_code = struct.unpack('>H', msg[4:6])[0]
        return ('DKUP', {'key_code': key_code})
    elif cmd == b'DMDN':  # 鼠标按键按下
        button = struct.unpack('>H', msg[4:6])[0]
        return ('DMDN', {'button': button})
    elif cmd == b'DMUP':  # 鼠标按键释放
        button = struct.unpack('>H', msg[4:6])[0]
        return ('DMUP', {'button': button})
```

#### 消息类型定义

| 消息类型   | 格式    | 参数                                 |
|--------|-------|------------------------------------|
| `DMMV` | `>HH` | x, y 绝对坐标 (0-65535)                |
| `DKDN` | `>H`  | key_code 按键代码                      |
| `DKUP` | `>H`  | key_code 按键代码                      |
| `DMDN` | `>H`  | button 鼠标按钮代码 (假设与 Linux BTN_* 一致) |
| `DMUP` | `>H`  | button 鼠标按钮代码                      |

### 第三阶段：客户端实现

实现主客户端逻辑，包括网络连接、消息处理循环和命令行参数解析。

#### 命令行参数

使用 Click 库解析命令行参数：

```python
import click
from click import Context


@click.command()
@click.option('--server', '-s', required=True, help='Synergy 服务器 IP 地址')
@click.option('--port', '-p', default=24800, help='端口号 (默认: 24800)')
@click.option('--coords-mode', type=click.Choice(['relative', 'absolute']),
              default='relative', help='坐标模式: relative=相对位移, absolute=绝对坐标')
def main(server: str, port: int, coords_mode: str):
    client = SynergyClient(server, port, coords_mode=coords_mode)
    client.run()
```

#### 主事件循环

```python
def run(self):
    self.connect()
    while self._running:
        msg = self._protocol.recv_message(self.sock)
        msg_type, params = self._protocol.parse_message(msg)
        self._handle_message(msg_type, params)


def _handle_message(self, msg_type, params):
    if msg_type == 'DMMV':
        x, y = params['x'], params['y']
        if self.coords_mode == 'relative':
            dx, dy = self._abs_to_rel(x, y)
            self._device.write_mouse_move(dx, dy)
        else:
            self._device.write_mouse_abs(x, y)
    elif msg_type == 'DKDN':
        self._device.write_key(params['key_code'], True)
    elif msg_type == 'DKUP':
        self._device.write_key(params['key_code'], False)
    elif msg_type == 'DMDN':
        self._device.write_key(params['button'], True)
    elif msg_type == 'DMUP':
        self._device.write_key(params['button'], False)
    self._device.syn()
```

### 第四阶段：坐标映射

将 Synergy 的绝对坐标（0-65535）转换为 Linux 输入事件。

#### 可配置坐标模式

通过 `--coords-mode` 参数选择坐标处理策略：

| 模式         | 说明      | 使用场景                |
|------------|---------|---------------------|
| `relative` | 转换为相对位移 | 需要已知屏幕分辨率           |
| `absolute` | 使用绝对坐标  | 需要 UInput 配置 EV_ABS |

#### 相对位移模式

```python
def _abs_to_rel(self, x: int, y: int) -> tuple[int, int]:
    """将 Synergy 绝对坐标转换为相对位移

    Args:
        x: 0-65535 范围的绝对坐标
        y: 0-65535 范围的绝对坐标

    Returns:
        (dx, dy) 相对位移
    """
    if not hasattr(self, '_last_x') or self._last_x is None:
        self._last_x, self._last_y = x, y
        return 0, 0

    # 根据屏幕分辨率归一化
    screen_width = self.screen_width or 1920
    screen_height = self.screen_height or 1080

    # 计算相对位移（缩放到合理范围）
    dx = int((x - self._last_x) * (screen_width / 65535))
    dy = int((y - self._last_y) * (screen_height / 65535))

    self._last_x, self._last_y = x, y
    return dx, dy
```

#### 绝对坐标模式

需要扩展 VirtualDevice 支持 EV_ABS 事件：

```python
# 在 VirtualDevice 中添加
def _setup_capabilities(self) -> dict:
    capabilities = {
        evdev.ecodes.EV_ABS: [
            (ecodes.ABS_X, (0, 65535, 0, 0)),
            (ecodes.ABS_Y, (0, 65535, 0, 0)),
        ],
        # ... 其他事件类型
    }
    return capabilities


def write_mouse_abs(self, x: int, y: int) -> None:
    """写入绝对坐标"""
    self._ui.write(ecodes.EV_ABS, ecodes.ABS_X, x)
    self._ui.write(ecodes.EV_ABS, ecodes.ABS_Y, y)
```

### 第五阶段：键码映射

创建 Synergy 键码到 Linux 键码的映射表。参考 Barrier 源码中的 KeyMap 实现。

### 第四阶段：坐标映射

将 Synergy 的绝对坐标（0-65535）转换为相对位移，或配置 UInput 使用 EV_ABS 绝对坐标模式。

## 主要挑战

1. ** 键码映射 **：Synergy 使用自定义键码，需要手动建立映射表
2. ** 坐标转换 **：绝对坐标 → 相对位移的转换
3. ** 权限管理 **：需要 `/dev/uinput` 读写权限
4. ** 协议完整性 **：最小化实现，跳过剪贴板同步和加密

## 文件结构

```
pydeskflow-unsafe-client/
├── AGENTS.md                    # 本文档
├── src/
│   ├── client.py                # 主客户端入口
│   ├── protocol.py              # Synergy 协议解析
│   ├── device.py                # 虚拟输入设备管理
│   └── mapping.py               # 键码和坐标映射
└── tests/                       # 测试目录
```

## 运行客户端

```bash
uv run python -m src.client --server < 服务器 IP 地址 >
```

---

## 语言规范说明

** 重要提示 **：本项目所有文档、注释、思考过程均使用中文书写。

- 代码注释使用中文
- Git 提交信息使用中文
- README 和文档使用中文
- 开发者交流使用中文

这样做的目的是：

1. 提高代码可读性，便于团队协作
2. 降低学习门槛，方便后续维护
3. 统一项目语言风格
