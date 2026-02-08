import re
import struct
from dataclasses import dataclass
from typing import TypeVar

from src.protocol.protocol_types import MsgType

T = TypeVar('T', bound='MsgBase')


@dataclass(slots=True)
class MsgBase:
    """消息基类"""
    _INSTRUCTIONS = None
    _FORMAT = ''

    @classmethod
    def _compile_format(cls):
        # 匹配如 "H", "I", "10s", "Is" 等片段
        pattern = re.compile(r'(Is|[0-9]+s|[a-zA-Z])')
        parts = pattern.findall(cls._FORMAT.lstrip('>'))

        instructions = []
        for p in parts:
            if p == 'Is':
                instructions.append(('VAR_STR', 4))
            elif 's' in p:
                instructions.append(('FIX_STR', struct.calcsize(p), p))
            else:
                instructions.append(('FIX_VAL', struct.calcsize(p), p))
        cls._INSTRUCTIONS = instructions

    @classmethod
    def from_unpack(cls, data: bytes):
        if not cls._INSTRUCTIONS:
            cls._compile_format()

        offset = 0
        args = []
        for op, size, *meta in cls._INSTRUCTIONS:
            if op == 'FIX_VAL':
                args.append(struct.unpack_from(f">{meta[0]}", data, offset)[0])
                offset += size
            elif op == 'FIX_STR':
                raw = struct.unpack_from(f">{meta[0]}", data, offset)[0]
                args.append(raw.decode('utf-8'))
                offset += size
            elif op == 'VAR_STR':
                length = struct.unpack_from(">I", data, offset)[0]
                offset += 4
                args.append(data[offset:offset + length].decode('utf-8'))
                offset += length
        return cls(*args)


@dataclass(slots=True)
class HelloMsg(MsgBase):
    _FORMAT = '>7sHH'
    CODE = MsgType.Hello
    protocol_name: str
    major: int
    minor: int


@dataclass(slots=True)
class HelloBackMsg(MsgBase):
    _FORMAT = '>7sHHIs'
    CODE = MsgType.HelloBack
    protocol_name: str
    major: int
    minor: int
    name: str


@dataclass(slots=True)
class CClipboardMsg(MsgBase):
    """Clipboard grab notification

    Sent when an application grabs a clipboard on either screen.
    This notifies the other screen that clipboard ownership has changed.
    Secondary screens must use the sequence number from the most recent kMsgCEnter.
    The primary always sends sequence number 0.

    Attributes:
        identifier: Clipboard identifier (1 byte)
        sequence: Sequence number (4 bytes)
    """
    _FORMAT = '>BI'
    CODE = MsgType.CCLP
    identifier: int
    sequence: int


@dataclass(slots=True)
class CCloseMsg(MsgBase):
    """Close connection command

    Instructs the client to close the connection gracefully.
    The client should clean up resources and disconnect.
    """
    CODE = MsgType.CBYE


@dataclass(slots=True)
class CEnterMsg(MsgBase):
    """Enter screen command

    Sent when the mouse cursor enters the secondary screen from the primary.
    The coordinates specify the exact entry point. The sequence number is used
    to order messages and must be returned in subsequent messages from the client.
    The modifier mask indicates which toggle keys (Caps Lock, Num Lock, etc.) are
    active and should be synchronized on the secondary screen.

    Attributes:
        entry_x: Entry X coordinate (2 bytes, signed)
        entry_y: Entry Y coordinate (2 bytes, signed)
        sequence_number: Sequence number (4 bytes, unsigned)
        mod_key_mask: Modifier key mask (2 bytes, unsigned)
    """
    _FORMAT = '>HHIH'
    CODE = MsgType.CINN
    entry_x: int
    entry_y: int
    sequence_number: int
    mod_key_mask: int


@dataclass(slots=True)
class CInfoAckMsg(MsgBase):
    """Screen information acknowledgment

    Sent by the primary in response to a secondary screen's kMsgDInfo message.
    This acknowledgment is sent for every kMsgDInfo, whether the primary
    had previously sent a kMsgQInfo query.
    """
    CODE = MsgType.CIAK


