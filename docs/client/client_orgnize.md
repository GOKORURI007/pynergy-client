实现一个健壮的 Synergy Client，核心挑战在于如何处理 ** 非阻塞 IO**、** 心跳维护 ** 以及 **
状态切换 **。

由于你之前已经有了高度自动化的 `protocol` 包，Client 的职责就是作为一个“驱动器”来运行这些逻辑。

---

## 1. 推荐的文件目录结构

将业务逻辑（Client）与协议解析（Protocol）彻底分开。

```text
pydeskflow/
├── src/
│   ├── protocol/            # 你之前实现的协议包
│   │   ├── __init__.py
│   │   ├── core.py          # MsgBase, Registry
│   │   ├── messages.py      # HelloMsg, KeyMsg...
│   │   └── parser.py        # SynergyParser
│   ├── client/              # 客户端实现
│   │   ├── __init__.py
│   │   ├── connection.py    # 核心：负责 Socket 读写与心跳
│   │   ├── handlers.py      # 业务：处理收到消息后的具体动作
│   │   └── states.py        # 状态定义 (Connecting, Handshaking, Ready)
│   └── main.py              # 入口：配置加载与启动
└── tests/                   # 单元测试

```

---

## 2. 核心类分布与职责

### A. `Connection` (连接管理器)

这是 Client 的心脏。它持有 `socket` 和 `SynergyParser` 实例。

* ** 职责 **：
* 维护底层连接。
* 运行 `recv` 循环并调用 `parser.feed()`。
* 定时发送心跳包（KeepAlive）。
* 提供 `send_msg(msg: MsgBase)` 统一发送接口。

### B. `SynergyClient` (高层抽象)

* ** 职责 **：
* 协调 `Connection` 和 `Handshake` 流程。
* 维护当前客户端的状态（如：是否已经握手成功）。
* 作为用户（开发者）调用的主入口。

### C. `MessageHandler` (消息分发器)

* ** 职责 **：
* 接收解析出来的 `MsgBase` 对象。
* 根据消息类型（如 `MouseDict`），执行具体的本地操作（如移动鼠标）。

---

## 3. 核心实现示例

### connection.py: 基础通信

这里展示一个基于 `select` 的准异步模型，它是 Python 实现同步 Client 最稳妥的方式。

```python
import socket
import select
import time
from loguru import logger
from ..protocol.parser import SynergyParser


class SynergyConnection:
    def __init__(self, host: str, port: int):
        self.address = (host, port)
        self.sock = None
        self.parser = SynergyParser()
        self.last_heartbeat = 0
        self._running = False

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)  # 设为非阻塞
        try:
            self.sock.connect(self.address)
        except BlockingIOError:
            pass  # 连接进行中

    def run_once(self, timeout=0.1):
        """主循环的单次迭代"""
        # 使用 select 监听可读事件
        readable, _, _ = select.select([self.sock], [], [], timeout)

        if readable:
            data = self.sock.recv(4096)
            if not data:
                return False  # 连接断开

            self.parser.feed(data)
            while (msg := self.parser.next_msg()):
                yield msg  # 吐出解析好的对象

        # 处理心跳 (例如每 5 秒发一次)
        if time.time() - self.last_heartbeat > 5:
            self.send_heartbeat()
        return True

    def send_msg(self, msg):
        data = msg.pack()
        # 注意：这里需要根据协议加上 4 字节长度头
        header = struct.pack(">I", len(data))
        self.sock.sendall(header + data)

    def send_heartbeat(self):
        # 假设心跳是某种特定的消息
        # self.send_msg(KeepAliveMsg())
        self.last_heartbeat = time.time()

```

### handlers.py: 业务分发

```python
class MessageDispatcher:
    def __init__(self, client):
        self.client = client

    def dispatch(self, msg):
        # 根据类名动态寻找 handle_ 方法
        handler_name = f"handle_{msg.__class__.__name__}"
        handler = getattr(self, handler_name, self.default_handler)
        handler(msg)

    def handle_HelloBackMsg(self, msg):
        logger.info(f"Server version: {msg.major}.{msg.minor}")
        self.client.on_handshake_complete()

    def default_handler(self, msg):
        logger.trace(f"Ignored message: {msg.CODE}")

```

---

## 4. 用户如何使用你的 Client？

这就是最终呈献给用户的 API 界面：

```python
from pydeskflow.client.connection import SynergyConnection
from pydeskflow.client.handlers import MessageDispatcher


class MySynergyClient:
    def __init__(self, host, port):
        self.conn = SynergyConnection(host, port)
        self.dispatcher = MessageDispatcher(self)
        self.is_ready = False

    def start(self):
        self.conn._connect()
        # 发送初始 Hello (握手第一步)
        # self.conn.send_msg(HelloMsg(...))

        logger.info("Client started, waiting for data...")
        try:
            while True:
                # 运行通信循环并获取消息
                for msg in self.conn.run_once():
                    self.dispatcher.dispatch(msg)
        except KeyboardInterrupt:
            logger.info("Stopping client...")

    def on_handshake_complete(self):
        self.is_ready = True
        logger.success("Synergy Link Established!")

```

---

## 5. 总结

1. **Protocol 包 **：是纯粹的计算层，提供 `Parser` 和 `MsgBase`。
2. **Connection 类 **：是 IO 层，管理 Socket 和字节流缓冲区。
3. **Dispatcher 类 **：是逻辑层，决定收到消息后“做什么”（比如操作 `pyautogui` 移动鼠标）。
4. ** 状态流转 **：建议在 `Client` 中通过一个简单的 `self.state` 变量来记录当前是 `CONNECTING`、
   `HANDSHAKING` 还是 `READY`。

** 你需要我为你补充如何结合 `pyautogui` 实现具体的鼠标控制
Handler，还是你想先完善握手阶段的状态切换逻辑？**
