from enum import Enum


class ClientState(Enum):
    """客户端状态枚举"""

    DISCONNECTED = 0
    CONNECTING = 1
    HANDSHAKE = 2
    CONNECTED = 3
    ACTIVE = 4
