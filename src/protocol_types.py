"""
协议类型定义模块

定义 Synergy 协议中使用的消息类型和类型别名。
"""

from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Synergy 消息类型枚举"""

    DMMV = 'DMMV'
    DKDN = 'DKDN'
    DKUP = 'DKUP'
    DMDN = 'DMDN'
    DMUP = 'DMUP'


ParsedMessage = tuple[MessageType, dict[str, Any]]
"""解析后的消息类型: (消息类型, 参数字典)"""
