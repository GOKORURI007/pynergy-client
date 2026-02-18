<div style="text-align: center;">

# Pynergy

![GitHub License](https://img.shields.io/github/license/GOKORURI007/pynergy?link=https%3A%2F%2Fgithub.com%2FGOKORURI007%2Fpynergy%2Fblob%2Fmaster%2FLICENSE)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)

[English](../README.md) | [简体中文](./README-zhCN.md)

** 基于 Synergy 协议的键鼠共享客户端，专为 Wayland 设计 **

[功能特性](#功能特性) • [快速开始](#快速开始) • [安装指南](#安装) • [配置说明](#配置文件) • [贡献指南](#贡献指南)

</div>

---

Pynergy 是一个基于 Synergy 协议的键鼠共享客户端，理论上兼容所有基于 Synergy 协议的同类软件（如
Deskflow）。

该项目源于大量 Wayland Compositor 没有实现 RemoteDesktop portal，导致无法使用 Deskflow
共享键鼠的问题。Pynergy 通过直接使用 `uinput` 内核模块来模拟输入设备，绕过了 Wayland 的限制，实现了在
Wayland 环境下的键鼠共享功能。

## 功能特性

### 客户端

| 功能     | 状态     | 说明                                                                     |
|--------|--------|------------------------------------------------------------------------|
| 远程控制   | ✅ 已实现  | 支持鼠标和键盘的远程控制                                                           |
| TLS 加密 | ✅ 已实现  | 支持 TLS/mTLS 加密通信                                                       |
| 绝对坐标移动 | ✅ 已实现  | 支持绝对和相对鼠标移动模式                                                          |
| 剪贴板共享  | 🔄 待实现 | 可配合 [sync-clipboard](https://github.com/GOKORURI007/sync-clipboard) 使用 |
| 文件传输   | 🔄 待实现 | -                                                                      |

### 技术亮点

- **Wayland 支持 **：通过 `uinput` 内核模块直接模拟输入设备，无需依赖 RemoteDesktop portal，理论上任何支持
  uinput 的设备均可使用
- ** 多后端架构 **：模块化设计，便于扩展不同的输入后端
- ** 国际化支持 **：内置中英文语言包
- ** 灵活配置 **：支持命令行参数和配置文件两种方式
- ** 自动重连 **：配合 systemd 可实现崩溃后自动重启

## 安装

### 1. 从源码安装

> 可能需要安装 `libevdev` `libxkbcommon` `linuxHeaders` `libinput`。

```bash
git clone https://github.com/GOKORURI007/pynergy.git
cd pynergy
uv sync --all-packages
uv run main.py --help
# 或者
uv run pyinstaller pynergy-client.spec --clean
./dist/pynergy-client --help
```

### 2. 从 Release 安装

[Release](https://github.com/GOKORURI007/pynergy/releases)

### 3. NixOS 安装

1. 在 `flake.nix` 中添加 `pynergy` input

```bash
inputs = {
    #  ...
    pynergy-client = {
      url = "github:GOKORURI007/pynergy";
      inputs.nixpkgs.follows = "nixpkgs";
    };
}
```

2. 在 `configuration.nix` 中添加 `pynergy` 包

```bash
environment.systemPackages = [
  inputs.pynergy.packages.${stdenv.hostPlatform.system}.default
];
```

---

## 环境准备

> ⚠️ ** 重要 **：目前 **pynergy** 依赖 `uinput` 内核模块来模拟输入设备。为了让程序能够正常运行，你需要确保当前用户拥有访问
> `/dev/uinput` 的权限。

### 1. 通用 Linux 配置 (udev 规则)

在大多数主流发行版（如 Ubuntu, Debian, Arch, Fedora）中，推荐通过 `udev` 规则永久解决权限问题：

* ** 创建规则文件：**
  创建一个名为 `/etc/udev/rules.d/99-pynergy.rules` 的文件，内容如下：

```udev
KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
```

* ** 配置用户组：**
  将你的当前用户加入 `input` 组：

```bash
sudo usermod -aG input $USER
```

* ** 加载模块：**
  确保 `uinput` 模块已加载：

```bash
sudo modprobe uinput
```

> ** 注意：** 修改用户组后，通常需要 ** 注销并重新登录 ** 才能生效。

### 2. 特定发行版配置

#### NixOS

在 NixOS 中，你不应该手动修改 `/etc` 或使用 `usermod`。请在你的 `configuration.nix` 中添加以下配置：

```nix
{config, pkgs, ...}:

{
  # 允许用户访问 uinput
  services.udev.extraRules = ''
    # 允许 input 组读写 evdev 设备
    KERNEL=="event*", NAME="input/%k", MODE="0660", GROUP="input"
    # 允许 input 组读写 uinput 设备
    KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
  '';

  # 将你的用户加入 input 组
  users.users.<your_username>.extraGroups = [ "input" ];

  # 确保内核模块在启动时加载
  boot.kernelModules = [ "uinput" ];
}
```

#### Arch Linux / Fedora

这些发行版通常已经预设了 `input` 组。你只需要执行上述的 `usermod` 命令，并确保 `uinput` 模块在启动时自动加载：

```bash
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
```

### 3. 验证配置

配置完成后，可以通过以下命令检查权限是否正确：

```bash
ls -l /dev/uinput
```

如果输出显示所属组为 `input` 且具有读写权限（`crw-rw----`），则说明配置成功。

## 快速开始

### 1. 命令行启动

```bash
pynergy-client --server 192.168.1.1 --client-name my-client
```

详细选项：

```bash
pynergy-client --help

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --config                                         PATH                                               Path to the configuration file                                            │
│                                                                                                     [default: /home/yjc/.config/pynergy/client-config.json]                   │
│ --server                                         TEXT                                               Deskflow/Others server IP address [default: localhost]                    │
│ --port                                           INTEGER                                            Port number [default: 24800]                                              │
│ --client-name                                    TEXT                                               Client name [default: sipl-yjc]                                           │
│ --mouse-backend                                  [uinput]                                           Mouse backend                                                             │
│ --keyboard-backend                               [uinput]                                           Keyboard backend                                                          │
│ --tls                     --no-tls                                                                  Whether to use tls [default: no-tls]                                      │
│ --mtls                    --no-mtls                                                                 Whether to use mtls [default: no-mtls]                                    │
│ --tls-trust               --no-tls-trust                                                            Whether to trust the server [default: no-tls-trust]                       │
│ --screen-width                                   INTEGER                                            Screen width                                                              │
│ --screen-height                                  INTEGER                                            Screen height                                                             │
│ --abs-mouse-move          --no-abs-mouse-move                                                       Whether to use absolute displacement [default: no-abs-mouse-move]         │
│ --mouse-move-threshold                           INTEGER                                            Unit: ms, balances smoothness and performance [default: 8]                │
│ --mouse-pos-sync-freq                            INTEGER                                            Sync frequency, sync with system real position every n moves [default: 2] │
│ --logger-name                                    TEXT                                               Logger name [default: Pynergy]                                            │
│ --log-dir                                        TEXT                                               Log directory location [default: /home/yjc/.local/state/pynergy/log]      │
│ --log-file                                       TEXT                                               Log file name [default: pynergy.log]                                      │
│ --log-level-file                                 [TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL]  File log level [default: WARNING]                                         │
│ --log-level-stdout                               [TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL]  Console log level [default: INFO]                                         │
│ --help                                                                                              Show this message and exit.                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### 2. systemd 服务配置（自动重启）

创建 systemd 服务文件以实现开机自启和崩溃自动恢复：

```bash
cat > ~/.config/systemd/user/pynergy-client.service << 'EOF'
[Unit]
Description=Pynergy Client - Synergy Protocol KVM Client
PartOf=graphical-session.target
After=graphical-session.target

[Service]
ExecStart=/path/to/pynergy-client --server 192.168.1.1 --client-name my-client
Restart=always
RestartSec=5
Type=simple
StartLimitBurst=15
StartLimitIntervalSec=120

[Install]
WantedBy=default.target
EOF
```

然后启用并启动服务：

```bash
systemctl --user daemon-reload
systemctl --user enable --now pynergy-client
```

## 配置文件

配置文件默认位于 `~/.config/pynergy/client-config.json`，可通过 `--config` 选项指定配置文件路径。

示例：

```json
{
    "server": "localhost",
    "port": 24800,
    "client_name": "Pynergy",
    "screen_width": null,
    "screen_height": null,
    "mouse_backend": null,
    "keyboard_backend": null,

    "abs_mouse_move": false,
    "mouse_move_threshold": 8,
    "mouse_pos_sync_freq": 2,

    "tls": false,
    "mtls": false,
    "tls_trust": false,
    "pem_path": "~/.config/pynergy/pynergy.pem",

    "logger_name": "Pynergy",
    "log_dir": "~/.local/state/pynergy/log",
    "log_file": "pynergy.log",
    "log_level_file": "WARNING",
    "log_level_stdout": "INFO"
}
```

## 项目结构

```
pynergy/
├── packages/
│   ├── pynergy_client/          # 客户端实现
│   │   ├── src/pynergy_client/
│   │   │   ├── app.py           # 应用入口和 CLI 定义
│   │   │   ├── config.py        # 配置管理
│   │   │   ├── i18n.py          # 国际化支持
│   │   │   ├── utils.py         # 工具函数
│   │   │   ├── client/          # 客户端核心逻辑
│   │   │   │   ├── client.py    # 客户端主类
│   │   │   │   ├── dispatcher.py # 消息分发器
│   │   │   │   ├── handlers.py  # 协议消息处理器
│   │   │   │   └── protocols.py # 协议实现
│   │   │   ├── device/          # 输入设备模拟
│   │   │   │   ├── base.py      # 设备基类定义
│   │   │   │   ├── device.py    # 设备工厂
│   │   │   │   ├── backends/    # 后端实现
│   │   │   │   │   └── vdev_uinput.py  # uinput 后端
│   │   │   │   └── context/     # 设备上下文
│   │   │   │       └── device_ctx_wayland.py  # Wayland 上下文
│   │   │   └── keymaps/         # 键盘映射转换
│   │   │       ├── base.py      # 映射基类
│   │   │       ├── hid_map.py   # HID 映射
│   │   │       ├── synergy_map.py # Synergy 映射
│   │   │       ├── vk_map.py    # Virtual Key 映射
│   │   │       ├── ecode_map.py # Event Code 映射
│   │   │       └── utils.py     # 映射工具
│   │   └── pyproject.toml
│   │
│   └── pynergy_protocol/        # Synergy 协议实现
│       └── src/pynergy_protocol/
│           ├── core.py          # 协议核心逻辑
│           ├── messages.py      # 消息定义
│           ├── parser.py        # 消息解析器
│           ├── protocol_types.py # 协议类型
│           └── struct_types.py  # 结构体类型
│
├── docs/                        # 文档目录
│   ├── README-zhCN.md          # 中文文档
│   └── project_structure.md    # 项目结构详解
│
├── justfile                     # 任务运行器配置
├── pyproject.toml              # 项目配置
└── flake.nix                   # Nix flake 配置
```

### 架构说明

- **pynergy_protocol**：独立于客户端的协议实现库，负责 Synergy 协议的消息解析、打包和类型定义
- **pynergy_client**：客户端主程序，集成协议库并提供输入设备模拟、键盘映射转换等功能
- **模块化设计**：设备后端、键盘映射、协议处理均为独立模块，便于扩展和维护

## 贡献指南

### 代码规范

提交前请通过 `ruff` 格式化代码：

```bash
uv run scripts/format.py
# 或
just format
```

### 构建可执行文件

```bash
uv run pyinstaller pynergy-client.spec
```

### 功能修改指南

#### 示例 1：添加新的输入后端

1. 在 `packages/pynergy_client/src/pynergy_client/device/backends/` 中创建新文件
   `vdev_[backend_name].py`
2. 继承 `BaseMouseVirtualDevice` 或 `BaseKeyboardVirtualDevice` 基类
3. 实现基类中的所有 `abstractmethod` 方法
4. 修改 `utils.py`[utils.py](../packages/pynergy_client/src/pynergy_client/utils.py) 中的 `init_backend` 方法，添加对应的 case 分支
5. 在 `config.py`[config.py](../packages/pynergy_client/src/pynergy_client/config.py) 中的 `Available_Backends` 中注册新后端

#### 示例 2：扩展 Synergy 协议功能

> 💡 ** 提示 **：不建议通过 Synergy 协议实现剪贴板 / 文件共享，即使是 Deskflow 这样的成熟实现在这方面也不够稳定。

实现步骤：

1. 在 [messages.py](../packages/pynergy_protocol/src/pynergy_protocol/messages.py)`messages.py`
   的注释或 [Deskflow 官方文档](https://deskflow.github.io/deskflow/protocol_reference.html)
   中查找对应的消息类型
2. 修改 [messages.py](../packages/pynergy_protocol/src/pynergy_protocol/messages.py)`messages.py` 中对应的消息类，根据需要重写 `pack` 或 `unpack` 方法
3. 在 [handlers.py](../packages/pynergy_client/src/pynergy_client/client/handlers.py)`handlers.py` 中添加相应的消息处理器，实现具体功能

## Known Issue

- 快速在两个屏幕之间移动鼠标会导致一段时间无法选取文本

## 常见问题

### Q: 为什么在 Wayland 下需要使用 uinput？

A: Wayland 安全模型限制了 X11 时代的输入注入方式（如 XTest）。uinput 是 Linux 内核提供的标准输入模拟接口，不受
Wayland 限制，因此是 Wayland 环境下实现键鼠共享的最佳方案。

### Q: 是否支持 macOS 或 Windows？

A: 目前仅支持 Linux，主要针对使用 Wayland 的发行版。macOS 和 Windows 使用 Deskflow 即可。

### Q: 如何调试连接问题？

A: 可以通过以下方式启用详细日志：

```bash
pynergy-client --server <ip> --log-level-stdout DEBUG --log-level-file TRACE
```

日志文件默认位于 `~/.local/state/pynergy/log/pynergy.log`

## 致谢

- [Synergy](https://github.com/symless/synergy-core) - 原始协议实现
- [Deskflow](https://github.com/deskflow/deskflow) - Synergy 的开源分支

---

<div style="text-align: center;">

** 如果觉得这个项目对你有帮助，请给个 Star ⭐**

</div>
