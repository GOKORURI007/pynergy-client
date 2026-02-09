from functools import wraps

from evdev import ecodes
from loguru import logger

from src.client.client_types import ClientProtocol, ClientState, HandlerMethod
from src.protocol import (
    CEnterMsg,
    CInfoAckMsg,
    CKeepAliveMsg,
    DInfoMsg,
    DKeyDownLangMsg,
    DKeyDownMsg,
    DKeyRepeatMsg,
    DKeyUpMsg,
    DLanguageSynchronisationMsg,
    DMouseDownMsg,
    DMouseMoveMsg,
    DMouseRelMoveMsg,
    DMouseUpMsg,
    DMouseWheelMsg,
    EIncompatibleMsg,
    MsgBase,
)


def device_check(func):
    @wraps(func)
    def wrapper(self, msg):
        # 1. 状态检查 (这里的 self 指的是调用者，即 Handler 或 Client 的实例)
        if self.client.state != ClientState.ACTIVE:
            logger.warning(f'忽略消息 {msg}，当前状态: {self.client.state}')
            return None

        # 2. 执行核心业务逻辑
        result = func(self, msg)

        # 3. 统一设备同步
        self.client.device.syn()

        return result

    return wrapper


class PynergyHandler:
    """专门负责处理解析后的业务逻辑"""

    def __init__(self, client: ClientProtocol):
        self.client = client

    @staticmethod
    def default_handler(msg):
        logger.warning(f'Ignored message: {msg.CODE}')

    @staticmethod
    def on_hello(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_helloback(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_cclp(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    def on_cbye(self, msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.info('收到关闭连接消息')
        self.client.running = False

    def on_cinn(self, msg: CEnterMsg):
        logger.debug(f'Handle {msg}')
        logger.info(f'进入屏幕，位置: ({msg.entry_x}, {msg.entry_y})')
        self.client.state = ClientState.ACTIVE
        modifiers = msg.mod_key_mask
        self.client.sync_modifiers(modifiers)
        self.client.last_x = None
        self.client.last_y = None

    @staticmethod
    def on_ciak(msg: MsgBase):
        logger.debug(f'Handle {msg}')

    def on_calv(self, msg: CKeepAliveMsg):
        logger.debug(f'Handle {msg}')
        assert self.client.sock is not None
        self.client.sock.sendall(msg.pack_for_socket())

    def on_cout(self, msg: MsgBase):
        logger.debug(f'Handle {msg}')
        self.client.state = ClientState.CONNECTED
        self.client.release_all_keys()

    @staticmethod
    def on_cnop(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_crop(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_csec(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @device_check
    def on_dkdn(self, msg: DKeyDownMsg):
        logger.debug(f'Handle {msg}')

        key_code = msg.key_button
        self.client.pressed_keys.add(key_code)
        self.client.device.write_key(key_code, True)

    @device_check
    def on_dkdl(self, msg: DKeyDownLangMsg):
        logger.debug(f'Handle {msg}')

        key_code = msg.key_button
        self.client.pressed_keys.add(key_code)
        self.client.device.write_key(key_code, True)

    @device_check
    def on_dkrp(self, msg: DKeyRepeatMsg):
        logger.debug(f'Handle {msg}')

        key_code = msg.key_button
        if key_code not in self.client.pressed_keys:
            self.client.pressed_keys.add(key_code)
            self.client.device.write_key(key_code, True)

    @device_check
    def on_dkup(self, msg: DKeyUpMsg):
        logger.debug(f'Handle {msg}')

        key_code = msg.key_button
        self.client.pressed_keys.discard(key_code)
        self.client.device.write_key(key_code, False)

    @device_check
    def on_dmdn(self, msg: DMouseDownMsg):
        logger.debug(f'Handle {msg}')

        button = msg.button
        self.client.device.write_key(button, True)

    @device_check
    def on_dmmv(self, msg: DMouseMoveMsg):
        logger.debug(f'Handle {msg}')

        x, y = msg.x, msg.y
        if self.client.coords_mode == 'relative':
            dx, dy = self.client.abs_to_rel(x, y)
            if dx != 0 or dy != 0:
                self.client.device.write_mouse_move(dx, dy)
        else:
            self.client.write_mouse_abs(x, y)

    @device_check
    def on_dmrm(self, msg: DMouseRelMoveMsg):
        logger.debug(f'Handle {msg}')

        dx, dy = msg.x_delta, msg.y_delta
        if dx != 0 or dy != 0:
            self.client.device.write_mouse_move(dx, dy)

    @device_check
    def on_dmup(self, msg: DMouseUpMsg):
        logger.debug(f'Handle {msg}')

        button = msg.button
        self.client.device.write_key(button, False)

    @device_check
    def on_dmwm(self, msg: DMouseWheelMsg):
        logger.debug(f'Handle {msg}')

        x, y = msg.x_delta, msg.y_delta
        if y != 0:
            self.client.device.write(ecodes.EV_REL, ecodes.REL_WHEEL, y)
        if x != 0:
            self.client.device.write(ecodes.EV_REL, ecodes.REL_HWHEEL, x)

    @device_check
    def on_dclp(self, msg: MsgBase):
        logger.debug(f'Handle {msg}')

    def on_dinf(self, msg: MsgBase):
        logger.debug(f'Handle {msg}, 发送 CIAK')
        self.client.sock.sendall(CInfoAckMsg().pack_for_socket())

    @staticmethod
    def on_dsop(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_ddrg(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_dftr(msg: MsgBase):
        logger.debug(f'Handle {msg}')
        logger.warning('This handler is unimplement')

    @staticmethod
    def on_lsyn(msg: DLanguageSynchronisationMsg):
        logger.debug(f'Handle {msg}')

    @staticmethod
    def on_secn(msg: MsgBase):
        logger.debug(f'Handle {msg}')

    def on_qinf(self, msg: MsgBase):
        logger.debug(f'Handle {msg}，发送 DINF')
        dinf_msg = DInfoMsg(
            0,
            0,
            self.client.screen_width,
            self.client.screen_height,
            0,
            0,
            0,
        )
        assert self.client.sock is not None
        self.client.sock.sendall(dinf_msg.pack_for_socket())

    def on_ebad(self, msg: MsgBase):
        logger.debug(f'Handle {msg}')
        self.client.running = False

    def on_ebsy(self, msg: MsgBase):
        logger.debug(f'Handle {msg}')
        self.client.running = False

    def on_eicv(self, msg: EIncompatibleMsg):
        logger.debug(f'Handle {msg}')
        logger.error(f'版本不兼容错误: {msg.major}.{msg.minor}')
        self.client.running = False

    def on_eunk(self, msg: MsgBase):
        logger.debug(f'Handle {msg}')
        self.client.running = False


class MessageDispatcher:
    def __init__(self, handler: PynergyHandler):
        self.handler = handler

    def dispatch(self, msg: MsgBase):
        # 根据类名动态寻找 handle_ 方法
        handler_name = f'on_{msg.CODE.lower()}'
        handler: HandlerMethod = getattr(self.handler, handler_name, self.handler.default_handler)
        handler(msg)
