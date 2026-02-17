# Pynergy

![GitHub License](https://img.shields.io/github/license/GOKORURI007/sync-clipboard?link=https%3A%2F%2Fgithub.com%2FGOKORURI007%2Fpynergy%2Fblob%2Fmaster%2FLICENSE)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)

[English](../README.md) | [简体中文](./README-zhCN.md)

Pynergy 是一个基于 Synergy 协议的键鼠共享客户端，理论上兼容所有基于 Synergy 协议的同类软件 ( 如
Deskflow)。
其源于大量 Wayland Compositor 没有实现 RemoteDesktop portal，导致无法使用 Deskflow 共享键鼠。

## 当前功能状态

- 服务端 (不可用，服务端推荐使用 Deskflow)
- 客户端
    - [x] remote control
    - [x] tsl
    - [ ] clipboard sharing (
      可同时使用其他软件，如 [sync-clipboard](https://github.com/GOKORURI007/sync-clipboard)
    - [ ] file transfer

## 安装

### 1. 从源码安装

```bash
git clone https://github.com/GOKORURI007/pynergy.git
cd pynergy
uv sync --all-packages
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

## 快速开始

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

### 2. systemd 启动 (Auto restart)

1. 复制下方设置到 `~/.config/systemd/user/`

```ini
[Service]
ExecStart = /path/to/pynergy-client
Restart = always
RestartSec = 5
Type = simple

[Unit]
After = graphical-session.target
Description = pynergy-client kvm client
PartOf = graphical-session.target
StartLimitBurst = 15
StartLimitIntervalSec = 120
```

2. 修改 `ExecStart` 中的 `/path/to/pynergy-client` 为实际的 `pynergy-client` 路径

3. 执行 `systemctl --user enable --now pynergy-client`




