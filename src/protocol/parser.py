import struct
from typing import Literal

from loguru import logger

from .core import MsgBase, Registry
from .protocol_types import MsgID


class SynergyParser:
    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes):
        """存入收到的原始字节"""
        if not data:
            return
        logger.trace(f'Fed {len(data)} bytes into buffer')
        self._buffer.extend(data)

    def next_msg(self) -> MsgBase | None:
        """
        尝试解析并返回一个消息对象。
        """
        # 基础长度检查（前 4 字节为包长度）
        msg_code_raw = 'unknown'
        total_packet_size = 0
        if len(self._buffer) < 4:
            return None

        try:
            # 1. 读取长度前缀
            # 使用 unpack_from 的好处是不需要切片，性能更好
            length = struct.unpack_from('>I', self._buffer)[0]

            # 协议安全检查：防止恶意超大包导致 OOM
            if length > 10 * 1024 * 1024:  # 假设最大包 10MB
                logger.error(f'Invalid packet length: {length}, clearing buffer')
                self._buffer.clear()
                return None

            # 检查缓冲区数据是否足够
            total_packet_size = 4 + length
            if len(self._buffer) < total_packet_size:
                logger.trace(f'Wait for more data: {len(self._buffer)}/{total_packet_size}')
                return None

            # 2. 提取数据包（跳过前 4 字节长度）
            packet = self._buffer[4:total_packet_size]

            # 这里的异常处理保护了接下来可能出错的解析逻辑
            try:
                # 假设 packet 前 4 字节是 CODE
                msg_code_raw = struct.unpack_from('>4s', packet)[0]

                # 3. 查找对应的消息类
                cls = Registry.get_class(msg_code_raw)

                if not cls:
                    logger.warning(
                        f'Unknown message code: {msg_code_raw}, size: {length}. Skipping.'
                    )
                    return None

                # 4. 执行反序列化
                # 这里假设你的类方法名为 unpack (根据你之前的代码)
                msg_obj = cls.unpack(packet)
                logger.debug(f'Successfully parsed message: {msg_code_raw}')
                return msg_obj

            except (struct.error, UnicodeDecodeError, ValueError) as e:
                logger.error(f'Failed to unpack message body (CODE: {msg_code_raw}): {e}')
                return None

            except Exception as e:
                logger.exception(f'Unexpected error during message construction: {e}')
                return None

        finally:
            # 核心原则：无论解析成功与否，只要长度足够，就必须消费掉这段数据
            # 除非你希望保留损坏的数据尝试重新解析（通常不建议）
            if len(self._buffer) >= total_packet_size:
                del self._buffer[:total_packet_size]

    def next_handshake_msg(self, msg_type: Literal[MsgID.Hello, MsgID.HelloBack]) -> MsgBase | None:
        """
        尝试解析并返回一个 Handshake 消息对象。
        """
        # 基础长度检查（前 4 字节为包长度）
        msg_code_raw = 'unknown'
        total_packet_size = 0
        if len(self._buffer) < 4:
            return None

        try:
            # 1. 读取长度前缀
            # 使用 unpack_from 的好处是不需要切片，性能更好
            length = struct.unpack_from('>I', self._buffer)[0]

            # 协议安全检查：防止恶意超大包导致 OOM
            if length > 10 * 1024 * 1024:  # 假设最大包 10MB
                logger.error(f'Invalid packet length: {length}, clearing buffer')
                self._buffer.clear()
                return None

            # 检查缓冲区数据是否足够
            total_packet_size = 4 + length
            if len(self._buffer) < total_packet_size:
                logger.trace(f'Wait for more data: {len(self._buffer)}/{total_packet_size}')
                return None

            # 2. 提取数据包（跳过前 4 字节长度）
            packet = self._buffer[4:total_packet_size]

            # 这里的异常处理保护了接下来可能出错的解析逻辑
            try:
                # 3. 查找对应的消息类
                cls = Registry.get_class(msg_type)

                if not cls:
                    logger.warning(
                        f'Unknown message code: {msg_code_raw}, size: {length}. Skipping.'
                    )
                    return None

                # 4. 执行反序列化
                # 这里假设你的类方法名为 unpack (根据你之前的代码)
                msg_obj = cls.unpack(packet)
                logger.debug(f'Successfully parsed message: {msg_code_raw}')
                return msg_obj

            except (struct.error, UnicodeDecodeError, ValueError) as e:
                logger.error(f'Failed to unpack message body (CODE: {msg_code_raw}): {e}')
                return None

            except Exception as e:
                logger.exception(f'Unexpected error during message construction: {e}')
                return None

        finally:
            # 核心原则：无论解析成功与否，只要长度足够，就必须消费掉这段数据
            # 除非你希望保留损坏的数据尝试重新解析（通常不建议）
            if len(self._buffer) >= total_packet_size:
                del self._buffer[:total_packet_size]
