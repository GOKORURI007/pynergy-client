import struct
from typing import Literal

from loguru import logger

from .core import MsgBase, Registry
from .protocol_types import MsgID


class PynergyParser[T: MsgBase]:
    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes):
        """Store received raw bytes"""
        if not data:
            return
        logger.opt(lazy=True).trace('{log}', log=lambda: f'Fed {len(data)} bytes into buffer')
        self._buffer.extend(data)

    def _parse_packet(self, get_class_func):
        """
        Private helper method: Core logic for parsing packets.
        :param get_class_func: Function to get message class (for distinguishing next_msg and next_handshake_msg)
        :return: Parsed message object or None
        """
        total_packet_size = 0

        # Basic length check (first 4 bytes are packet length)
        if len(self._buffer) < 4:
            return None

        try:
            # 1. Read length prefix
            length = struct.unpack_from('>I', self._buffer)[0]

            # Protocol security check: Prevent malicious oversized packets from causing OOM
            if length > 10 * 1024 * 1024:  # Assume max packet size is 10MB
                logger.opt(lazy=True).error(
                    '{log}', log=lambda: f'Invalid packet length: {length}, clearing buffer'
                )
                self._buffer.clear()
                return None

            # Check if buffer has enough data
            total_packet_size = 4 + length
            if len(self._buffer) < total_packet_size:
                logger.opt(lazy=True).trace(
                    '{log}',
                    log=lambda: f'Wait for more data: {len(self._buffer)}/{total_packet_size}',
                )
                return None

            # 2. Extract packet (skip first 4 bytes of length)
            packet = self._buffer[4:total_packet_size]

            try:
                # 3. Call passed function to get message class
                cls = get_class_func(packet)

                if not cls:
                    logger.opt(lazy=True).warning(
                        '{log}',
                        log=lambda: (
                            f'Unknown message code: {packet[:4].decode()}, size: {length}. Skipping.'
                        ),
                    )
                    return None

                # 4. Perform deserialization
                msg_obj = cls.unpack(packet)
                logger.opt(lazy=True).trace(
                    '{log}', log=lambda: f'Successfully parsed message: {msg_obj}'
                )
                return msg_obj

            except (struct.error, UnicodeDecodeError, ValueError):
                logger.opt(lazy=True).error(
                    '{log}',
                    log=lambda: f'Failed to unpack message body (CODE: {packet[:4].decode()}): {e}',
                )
                return None

            except Exception:
                logger.opt(lazy=True).exception(
                    '{log}', log=lambda: f'Unexpected error during message construction: {e}'
                )
                return None

        finally:
            # Core principle: Regardless of parsing success, consume this data as long as length is sufficient
            if len(self._buffer) >= total_packet_size:
                del self._buffer[:total_packet_size]

    def next_msg(self) -> T | None:
        """
        Try to parse and return a regular message object.
        """

        def get_class(packet):
            # Extract msg_code from packet and find corresponding message class
            msg_code = struct.unpack_from('>4s', packet)[0]
            return Registry.get_class(msg_code.decode())

        return self._parse_packet(get_class)

    def next_handshake_msg(self, msg_type: Literal[MsgID.Hello, MsgID.HelloBack]) -> T | None:
        """
        Try to parse and return a Handshake message object.
        """

        def get_class(_packet):
            # Find message class directly by msg_type
            return Registry.get_class(msg_type)

        return self._parse_packet(get_class)
