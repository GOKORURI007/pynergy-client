import struct
from dataclasses import dataclass, fields
from types import NoneType
from typing import (
    Annotated,
    ClassVar,
    Literal,
    Self,
    TypeAlias,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

from loguru import logger

from .protocol_types import MsgID

OpCode: TypeAlias = Literal['FIX_VAL', 'FIX_STR', 'VAR_STR']
InstructionType: TypeAlias = list[tuple[OpCode, int, str]]
T = TypeVar('T', bound='MsgBase')


@dataclass(slots=True)
class MsgBase[T]:
    """Message base class"""

    _INSTRUCTIONS: ClassVar[InstructionType | NoneType] = None
    _FORMAT: ClassVar[str] = ''
    CODE: ClassVar[str] = ''

    def __init_subclass__(cls: T, **kwargs):
        # Prevent dataclass(slots=True) from repeatedly executing when rebuilding a class
        if '_format_initialized' in cls.__dict__:
            return
        # --- compile format ---
        hints = get_type_hints(cls, include_extras=True)

        fmt_parts: list[str] = ['>']
        instructions: InstructionType = []
        for field_name, hint in hints.items():
            if field_name.startswith('_') or field_name == 'CODE':
                continue

            if get_origin(hint) is Annotated:
                metadata = get_args(hint)
                struct_char = metadata[1]

                # Determine the type of operation
                op: OpCode
                if struct_char == 'Is':
                    op = 'VAR_STR'
                    size = 4  # Size of the length prefix only
                elif 's' in struct_char:
                    op = 'FIX_STR'
                    size = struct.calcsize(struct_char)
                else:
                    op = 'FIX_VAL'
                    size = struct.calcsize(struct_char)

                fmt_parts.append(struct_char)
                instructions.append((op, size, struct_char))

            else:
                raise TypeError(
                    f'Field {field_name} must be annotated with Annotated (such as Int32, UInt16). '
                    f'Got {type(hint)} instead.'
                )

        setattr(cls, '_FORMAT', ''.join(fmt_parts))
        setattr(cls, '_INSTRUCTIONS', instructions)
        setattr(cls, '_format_initialized', True)

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        try:
            logger.opt(lazy=True).trace(
                '{log}', log=lambda: f'Unpacking {cls.__name__}: data length={len(data)} bytes'
            )
            data = cls.before_unpack(data)
            offset = 0
            args = []

            if cls._INSTRUCTIONS is None:
                raise ValueError(f'Instruction set not initialized: {cls.__name__}')

            for i, (op, size, fmt) in enumerate(cls._INSTRUCTIONS):
                if offset >= len(data):
                    raise ValueError(f'Insufficient data: Out of range at directive {i} ({op}).')

                try:
                    if op == 'FIX_VAL':
                        # Unpack the value directly
                        val = struct.unpack_from(f'>{fmt}', data, offset)[0]
                        args.append(val)
                        offset += size
                        logger.opt(lazy=True).trace(
                            '{log}',
                            log=lambda: (
                                f'Unpack fixed values: format={fmt}, value={val}, new offset={offset}'
                            ),
                        )

                    elif op == 'FIX_STR':
                        # Unwrap fixed-length strings and strip
                        raw_val = struct.unpack_from(f'>{fmt}', data, offset)[0]
                        val = raw_val.decode().rstrip('\x00')
                        args.append(val)
                        offset += size
                        logger.opt(lazy=True).trace(
                            '{log}',
                            log=lambda: (
                                f'Unpack fixed string: format={fmt}, value={val}, new offset={offset}'
                            ),
                        )

                    elif op == 'VAR_STR':
                        # Unpack a lengthened string: Read 4 bytes of length first
                        if offset + 4 > len(data):
                            raise ValueError('The length of the variable string is incomplete')

                        length = struct.unpack_from('>I', data, offset)[0]
                        offset += size

                        if offset + length > len(data):
                            raise ValueError(
                                f'Variable length string data is incomplete: '
                                f'declared length={length}, available data={len(data) - offset}'
                            )

                        val = data[offset : offset + length].decode()
                        args.append(val)
                        offset += length
                        logger.opt(lazy=True).debug(
                            '{log}',
                            log=lambda: (
                                f'Unpack Lengthy String: '
                                f'length={length}, value={val}, new offset={offset}'
                            ),
                        )

                except UnicodeDecodeError as e:
                    raise ValueError(f'UTF-8 decoding fails in directive {i} ({op}): {e}') from e
                except struct.error as e:
                    raise ValueError(
                        f'Struct unpacking fails in directive {i} ({op}), format={fmt}: {e}'
                    ) from e

            if offset < len(data):
                logger.opt(lazy=True).warning(
                    '{log}',
                    log=lambda: (
                        f'{len(data) - offset} bytes of unprocessed data remaining after unpacking'
                    ),
                )

            result = cls(*args)  # type: ignore[call-arg]
            result = cls.after_unpack(result)
            logger.opt(lazy=True).trace(
                '{log}', log=lambda: f'Successful unpacking {cls.__name__}: {result}'
            )
            return result

        except Exception:
            logger.opt(lazy=True).error(
                '{log}',
                log=lambda: f'Unpacking {cls.__name__} failed: {e}',
            )
            raise

    def pack(self) -> bytes:
        """
        Dynamically Pack based on the order of fields defined by the class and _INSTRUCTIONS
        """
        try:
            logger.opt(lazy=True).trace('{log}', log=lambda: f'Start packing {self}')
            self.before_pack()
            result = bytearray()

            code_bytes = struct.pack(f'>{len(self.CODE)}s', self.CODE.encode('utf-8'))
            result.extend(code_bytes)
            logger.opt(lazy=True).trace(
                '{log}', log=lambda: f'Pack message code: {self.CODE}, length={len(code_bytes)}'
            )

            # Get the values of all fields defined by the dataclass (in order of definition)
            data_fields = [
                f for f in fields(self) if not f.name.startswith('_') and f.name != 'CODE'
            ]

            if self._INSTRUCTIONS is None:
                raise ValueError('Instruction list undefined')

            if len(data_fields) != len(self._INSTRUCTIONS):
                raise ValueError(
                    f'The number of fields ({len(data_fields)}) does not match '
                    f'the number of instructions ({len(self._INSTRUCTIONS)}).'
                )

            # Process the instructions and field values one by one
            for i, ((op, size, fmt), field_def) in enumerate(zip(self._INSTRUCTIONS, data_fields)):
                try:
                    val = getattr(self, field_def.name)
                    logger.opt(lazy=True).trace(
                        '{log}',
                        log=lambda: (
                            f'Process field {field_def.name}: value={val}, operation={op}, format={fmt}'
                        ),
                    )

                    if op == 'FIX_VAL':
                        # Processing values (I, H, B, etc.)
                        packed_val = struct.pack(f'>{fmt}', val)
                        result.extend(packed_val)
                        logger.opt(lazy=True).trace(
                            '{log}', log=lambda: f'Packing fixed value: {val} -> {packed_val.hex()}'
                        )

                    elif op == 'FIX_STR':
                        # Handle fixed-length strings, ensuring they are encoded as
                        # bytes and pfilled/truncated
                        try:
                            s_bytes = val.encode('utf-8')
                            # struct.pack automatically handles truncation and
                            # completion \x00 based on FMT (e.g. "7s").
                            packed_str = struct.pack(f'>{fmt}', s_bytes)
                            result.extend(packed_str)
                            logger.opt(lazy=True).trace(
                                '{log}',
                                log=lambda: f"打包固定字符串: '{val}' -> {packed_str.hex()}",
                            )
                        except UnicodeEncodeError as e:
                            raise ValueError(f'编码字符串字段 {field_def.name} 失败: {e}') from e

                    elif op == 'VAR_STR':
                        # Handling Variable Strings (Synergy Style: Length + Data)
                        try:
                            s_bytes = val.encode('utf-8')
                            length = len(s_bytes)
                            # Punch in 4 bytes before punching in the actual content
                            length_bytes = struct.pack('>I', length)
                            result.extend(length_bytes)
                            result.extend(s_bytes)
                            logger.trace(
                                '{log}',
                                log=lambda: (
                                    f'Packing Long String: {val} '
                                    f'(length={length}) -> {length_bytes.hex()}{s_bytes.hex()}'
                                ),
                            )
                        except UnicodeEncodeError as e:
                            raise ValueError(
                                f'Encoding a variable string field {field_def.name} fails: {e}'
                            ) from e

                except struct.error as e:
                    raise ValueError(
                        f'Packing field {field_def.name} (directive {i}) '
                        f'failed with format={fmt}: {e}'
                    ) from e
                except Exception:
                    logger.opt(lazy=True).error(
                        '{log}',
                        log=lambda: f'Error with packaging field {field_def.name}: {e}',
                    )
                    raise

            final_result = bytes(result)
            final_result = self.after_pack(final_result)
            logger.opt(lazy=True).trace(
                '{log}',
                log=lambda: (
                    f'Successfully packed {self.__class__.__name__}: '
                    f'total length={len(final_result)} bytes'
                ),
            )
            return final_result

        except Exception:
            logger.opt(lazy=True).error(
                '{log}',
                log=lambda: f'Pack {self.__class__.__name__} failed: {e}',
            )
            raise

    def pack_for_socket(self) -> bytes:
        """
        Append a 4-byte length prefix (Big-endian) before the message body
        """
        payload = self.pack()
        return struct.pack('>I', len(payload)) + payload

    @staticmethod
    def before_unpack(data: bytes) -> bytes:
        """Execute before unpacking"""
        return data[4:]

    @classmethod
    def after_unpack(cls, result: Self) -> Self:
        """Executed after unpacking"""
        return result

    def before_pack(self):
        """Execute before packing"""
        pass

    @staticmethod
    def after_pack(result: bytes) -> bytes:
        """Executed after packing"""
        return result


class Registry:
    _MAPPING: dict[MsgID, type['MsgBase']] = {}

    @classmethod
    def register(cls, msg_code: MsgID):
        def wrapper(subclass):
            if not issubclass(subclass, MsgBase):
                raise TypeError(
                    f'The registered class {subclass.__name__} must inherit from MsgBase'
                )

            if msg_code in cls._MAPPING:
                logger.opt(lazy=True).warning(
                    '{log}',
                    log=lambda: (
                        f'The message type {msg_code} is registered and will be overwritten'
                    ),
                )

            cls._MAPPING[msg_code] = subclass
            subclass.CODE = msg_code
            logger.opt(lazy=True).trace(
                '{log}', log=lambda: f'Registration message type: {msg_code} -> {subclass.__name__}'
            )
            return subclass

        return wrapper

    @classmethod
    def get_class(cls, msg_code: MsgID) -> type[MsgBase]:
        if msg_code not in cls._MAPPING:
            logger.opt(lazy=True).warning('{log}', log=lambda: f'Message Not Found: {msg_code}')
            raise KeyError(f'Unregistered message type: {msg_code}')

        result = cls._MAPPING[msg_code]
        logger.opt(lazy=True).trace(
            '{log}', log=lambda: f'Get message class: {msg_code} -> {result.__name__}'
        )
        return result

    @classmethod
    def get_registered_types(cls) -> list[MsgID]:
        """Returns all registered message types"""
        return list(cls._MAPPING.keys())

    @classmethod
    def is_registered(cls, msg_code: MsgID) -> bool:
        """Check if the message type is registered"""
        return msg_code in cls._MAPPING