@dataclass(slots=True)
class CKeepAliveMsg(MsgBase):
    """Keep-alive message

    Sent periodically by the server to verify that connections are still active.
    Clients must reply with the same message upon receipt.

    Timing:
        - Default interval: 3 seconds (configurable)
        - Timeout: 3 missed messages trigger disconnection

    Behavior:
        - Server sends keep-alive to client
        - Client immediately responds with keep-alive back to server
        - If server doesn't receive response within timeout, it disconnects client
        - If client doesn't receive keep-alives, it should disconnect from server
    """
    CODE = MsgType.CALV


@dataclass(slots=True)
class CLeaveMsg(MsgBase):
    """Leave screen command

    Sent when the mouse cursor leaves the secondary screen and returns to the primary.
    Upon receiving this message, the secondary screen should:
        1. Send clipboard data for any clipboards it has grabbed
        2. Only send clipboards that have changed since the last leave
        3. Use the sequence number from the most recent kMsgCEnter
    """
    CODE = MsgType.COUT


@dataclass(slots=True)
class CNoopMsg(MsgBase):
    """No operation command

    A no-operation message that can be used for testing connectivity or as a placeholder.
    Has no effect on the receiving end.
    """
    CODE = MsgType.CNOP


@dataclass(slots=True)
class CResetOptionsMsg(MsgBase):
    """Reset options command

    Instructs the client to reset all of its options to their default values.
    This is typically sent when the server configuration changes.
    """
    CODE = MsgType.CROP


@dataclass(slots=True)
class CScreenSaverMsg(MsgBase):
    """Screensaver state change

    Notifies the secondary screen when the primary's screensaver starts or stops.
    The secondary can use this to synchronize its own screensaver state.

    Attributes:
        state: Screensaver state (1 byte): 1 = started, 0 = stopped Examples:
    """
    _FORMAT = '>?'
    CODE = MsgType.CSEC
    state: bool


@dataclass(slots=True)
class DKeyDownMsg(MsgBase):
    """Key press event

    Key Mapping Strategy: The KeyButton parameter is crucial for proper key release handling.
    The secondary screen should:

        1. Map the KeyID to its local virtual key
        2. Remember the association between KeyButton and the local physical key
        3. Use KeyButton (not KeyID) to identify which key to release

    This is necessary because:

        - Dead keys can change the KeyID between press and release
        - Different keyboard layouts may produce different KeyIDs
        - Modifier keys released before the main key can alter KeyID

    Attributes:
        key_id: KeyID (2 bytes) - Virtual key identifier, often called a "keysym" on Linux/X11.
        This is platform-dependent and corresponds to values like XK_a on X11/Linux,
        'a' on macOS, and 'A' on Windows.
        mod_key_mask: KeyModifierMask (2 bytes) - Active modifier keys
        key_button: KeyButton (2 bytes) - Physical key code, often called a "keycode" or "scancode".
        This is the raw, platform-dependent scan code of the key pressed.
    """
    _FORMAT = '>HHH'
    CODE = MsgType.DKDN
    key_id: int
    mod_key_mask: int
    key_button: int


@dataclass(slots=True)
class DKeyDownLangMsg(MsgBase):
    """Key press with language code

    Enhanced version of kMsgDKeyDown that includes language information to help
    clients handle unknown language characters correctly.

    Attributes:
        key_id: KeyID (2 bytes) - Virtual key identifier, often called a "keysym" on Linux/X11.
        This is platform-dependent and corresponds to values like XK_a on X11/Linux,
        'a' on macOS, and 'A' on Windows.
        mod_key_mask: KeyModifierMask (2 bytes) - Active modifier keys
        key_button: KeyButton (2 bytes) - Physical key code, often called a "keycode" or "scancode".
        This is the raw, platform-dependent scan code of the key pressed.
        language_code: Language code (string) - Keyboard language identifier

    Examples:
        'a' key (KeyID 0x61), no modifiers, physical key (KeyButton 0x1E), English
        "DKDL\x00\x61\x00\x00\x00\x1E\x00\x00\x00\x02en"
    """
    _FORMAT = '>HHHIs'
    CODE = MsgType.DKDL
    key_id: int
    mod_key_mask: int
    key_button: int
    language_code: str


