<div style="text-align: center;">

# Pynergy

![GitHub License](https://img.shields.io/github/license/GOKORURI007/pynergy?link=https%3A%2F%2Fgithub.com%2FGOKORURI007%2Fpynergy%2Fblob%2Fmaster%2FLICENSE)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)

[English](./README.md) | [简体中文](./docs/README-zhCN.md)

**A keyboard and mouse sharing client based on the Synergy protocol, designed for Wayland**

[Features](#features) • [Quick Start](#quick-start) • [Installation](#installation) • [Configuration](#configuration) • [Contributing](#contributing)

</div>

---

Pynergy is a keyboard and mouse sharing client based on the Synergy protocol, theoretically compatible with all Synergy-based software (such as Deskflow).

This project originated from the issue where many Wayland Compositors have not implemented the RemoteDesktop portal, making it impossible to use Deskflow for keyboard and mouse sharing. Pynergy bypasses Wayland's limitations by directly using the `uinput` kernel module to simulate input devices, enabling keyboard and mouse sharing functionality in Wayland environments.

## Features

### Client

| Feature          | Status           | Description                                                                |
|------------------|------------------|----------------------------------------------------------------------------|
| Remote Control   | ✅ Implemented   | Supports remote control of mouse and keyboard                              |
| TLS Encryption   | ✅ Implemented   | Supports TLS/mTLS encrypted communication                                  |
| Absolute Movement| ✅ Implemented   | Supports both absolute and relative mouse movement modes                  |
| Clipboard Sharing| 🔄 To be Implemented | Can be used with [sync-clipboard](https://github.com/GOKORURI007/sync-clipboard) |
| File Transfer    | 🔄 To be Implemented | -                                                                          |

### Technical Highlights

- **Wayland Support**: Simulates input devices directly via the `uinput` kernel module without relying on the RemoteDesktop portal. Theoretically works on any device that supports uinput
- **Multi-backend Architecture**: Modular design for easy extension of different input backends
- **Internationalization Support**: Built-in Chinese and English language packs
- **Flexible Configuration**: Supports both command-line arguments and configuration files
- **Auto-reconnection**: Can automatically restart after crashes when used with systemd

## Installation

### 1. Install from Source

> You may need to install `libevdev` `libxkbcommon` `linuxHeaders` `libinput`.

```bash
git clone https://github.com/GOKORURI007/pynergy.git
cd pynergy
uv sync --all-packages
uv run main.py --help
# or
uv run pyinstaller pynergy-client.spec --clean
./dist/pynergy-client --help
```

### 2. Install from Release

[Release](https://github.com/GOKORURI007/pynergy/releases)

### 3. NixOS Installation

1. Add `pynergy` input in `flake.nix`

```bash
inputs = {
    #  ...
    pynergy-client = {
      url = "github:GOKORURI007/pynergy";
      inputs.nixpkgs.follows = "nixpkgs";
    };
}
```

2. Add `pynergy` package in `configuration.nix`

```bash
environment.systemPackages = [
  inputs.pynergy.packages.${stdenv.hostPlatform.system}.default
];
```

---

## Environment Setup

> ⚠️ **Important**: Currently, **pynergy** relies on the `uinput` kernel module to simulate input devices. For the program to run properly, you need to ensure that the current user has permission to access `/dev/uinput`.

### 1. General Linux Configuration (udev Rules)

In most mainstream distributions (such as Ubuntu, Debian, Arch, Fedora), it is recommended to permanently resolve permission issues through `udev` rules:

* **Create rule file:**
  Create a file named `/etc/udev/rules.d/99-pynergy.rules` with the following content:

```udev
KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
```

* **Configure user group:**
  Add your current user to the `input` group:

```bash
sudo usermod -aG input $USER
```

* **Load module:**
  Ensure the `uinput` module is loaded:

```bash
sudo modprobe uinput
```

> **Note:** After modifying user groups, you usually need to **log out and log back in** for the changes to take effect.

### 2. Distribution-specific Configuration

#### NixOS

In NixOS, you should not manually modify `/etc` or use `usermod`. Instead, add the following configuration to your `configuration.nix`:

```nix
{config, pkgs, ...}:

{
  # Allow users to access uinput
  services.udev.extraRules = ''
    # Allow input group to read/write evdev devices
    KERNEL=="event*", NAME="input/%k", MODE="0660", GROUP="input"
    # Allow input group to read/write uinput device
    KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
  '';

  # Add your user to the input group
  users.users.<your_username>.extraGroups = [ "input" ];

  # Ensure kernel modules are loaded at boot
  boot.kernelModules = [ "uinput" ];
}
```

#### Arch Linux / Fedora

These distributions typically have the `input` group pre-configured. You only need to execute the `usermod` command mentioned above and ensure that the `uinput` module is loaded automatically at startup:

```bash
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
```

### 3. Verify Configuration

After completing the configuration, you can check whether permissions are correctly set with the following command:

```bash
ls -l /dev/uinput
```

If the output shows that the group is `input` and it has read/write permissions (`crw-rw----`), the configuration is successful.

## Quick Start

### 1. Command Line Startup

```bash
pynergy-client --server 192.168.1.1 --client-name my-client
```

Detailed options:

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

### 2. systemd Service Configuration (Auto-restart)

Create a systemd service file to enable startup on boot and automatic crash recovery:

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

Then enable and start the service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now pynergy-client
```

## Configuration

The configuration file is located at `~/.config/pynergy/client-config.json` by default, and can be specified with the `--config` option.

Example:

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

## Project Structure

```
pynergy/
├── packages/
│   ├── pynergy_client/          # Client implementation
│   │   ├── src/pynergy_client/
│   │   │   ├── app.py           # Application entry and CLI definition
│   │   │   ├── config.py        # Configuration management
│   │   │   ├── i18n.py          # Internationalization support
│   │   │   ├── utils.py         # Utility functions
│   │   │   ├── client/          # Client core logic
│   │   │   │   ├── client.py    # Client main class
│   │   │   │   ├── dispatcher.py # Message dispatcher
│   │   │   │   ├── handlers.py  # Protocol message handlers
│   │   │   │   └── protocols.py # Protocol implementation
│   │   │   ├── device/          # Input device simulation
│   │   │   │   ├── base.py      # Device base class definition
│   │   │   │   ├── device.py    # Device factory
│   │   │   │   ├── backends/    # Backend implementations
│   │   │   │   │   └── vdev_uinput.py  # uinput backend
│   │   │   │   └── context/     # Device context
│   │   │   │       └── device_ctx_wayland.py  # Wayland context
│   │   │   └── keymaps/         # Keyboard mapping conversion
│   │   │       ├── base.py      # Mapping base class
│   │   │       ├── hid_map.py   # HID mapping
│   │   │       ├── synergy_map.py # Synergy mapping
│   │   │       ├── vk_map.py    # Virtual Key mapping
│   │   │       ├── ecode_map.py # Event Code mapping
│   │   │       └── utils.py     # Mapping utilities
│   │   └── pyproject.toml
│   │
│   └── pynergy_protocol/        # Synergy protocol implementation
│       └── src/pynergy_protocol/
│           ├── core.py          # Protocol core logic
│           ├── messages.py      # Message definitions
│           ├── parser.py        # Message parser
│           ├── protocol_types.py # Protocol types
│           └── struct_types.py  # Struct types
│
├── docs/                        # Documentation directory
│   ├── README-zhCN.md          # Chinese documentation
│   └── project_structure.md    # Detailed project structure
│
├── justfile                     # Task runner configuration
├── pyproject.toml              # Project configuration
└── flake.nix                   # Nix flake configuration
```

### Architecture Overview

- **pynergy_protocol**: An independent protocol implementation library responsible for Synergy protocol message parsing, packing, and type definitions
- **pynergy_client**: The main client program that integrates the protocol library and provides input device simulation, keyboard mapping conversion, and other features
- **Modular Design**: Device backends, keyboard mappings, and protocol processing are all independent modules for easy extension and maintenance

## Development Guide

### Code Style

Please format your code with `ruff` before committing:

```bash
uv run scripts/format.py
# or
just format
```

### Build Executable

```bash
uv run pyinstaller pynergy-client.spec
```

### Feature Modification Guide

#### Example 1: Adding a New Input Backend

1. Create a new file `vdev_[backend_name].py` in `packages/pynergy_client/src/pynergy_client/device/backends/`
2. Inherit from `BaseMouseVirtualDevice` or `BaseKeyboardVirtualDevice` base class
3. Implement all `abstractmethod` methods in the base class
4. Modify the `init_backend` method in [utils.py](../packages/pynergy_client/src/pynergy_client/utils.py) to add the corresponding case branch
5. Register the new backend in `Available_Backends` in [config.py](../packages/pynergy_client/src/pynergy_client/config.py)

#### Example 2: Extending Synergy Protocol Functionality

> 💡 **Tip**: It is not recommended to implement clipboard/file sharing via the Synergy protocol, as even mature implementations like Deskflow are not stable enough in this regard.

Implementation steps:

1. Find the corresponding message type in the comments of [messages.py](../packages/pynergy_protocol/src/pynergy_protocol/messages.py) or in the [Deskflow official documentation](https://deskflow.github.io/deskflow/protocol_reference.html)
2. Modify the corresponding message class in [messages.py](../packages/pynergy_protocol/src/pynergy_protocol/messages.py), overriding the `pack` or `unpack` methods as needed
3. Add the corresponding message handler in [handlers.py](../packages/pynergy_client/src/pynergy_client/client/handlers.py) to implement the specific functionality

## Known Issues

- Quickly moving the mouse between two screens results in an inability to select text for a period of time

## FAQ

### Q: Why do I need to use uinput under Wayland?

A: Wayland's security model restricts X11-era input injection methods (such as XTest). uinput is a standard input simulation interface provided by the Linux kernel that is not restricted by Wayland, making it the best solution for implementing keyboard and mouse sharing in Wayland environments.

### Q: Is macOS or Windows supported?

A: Currently only Linux is supported, primarily for distributions using Wayland. For macOS and Windows, you can use Deskflow.

### Q: How do I debug connection issues?

A: You can enable verbose logging with the following command:

```bash
pynergy-client --server <ip> --log-level-stdout DEBUG --log-level-file TRACE
```

The log file is located at `~/.local/state/pynergy/log/pynergy.log` by default

## Acknowledgments

- [Synergy](https://github.com/symless/synergy-core) - Original protocol implementation
- [Deskflow](https://github.com/deskflow/deskflow) - Open source fork of Synergy

---

<div style="text-align: center;">

**If you find this project helpful, please give it a Star ⭐**

</div>
