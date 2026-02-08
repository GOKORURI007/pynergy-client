既然你是在构建一个供他人调用的 **Protocol Package**，那么最 Pythonic 的做法是保持 **“无状态（Stateless）”
**。你的库只负责解析和构建字节流，而不干涉用户的 Socket 连接。

以下是一个标准的协议库框架建议，你可以将其命名为 `synergy_proto`。

---

## 1. 文件组织结构

这种结构清晰地分离了消息定义、核心逻辑和辅助工具。

```text
synergy_proto/
├── __init__.py           # 暴露核心类：Parser, MsgBase, Registry
├── core.py               # 基础定义：MsgBase, Registry 装饰器
├── messages.py           # 具体的消息实现 (HelloMsg, KeyMsg 等)
├── parser.py             # 粘包处理与解析逻辑
└── exceptions.py         # 协议相关的异常定义 (ProtocolError)

```

---

## 2. 核心代码定义

### core.py (基础骨架)

利用 `__init_subclass__` 实现自动注册，不需要手动维护映射表。

```python
import struct
from dataclasses import dataclass
from typing import Dict, Type


class Registry:
    _MAPPING: Dict[int, Type['MsgBase']] = {}

    @classmethod
    def register(cls, msg_code: int):
        def wrapper(subclass):
            cls._MAPPING[msg_code] = subclass
            subclass.CODE = msg_code
            return subclass

        return wrapper

    @classmethod
    def get_class(cls, msg_code: int) -> Type['MsgBase']:
        return cls._MAPPING.get(msg_code)


@dataclass(slots=True)
class MsgBase:
    CODE: int = 0

    def pack(self) -> bytes:
        """用户需要实现：对象 -> bytes"""
        raise NotImplementedError

    @classmethod
    def from_unpack(cls, data: bytes):
        """用户已经实现的：bytes -> 对象"""
        raise NotImplementedError

```

### messages.py (具体消息)

这里存放你所有的 `dataclass`。

```python
from .core import MsgBase, Registry


@Registry.register(0x0001)
@dataclass(slots=True)
class HelloMsg(MsgBase):
    protocol_name: str
    major: int
    minor: int

    def pack(self) -> bytes:
        # 实现你的打包逻辑
        name_bytes = self.protocol_name.encode('utf-8')
        return struct.pack(f">I{len(name_bytes)}sHH", len(name_bytes), name_bytes, self.major,
                           self.minor)

```

### parser.py (流解析器)

这是给用户的核心工具，处理 TCP 粘包。

```python
from .core import Registry


class SynergyParser:
    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes):
        """存入收到的原始字节"""
        self._buffer.extend(data)

    def next_msg(self):
        """
        尝试解析并返回一个消息对象。
        采用生成器风格或循环调用。
        """
        if len(self._buffer) < 4:
            return None

        # 1. 读取长度 (假设前4字节)
        length = struct.unpack_from(">I", self._buffer)[0]
        if len(self._buffer) < length + 4:
            return None

        # 2. 提取数据包
        packet = self._buffer[4:4 + length]
        msg_code = struct.unpack_from(">I", packet)[0]  # 假设 packet 前4字节是 CODE

        # 3. 查找并转换
        cls = Registry.get_class(msg_code)
        if cls:
            msg_obj = cls.from_unpack(packet[4:])
            del self._buffer[:4 + length]  # 消费掉已读数据
            return msg_obj

        # 如果是未知消息，跳过防止死循环
        del self._buffer[:4 + length]
        return None

```

---

## 3. 用户调用示例

用户可以自由地在同步或异步环境中使用你的库。

### 场景 A：同步 Socket 调用 (简单直观)

```python
import socket
from synergy_proto import SynergyParser, HelloMsg


def run_client():
    sock = socket.socket()
    sock.connect(('127.0.0.1', 24800))
    parser = SynergyParser()

    while True:
        data = sock.recv(4096)
        if not data: break

        parser.feed(data)
        while True:
            msg = parser.next_msg()
            if not msg: break

            # 处理消息逻辑
            if isinstance(msg, HelloMsg):
                print(f"Connected to {msg.protocol_name}")

```

### 场景 B：构建并发送消息

```python
from synergy_proto import HelloMsg


def send_hello(sock):
    msg = HelloMsg(protocol_name="Synergy", major=1, minor=6)
    # 这里的 pack() 包含了协议头长度封装
    payload = msg.pack()
    header = struct.pack(">I", len(payload))
    sock.sendall(header + payload)

```

---

## 4. 为什么这样组织？

1. **高内聚**：`messages.py` 就像一份动态说明书，你可以直接用 **MkDocs** 扫描这个文件生成 API 文档。
2. **低耦合**：`SynergyParser` 不关心数据是怎么来的（Socket, Serial, 甚至是本地文件读取），它只负责逻辑运算。
3. **易扩展**：用户如果要自定义一个私有消息，只需要在自己的代码里写个 `dataclass` 并加上
   `@Registry.register(ID)`，你的 `Parser` 就能自动识别它。

**这样一套结构是否符合你的项目预期？如果需要，我可以为你补充 `exceptions.py` 的定义逻辑。**
