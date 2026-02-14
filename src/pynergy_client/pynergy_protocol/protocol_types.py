"""
协议类型定义模块

定义 Deskflow 协议中使用的消息类型和类型别名。
"""

from enum import Enum


class MsgID(str, Enum):
    """Deskflow message type enum"""

    # --- handshake ---
    Hello = 'Hello'
    HelloBack = 'HelloBack'

    # --- command ---
    CCLP = 'CCLP'
    """Clipboard grab notification"""
    CBYE = 'CBYE'
    """Close connection command"""
    CINN = 'CINN'
    """Enter screen command"""
    CIAK = 'CIAK'
    """Screen information acknowledgment"""
    CALV = 'CALV'
    """Keep-alive message"""
    COUT = 'COUT'
    """Leave screen command"""
    CNOP = 'CNOP'
    """No operation command"""
    CROP = 'CROP'
    """Reset options command"""
    CSEC = 'CSEC'
    """Screensaver state change"""

    # --- data ---
    DKDN = 'DKDN'
    """Key press event"""
    DKDL = 'DKDL'
    """Key press with language code"""
    DKRP = 'DKRP'
    """Key auto-repeat event"""
    DKUP = 'DKUP'
    """Key release event"""
    DMDN = 'DMDN'
    """Mouse press event"""
    DMMV = 'DMMV'
    """Mouse move event"""
    DMRM = 'DMRM'
    """Relative mouse movement"""
    DMUP = 'DMUP'
    """Mouse release event"""
    DMWM = 'DMWM'
    """Mouse wheel scroll event"""
    DCLP = 'DCLP'
    """Clipboard data transfer"""
    DINF = 'DINF'
    """Client screen information"""
    DSOP = 'DSOP'
    """Set client options"""
    DDRG = 'DDRG'
    """Drag and drop information"""
    DFTR = 'DFTR'
    """File transfer data"""
    LSYN = 'LSYN'
    """Language synchronization"""
    SECN = 'SECN'
    """Secure input notification (macOS)"""

    # --- query ---
    QINF = 'QINF'
    """Query screen information"""

    # --- error ---
    EBAD = 'EBAD'
    """Protocol violation"""
    EBSY = 'EBSY'
    """Client name already in use"""
    EICV = 'EICV'
    """Incompatible pynergy_protocol versions"""
    EUNK = 'EUNK'
    """Unknown client name"""


class ModifierKeyMask(int, Enum):
    """Modifier key mask"""

    Shift = 0x0001
    Control = 0x0002
    Alt = 0x0004
    Meta = 0x0008
    Super = 0x0010
    AltGr = 0x0020
    Level5Lock = 0x0040
    CapsLock = 0x1000
    NumLock = 0x2000
    ScrollLock = 0x4000
