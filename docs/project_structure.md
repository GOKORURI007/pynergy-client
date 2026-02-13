既然 `pynergy-client` 本身也是一个需要运行的实体（Client），那么最合理的架构是将它作为 Workspace 的*
*根项目**或者**成员项目之一**。

在 `uv` 的 Workspace 模式下，通常建议将 Client 放在根目录，而将协议和配置工具作为成员包（Members）。

### 1. 推荐的目录结构

在这种结构下，`pynergy-client` 负责业务逻辑，并通过 `uv` 自动建立的“编辑模式（Editable）”直接调用同级目录下的子包。

```text
pynergy-client/           # 顶级目录 (Git/jj 仓库根目录)
├── pyproject.toml        # 整个 Workspace 的定义 + Client 本身的元数据
├── .python-version
├── src/
│   └── pynergy_client/   # Client 本身的源码
│       └── main.py       # 这里可以使用 'import pynergy_protocol'
├── pynergy_protocol/             # pynergy-protocol 子包
│   ├── pyproject.toml
│   └── src/pynergy_protocol/
└── pyhid_map/              # pyhid-map 子包
    ├── pyproject.toml
    └── src/pyhid_map/

```

### 2. `uv` 配置文件示例

#### 根目录 `pyproject.toml` (Client)

这里定义了 Client 的身份，并声明了对子包的本地路径依赖。

```toml
[project]
name = "pynergy-client"
version = "0.1.0"
dependencies = [
    "loguru",
    "pynergy-protocol", # 直接引用成员包名
    "pyhid-map", # 直接引用成员包名
]

[tool.uv.workspace]
members = ["protocol", "keymaps"]

# 关键：告诉 uv 去哪里找这两个包的源码
[tool.uv.sources]
pynergy-protocol = { path = "./protocol" }
pyhid-map = { path = "./keymaps" }

```

#### 子包 `protocol/pyproject.toml`

子包保持独立，拥有自己的依赖和 Logger 配置。

```toml
[project]
name = "pynergy-protocol"
version = "0.1.0"
dependencies = ["loguru"]

```

---

### 3. 如何应对“上游仓库不同”

这是你需求中最核心的挑战。既然 `protocol` 和 `keymaps` 有各自的上游，你可以选择以下方案：

#### 方案 A：Jujutsu (推荐)

`jj` 处理多仓库非常灵活。你可以只初始化一个 `jj` 仓库在根目录，但添加多个 Git Remote：

* `remote add origin <client-url>`
* `remote add proto-origin <protocol-url>`
* `remote add map-origin <keymap-url>`

你可以利用 `jj` 的 **Revset** 功能，通过 `jj push -r "namespace(proto)" proto-origin`
（或类似逻辑）来针对性推送特定目录的修改。`jj` 并不强制物理隔离，它更关注变更集（Changeset）。

#### 方案 B：Git Subtree (优于 Submodule)

如果你坚持使用 Git，我建议用 `git subtree` 而不是 `submodule`。

* **Subtree** 会将子仓库的代码直接合并进主仓库。
* 当你修改了 `protocol/` 下的代码，你可以运行 `git subtree push --prefix=protocol proto-origin main`
  将该目录单独推送到它的独立仓库。
* **优点**：主仓库克隆后直接就能跑，不需要额外的 `submodule init`。

---

### 4. Logger 的隔离

在 `uv` Workspace 下，由于每个包都有独立的 `src` 布局，你在 Client 中调用时，Logger 的管理会变得非常清晰：

```python
# pynergy_protocol/src/pynergy_protocol/core.py
from loguru import logger

# 子包内部定义的 logger 会带有自己的 context
log = logger.bind(name="pynergy_protocol")

# src/pynergy_client/main.py
from pynergy_protocol.core import log as proto_log
from loguru import logger

client_log = logger.bind(name="client")


def run():
    client_log.info("Client 启动")
    proto_log.info("正在解析协议")  # 这条日志会自动带有 pynergy_protocol 标识

```

**下一步建议：**
如果你需要，我可以为你生成一个用于初始化整个结构的 **Shell 脚本**（包含 `uv init` 和目录创建指令），或者详细展示如何在
**NixOS** 环境下通过 `shell.nix` 自动挂载这些开发工具？
