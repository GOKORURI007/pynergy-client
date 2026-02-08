import struct
from dataclasses import dataclass, fields
from typing import Annotated, Literal, TypeAlias, get_args, get_origin, get_type_hints

from loguru import logger

from src.protocol.protocol_types import MsgID

OpCode: TypeAlias = Literal['FIX_VAL', 'FIX_STR', 'VAR_STR']
InstructionType: TypeAlias = list[tuple[OpCode, int, str]]


@dataclass(slots=True)
class MsgBase:
    """消息基类"""

    _INSTRUCTIONS = None
    _FORMAT = ''
    CODE = ''

    def __init_subclass__(cls, **kwargs):
        # 防止 dataclass(slots=True) 重建类时重复执行
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

                # 判定操作类型
                op: OpCode
                if struct_char == 'Is':
                    op = 'VAR_STR'
                    size = 4  # 仅长度前缀的大小
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

        cls._FORMAT = ''.join(fmt_parts)
        cls._INSTRUCTIONS = instructions
        cls._format_initialized = True

    @classmethod
    def unpack(cls, data: bytes):
        logger.debug(f'开始解包 {cls.__name__}: 数据长度={len(data)} 字节')

        try:
            offset = 0
            args = []

            for i, (op, size, fmt) in enumerate(cls._INSTRUCTIONS):
                if offset >= len(data):
                    raise ValueError(f'数据不足：在指令 {i} ({op}) 处超出范围')

                try:
                    if op == 'FIX_VAL':
                        # 直接解包数值
                        val = struct.unpack_from(f'>{fmt}', data, offset)[0]
                        args.append(val)
                        offset += size
                        logger.debug(f'解包固定值: 格式={fmt}, 值={val}, 新偏移={offset}')

                    elif op == 'FIX_STR':
                        # 解包固定长度字符串并 strip
                        raw_val = struct.unpack_from(f'>{fmt}', data, offset)[0]
                        val = raw_val.decode('utf-8').rstrip('\x00')
                        args.append(val)
                        offset += size
                        logger.debug(f"解包固定字符串: 格式={fmt}, 值='{val}', 新偏移={offset}")

                    elif op == 'VAR_STR':
                        # 解包变长字符串：先读 4 字节长度
                        if offset + 4 > len(data):
                            raise ValueError('变长字符串长度信息不完整')

                        length = struct.unpack_from('>I', data, offset)[0]
                        offset += size

                        if offset + length > len(data):
                            raise ValueError(
                                f'变长字符串数据不完整：声明长度={length}, 可用数据={len(data) - offset}'
                            )

                        val = data[offset: offset + length].decode('utf-8')
                        args.append(val)
                        offset += length
                        logger.debug(f"解包变长字符串: 长度={length}, 值='{val}', 新偏移={offset}")

                except UnicodeDecodeError as e:
                    raise ValueError(f'UTF-8 解码失败在指令 {i} ({op}): {e}') from e
                except struct.error as e:
                    raise ValueError(f"结构体解包失败在指令 {i} ({op}), 格式='{fmt}': {e}") from e

            if offset < len(data):
                logger.warning(f'解包后剩余 {len(data) - offset} 字节未处理的数据')

            result = cls(*args)  # type: ignore[call-arg]
            logger.debug(f'成功解包 {cls.__name__}: {result}')
            return result

        except Exception as e:
            logger.error(f'解包 {cls.__name__} 失败: {e}', exc_info=True)
            raise

    def pack(self) -> bytes:
        """根据类定义的字段顺序和 _INSTRUCTIONS 动态打包"""
        logger.debug(f'开始打包 {self.__class__.__name__}: {self}')

        try:
            result = bytearray()

            try:
                code_bytes = struct.pack(f'>{len(self.CODE)}s', self.CODE.encode('utf-8'))
                result.extend(code_bytes)
                logger.debug(f"打包消息代码: '{self.CODE}', 长度={len(code_bytes)}")
            except struct.error as e:
                raise ValueError(f"打包消息代码 '{self.CODE}' 失败: {e}") from e

            # 获取 dataclass 定义的所有字段的值 (按定义顺序)
            data_fields = [
                f for f in fields(self) if not f.name.startswith('_') and f.name != 'CODE'
            ]

            if len(data_fields) != len(self._INSTRUCTIONS):
                raise ValueError(
                    f'字段数量 ({len(data_fields)}) 与指令数量 ({len(self._INSTRUCTIONS)}) 不匹配'
                )

            # 将指令与字段值一一对应进行处理
            for i, ((op, size, fmt), field_def) in enumerate(zip(self._INSTRUCTIONS, data_fields)):
                try:
                    val = getattr(self, field_def.name)
                    logger.debug(f'处理字段 {field_def.name}: 值={val}, 操作={op}, 格式={fmt}')

                    if op == 'FIX_VAL':
                        # 处理数值 (I, H, B 等)
                        packed_val = struct.pack(f'>{fmt}', val)
                        result.extend(packed_val)
                        logger.debug(f'打包固定值: {val} -> {packed_val.hex()}')

                    elif op == 'FIX_STR':
                        # 处理固定长度字符串，确保编码为 bytes 并填充 / 截断
                        try:
                            s_bytes = val.encode('utf-8')
                            # struct.pack 会自动根据 fmt ( 如 "7s") 处理截断和补 \x00
                            packed_str = struct.pack(f'>{fmt}', s_bytes)
                            result.extend(packed_str)
                            logger.debug(f"打包固定字符串: '{val}' -> {packed_str.hex()}")
                        except UnicodeEncodeError as e:
                            raise ValueError(f'编码字符串字段 {field_def.name} 失败: {e}') from e

                    elif op == 'VAR_STR':
                        # 处理变长字符串 (Synergy 风格: Length + Data)
                        try:
                            s_bytes = val.encode('utf-8')
                            length = len(s_bytes)
                            # 先打入 4 字节长度，再打入实际内容
                            length_bytes = struct.pack('>I', length)
                            result.extend(length_bytes)
                            result.extend(s_bytes)
                            logger.debug(
                                f"打包变长字符串: '{val}' (长度={length}) -> {length_bytes.hex()}{s_bytes.hex()}"
                            )
                        except UnicodeEncodeError as e:
                            raise ValueError(
                                f'编码变长字符串字段 {field_def.name} 失败: {e}'
                            ) from e

                except struct.error as e:
                    raise ValueError(
                        f"打包字段 {field_def.name} (指令 {i}) 失败，格式='{fmt}': {e}"
                    ) from e
                except Exception as e:
                    logger.error(f'打包字段 {field_def.name} 时发生错误: {e}', exc_info=True)
                    raise

            final_result = bytes(result)
            logger.debug(f'成功打包 {self.__class__.__name__}: 总长度={len(final_result)} 字节')
            return final_result

        except Exception as e:
            logger.error(f'打包 {self.__class__.__name__} 失败: {e}', exc_info=True)
            raise


