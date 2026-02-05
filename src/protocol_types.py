"""
协议类型定义模块

定义 Deskflow 协议中使用的消息类型和类型别名。
"""

from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Deskflow 消息类型枚举"""

    DMMV = 'DMMV'
    DKDN = 'DKDN'
    DKUP = 'DKUP'
    DMDN = 'DMDN'
    DMUP = 'DMUP'
    DMRM = 'DMRM'
    DMWM = 'DMWM'
    DKRP = 'DKRP'
    DKDL = 'DKDL'

    Hello = 'Hello'
    HelloBack = 'HelloBack'

    QINF = 'QINF'
    CINN = 'CINN'
    COUT = 'COUT'
    CALV = 'CALV'
    CBYE = 'CBYE'
    CIAK = 'CIAK'
    DSOP = 'DSOP'
    CNOP = 'CNOP'

    DINF = 'DINF'
    DCLP = 'DCLP'
    DSEC = 'DSEC'
    LSYN = 'LSYN'
    DFTR = 'DFTR'
    DDRG = 'DDRG'

    EICV = 'EICV'
    EBSY = 'EBSY'
    EBAD = 'EBAD'
    EUNK = 'EUNK'


class ClientState(Enum):
    """客户端状态枚举"""

    DISCONNECTED = 0
    CONNECTING = 1
    HANDSHAKE = 2
    CONNECTED = 3
    ACTIVE = 4


ParsedMessage = tuple[MessageType, dict[str, Any]]
"""解析后的消息类型: (消息类型, 参数字典)"""