@dataclass(slots=True)
class DKeyRepeatMsg(MsgBase):
    """Key auto-repeat event

    Sent when a key is held down and auto-repeating. The repeat count indicates
    how many repeat events occurred since the last message.

    Attributes:
        key_id: KeyID (2 bytes) - Virtual key identifier, often called a "keysym" on Linux/X11.
        This is platform-dependent and corresponds to values like XK_a on X11/Linux,
        'a' on macOS, and 'A' on Windows.
        mod_key_mask: KeyModifierMask (2 bytes) - Active modifier keys
        repeat_count: Repeat count (2 bytes) - Number of repeats
        key_button: KeyButton (2 bytes) - Physical key code, often called a "keycode" or "scancode".
        This is the raw, platform-dependent scan code of the key pressed.
        language_code: Language code (string) - Keyboard language identifier

    Examples:
        'a' key repeating 3 times, English layout
        "DKRP\x00\x61\x00\x00\x00\x03\x00\x1E\x00\x00\x00\x02en"
    """
    _FORMAT = '>HHHIs'
    CODE = MsgType.DKRP
    key_id: int
    mod_key_mask: int
    repeat_count: int
    key_button: int
    language_code: str


@dataclass(slots=True)
class DKeyUpMsg(MsgBase):
    """Key release event

    Important:
        The secondary screen should use KeyButton (not KeyID) to
        determine which physical key to release. This ensures correct
        behavior with dead keys and layout differences.

    Attributes:
        key_id: KeyID (2 bytes) - Virtual key identifier, often called a "keysym" on Linux/X11.
        This is platform-dependent and corresponds to values like XK_a on X11/Linux,
        'a' on macOS, and 'A' on Windows.
        mod_key_mask: KeyModifierMask (2 bytes) - Active modifier keys
        key_button: KeyButton (2 bytes) - Physical key code, often called a "keycode" or "scancode".
        This is the raw, platform-dependent scan code of the key pressed.
    """
    _FORMAT = '>HHH'
    CODE = MsgType.DKUP
    key_id: int
    mod_key_mask: int
    key_button: int


@dataclass(slots=True)
class DMouseDownMsg(MsgBase):
    """Mouse press event

    Button IDs:
        1: Left button
        2: Right button
        3: Middle button
        4+: Additional buttons (side buttons, etc.)

    Attributes:
        button: ButtonID (1 byte) - Mouse button identifier
    """
    _FORMAT = '>B'
    CODE = MsgType.DMDN
    button: int


@dataclass(slots=True)
class DMouseMoveMsg(MsgBase):
    """Mouse move event

    Coordinates are absolute positions on the secondary screen.
    The origin (0,0) is typically the top-left corner.

    Attributes:
        x: X coordinate (2 bytes, signed) - Absolute screen position
        y: Y coordinate (2 bytes, signed) - Absolute screen position
    """
    _FORMAT = '>HH'
    CODE = MsgType.DMMV
    x: int
    y: int


@dataclass(slots=True)
class MouseRelMoveMsg(MsgBase):
    """Relative mouse movement

    Relative movement is useful for:
        - High-precision input devices
        - Gaming applications
        - When absolute positioning is not desired

    Attributes:
        x_delta: X delta (2 bytes, signed) - Horizontal movement
        y_delta: Y delta (2 bytes, signed) - Vertical movement
    """
    _FORMAT = '>HH'
    CODE = MsgType.DMRM
    x_delta: int
    y_delta: int


@dataclass(slots=True)
class DMouseUpMsg(MsgBase):
    """Mouse release event

    Button IDs are the same as for kMsgDMouseDown.

    Attributes:
        button: ButtonID (1 byte) - Mouse button identifier
    """
    _FORMAT = '>B'
    CODE = MsgType.DMUP
    button: int


@dataclass(slots=True)
class DMouseWheelMsg(MsgBase):
    """Mouse wheel scroll event

    Scroll Values:
        - +120: One tick forward (away from user) or right
        - -120: One tick backward (toward user) or left
        - Values are typically multiples of 120

    Directions:
        - Vertical: Positive = up/away, Negative = down/toward
        - Horizontal: Positive = right, Negative = left

    Attributes:
        x_delta: X delta (2 bytes, signed) - Horizontal scroll
        y_delta: Y delta (2 bytes, signed) - Vertical scroll
    """
    _FORMAT = '>HH'
    CODE = MsgType.DMWM
    x_delta: int
    y_delta: int


