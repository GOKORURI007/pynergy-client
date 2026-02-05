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
from evdev import UInput, ecodes as e

capabilities = {
    e.EV_KEY: [e.KEY_A, e.KEY_B, e.KEY_ENTER, ...],  # 键盘按键列表
    e.EV_REL: [e.REL_X, e.REL_Y],  # 鼠标相对移动
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT]  # 鼠标按键
}
ui = UInput(capabilities, name='pydeskflow-virtual-device')
```

### 第二阶段：协议实现

#### 握手阶段

```python
# 发送 Synergy 握手协议
msg = b'Synergy' + struct.pack('>HH', 1, 6)
header = struct.pack('>I', len(msg))
s.send(header + msg)
```

#### 消息解析

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
        # 计算相对位移或直接写入绝对坐标
        ui.write(e.EV_REL, e.REL_X, x_diff)
        ui.write(e.EV_REL, e.REL_Y, y_diff)
    elif cmd == b'DKDN':  # 按键按下
        key_code = struct.unpack('>H', msg[4:6])[0]
        linux_key = synergy_to_linux_keycode(key_code)
        ui.write(e.EV_KEY, linux_key, 1)
    elif cmd == b'DKUP':  # 按键释放
        key_code = struct.unpack('>H', msg[4:6])[0]
        linux_key = synergy_to_linux_keycode(key_code)
        ui.write(e.EV_KEY, linux_key, 0)

    ui.syn()  # 同步事件
```

### 第三阶段：键码映射

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