class Registry:
    _MAPPING: dict[MsgID, MsgBase] = {}

    @classmethod
    def register(cls, msg_code: MsgID):
        def wrapper(subclass):
            if not issubclass(subclass, MsgBase):
                raise TypeError(f'注册的类 {subclass.__name__} 必须继承自 MsgBase')

            if msg_code in cls._MAPPING:
                logger.warning(f'消息类型 {msg_code} 已被注册，将被覆盖')

            cls._MAPPING[msg_code] = subclass
            subclass.CODE = msg_code
            logger.trace(f'注册消息类型: {msg_code} -> {subclass.__name__}')
            return subclass

        return wrapper

    @classmethod
    def get_class(cls, msg_code: MsgID) -> MsgBase:
        if msg_code not in cls._MAPPING:
            logger.warning(f'未找到消息类型: {msg_code}')
            raise KeyError(f'未注册的消息类型: {msg_code}')

        result = cls._MAPPING[msg_code]
        logger.trace(f'获取消息类: {msg_code} -> {result.__name__}')
        return result

    @classmethod
    def get_registered_types(cls) -> list[MsgID]:
        """返回所有已注册的消息类型"""
        return list(cls._MAPPING.keys())

    @classmethod
    def is_registered(cls, msg_code: MsgID) -> bool:
        """检查消息类型是否已注册"""
        return msg_code in cls._MAPPING