@dataclass(slots=True)
class DClipboardMsg(MsgBase):
    """Clipboard data transfer

    Clipboard Identifiers:
        - 0: Primary clipboard (Ctrl+C/Ctrl+V)
        - 1: Selection clipboard (middle-click on X11)

    Sequence Numbers:
        - Primary always sends sequence number 0
        - Secondary uses sequence number from most recent kMsgCEnter

    Streaming (v1.6+): For large clipboard data, the mark byte enables chunked transfer:
        - 0: Single chunk (complete data)
        - 1: First chunk of multi-chunk transfer
        - 2: Middle chunk
        - 3: Final chunk

    Attributes:
        identifier: Clipboard identifier (1 byte)
        sequence: Sequence number (4 bytes)
        flag: Mark/flags (1 byte) - For streaming support (v1.6+)
        data: Clipboard data (string)

    Examples:
        Primary clipboard, sequence 1, no flags, text "Hello World"
        "DCLP\x00\x00\x00\x00\x01\x00\x00\x00\x00\x0BHello World"
    """
    _FORMAT = '>BI?Is'
    CODE = MsgType.DCLP
    identifier: int
    sequence: int
    flag: bool
    data: str


@dataclass(slots=True)
class DInfoMsg(MsgBase):
    """Client screen information

    When to Send:
        1. In response to kMsgQInfo query
        2. When screen resolution changes
        3. During initial connection setup

    Resolution Change Protocol: When sending due to resolution change, the secondary should:
        1. Send kMsgDInfo with new dimensions
        2. Ignore kMsgDMouseMove until receiving kMsgCInfoAck
        3. This prevents mouse movement outside the new screen area

    Attributes:
        left_edge_coord: Left edge coordinate (2 bytes, signed)
        top_edge_coord: Top edge coordinate (2 bytes, signed)
        screen_width: Screen width in pixels (2 bytes, unsigned)
        screen_height: Screen height in pixels (2 bytes, unsigned)
        warp_zone: Warp zone size (2 bytes, obsolete)
        mouse_x: Mouse X position (2 bytes, signed)
        mouse_y: Mouse Y position (2 bytes, signed)

    Examples:
        Screen at (0,0), 1920x1080, mouse at (400,300)
        "DINF\x00\x00\x00\x00\x07\x80\x04\x38\x00\x00\x01\x90\x01\x2C"
    """
    _FORMAT = '>HHHHHHH'
    CODE = MsgType.DINF
    left_edge_coord: int
    top_edge_coord: int
    screen_width: int
    screen_height: int
    warp_zone: int  # obsolete
    mouse_x: int
    mouse_y: int


@dataclass(slots=True)
class DSetOptionsMsg(MsgBase):
    """Set client options

    Sets configuration options on the client. Options are sent as alternating
    option ID and value pairs. The client should apply these settings to modify
    its behavior.

    Attributes:
        options: Option/value pairs (4-byte integer list)

    Examples:
        2 pairs: option 1 = value 1, option 2 = value 0
        "DSOP\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x00"
    """
    _FORMAT = '>B'
    CODE = MsgType.DSOP
    options: dict[str, int]

    @classmethod
    def from_unpack(cls, data: bytes):
        ...


@dataclass(slots=True)
class DDragInfoMsg(MsgBase):
    """Drag and drop information

    Sent when a drag-and-drop operation begins. Contains the list of files being dragged.
    The actual file transfer follows using kMsgDFileTransfer messages.

    File Path Format:
        - Paths are null-terminated strings
        - Multiple paths are concatenated with null separators
        - Paths should use forward slashes for compatibility

    Attributes:
        file_counts: Number of files (2 bytes)
        file_paths: File paths (string) - Null-separated file paths

    Examples:
        Dragging 2 files
        "DDRG\x00\x02/path/to/file1.txt\x00/path/to/file2.txt\x00"
    """
    _FORMAT = '>HIs'
    CODE = MsgType.DDRG
    file_counts: int
    file_paths: list[str]

    @classmethod
    def from_unpack(cls, data: bytes):
        ...


@dataclass(slots=True)
class DFileTransferMsg(MsgBase):
    """File transfer data

    Transfer Marks:
        - 1 (kDataStart): Data contains file size (8 bytes)
        - 2 (kDataChunk): Data contains file content chunk
        - 3 (kDataEnd): Transfer complete (data may be empty)

    Protocol Flow:
        1. Sender initiates with kDataStart containing total file size
        2. Sender sends multiple kDataChunk messages with file content
        3. Sender concludes with kDataEnd to signal completion
        4. Receiver can abort by closing connection

    Attributes:
        mark: Transfer mark (1 byte) - Transfer state
        data: Data (string) - Content depends on mark

    Examples:
        Send 4096 bytes
        "DFTR\x01\x00\x00\x00\x00\x00\x00\x10\x00"
        "DFTR\x02[1024 bytes of file data]"
        "DFTR\x02[1024 bytes of file data]"
        "DFTR\x02[1024 bytes of file data]"
        "DFTR\x02[1024 bytes of file data]"
        "DFTR\x03"
    """
    _FORMAT = '>BI?Is'
    CODE = MsgType.DFTR
    mark: int
    data: str

    @classmethod
    def from_unpack(cls, data: bytes):
        ...


@dataclass(slots=True)
class DLanguageSynchronisationMsg(MsgBase):
    """Language synchronization

    Synchronizes keyboard language/layout information between primary and secondary screens. Helps ensure proper character mapping when different keyboard layouts are used.

    Language Format:
        - Comma-separated list of language codes
        - Uses standard ISO 639-1 language codes
        - Primary language listed first

    Attributes:
        lang_list: Language list (string) - Available server languages

    Examples:
        Server supports English, French, German, Spanish
        "LSYN\x00\x00\x00\x0Ben,fr,de,es"
    """
    _FORMAT = '>Is'
    CODE = MsgType.LSYN
    lang_list: list[str]


@dataclass(slots=True)
class DSecureInputNotificationMsg(MsgBase):
    """Secure input notification (macOS)

     Notifies the secondary screen when an application on the primary requests secure
     input mode.This is primarily a macOS feature where certain applications (like
     password fields) can request exclusive keyboard access.

     The secondary can use this information to:
        - Display security warnings to the user
        - Temporarily disable input forwarding
        - Show which application is requesting secure input

    Attributes:
        app_name: Application name (string) - App requesting secure input

    Examples:
        Terminal app is requesting secure input
        "SECN\x00\x00\x00\x08Terminal"
    """
    _FORMAT = '>Is'
    CODE = MsgType.SECN
    app_name: str


@dataclass(slots=True)
class QInfoMsg(MsgBase):
    """Query screen information

    Requests the secondary screen to send its current screen information.
    The client should respond with a kMsgDInfo message containing:
        - Screen dimensions and position
        - Current mouse position
        - Other screen-related data

    This is typically sent:
        - During initial connection setup
        - When the server needs updated screen information
        - After configuration changes
    """
    CODE = MsgType.QINF


@dataclass(slots=True)
class EBadMsg(MsgBase):
    """Protocol violation

    Sent when the client violates the protocol in some way. This can include:
        - Sending malformed messages
        - Sending messages in wrong order
        - Sending unexpected message types
        - Exceeding protocol limits

    After sending this message, the server will immediately disconnect the client.
    This indicates a serious protocol error that cannot be recovered from.

    Common Causes:
        - Implementation bugs in client
        - Corrupted network data
        - Version mismatch not caught earlier
        - Malicious or broken client
    """
    CODE = MsgType.EBAD


@dataclass(slots=True)
class EBusyMsg(MsgBase):
    """Client name already in use

    Sent when the client name provided during connection is already in use by another connected client. Client names must be unique within a Deskflow network.

    After receiving this message, the client should:
        1. Disconnect from the server
        2. Inform the user of the name conflict
        3. Allow the user to choose a different name
        4. Retry connection with the new name
    """
    CODE = MsgType.EBSY


@dataclass(slots=True)
class EIncompatibleMsg(MsgBase):
    """Incompatible protocol versions

    Sent when the client and server have incompatible protocol versions.
    This typically occurs when:
        - Major versions differ (fundamental incompatibility)
        - Server requires newer features than client supports

    After sending this message, the server will disconnect the client.
    The client should display an appropriate error message to the user.

    Attributes:
        major: Primary major version (2 bytes)
        minor: Primary minor version (2 bytes)
    """
    _FORMAT = '>HH'
    CODE = MsgType.EICV
    major: int
    minor: int


@dataclass(slots=True)
class EUnknownMsg(MsgBase):
    """Unknown client name

    Sent when the client name provided during connection is not found in the server's screen configuration map. This means the server doesn't know about this client.

    This can happen when:
        - Client name is misspelled
        - Server configuration doesn't include this client
        - Client is connecting to wrong server

    The client should inform the user and check:
        - Client name spelling
        - Server configuration
        - Network connectivity to correct server
    """
    CODE = MsgType.EUNK
