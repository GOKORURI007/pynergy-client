"""
Niri + Mac Deskflow Compatibility Module
=========================================

This module patches PynergyHandler methods to add support for:
1. Mac deskflow servers that send key_id (X11 keysym) instead of key_button
2. Niri (Wayland compositor) key repeat behavior via tap_key
3. Absolute mouse positioning via wlr-randr detected screen size

Usage:
    from pynergy_client.niri_compat import patch_handler
    from pynergy_client.client.handlers import PynergyHandler
    patch_handler(PynergyHandler)

Or set env PYNERGY_NIRI_COMPAT=1 before importing pynergy_client
to auto-patch at import time.
"""

import os
from functools import wraps

from evdev import ecodes as e
from loguru import logger

# ---------------------------------------------------------------------------
# Key mapping tables
# ---------------------------------------------------------------------------

# key_id (Unicode/keysym) -> evdev keycode for printable ASCII (US layout base)
KEY_ID_TO_ECODE: dict[int, int] = {
    0x0020: e.KEY_SPACE,
    0x0030: e.KEY_0, 0x0031: e.KEY_1, 0x0032: e.KEY_2, 0x0033: e.KEY_3, 0x0034: e.KEY_4,
    0x0035: e.KEY_5, 0x0036: e.KEY_6, 0x0037: e.KEY_7, 0x0038: e.KEY_8, 0x0039: e.KEY_9,
    0x002D: e.KEY_MINUS,   # -
    0x003D: e.KEY_EQUAL,   # =
    0x0060: e.KEY_GRAVE,   # `
    0x005B: e.KEY_LEFTBRACE,   # [
    0x005D: e.KEY_RIGHTBRACE,  # ]
    0x005C: e.KEY_BACKSLASH,   # \\
    0x003B: e.KEY_SEMICOLON,   # ;
    0x0027: e.KEY_APOSTROPHE,  # '
    0x002C: e.KEY_COMMA,       # ,
    0x002E: e.KEY_DOT,         # .
    0x002F: e.KEY_SLASH,       # /
    0x0061: e.KEY_A, 0x0062: e.KEY_B, 0x0063: e.KEY_C, 0x0064: e.KEY_D, 0x0065: e.KEY_E,
    0x0066: e.KEY_F, 0x0067: e.KEY_G, 0x0068: e.KEY_H, 0x0069: e.KEY_I, 0x006A: e.KEY_J,
    0x006B: e.KEY_K, 0x006C: e.KEY_L, 0x006D: e.KEY_M, 0x006E: e.KEY_N, 0x006F: e.KEY_O,
    0x0070: e.KEY_P, 0x0071: e.KEY_Q, 0x0072: e.KEY_R, 0x0073: e.KEY_S, 0x0074: e.KEY_T,
    0x0075: e.KEY_U, 0x0076: e.KEY_V, 0x0077: e.KEY_W, 0x0078: e.KEY_X, 0x0079: e.KEY_Y,
    0x007A: e.KEY_Z,
}

# Shifted key_id -> base key_id (used to know when to press Shift)
SHIFTED_TO_BASE: dict[int, int] = {
    0x0041: 0x0061, 0x0042: 0x0062, 0x0043: 0x0063, 0x0044: 0x0064,
    0x0045: 0x0065, 0x0046: 0x0066, 0x0047: 0x0067, 0x0048: 0x0068,
    0x0049: 0x0069, 0x004A: 0x006A, 0x004B: 0x006B, 0x004C: 0x006C,
    0x004D: 0x006D, 0x004E: 0x006E, 0x004F: 0x006F, 0x0050: 0x0070,
    0x0051: 0x0071, 0x0052: 0x0072, 0x0053: 0x0073, 0x0054: 0x0074,
    0x0055: 0x0075, 0x0056: 0x0076, 0x0057: 0x0077, 0x0058: 0x0078,
    0x0059: 0x0079, 0x005A: 0x007A,
    0x0021: 0x0031, 0x0040: 0x0032, 0x0023: 0x0033, 0x0024: 0x0034,
    0x0025: 0x0035, 0x005E: 0x0036, 0x0026: 0x0037, 0x002A: 0x0038,
    0x0028: 0x0039, 0x0029: 0x0030, 0x005F: 0x002D, 0x002B: 0x003D,
    0x007E: 0x0060, 0x007B: 0x005B, 0x007D: 0x005D, 0x007C: 0x005C,
    0x003A: 0x003B, 0x0022: 0x0027, 0x003C: 0x002C, 0x003E: 0x002E,
    0x003F: 0x002F,
}

# Synergy/Deskflow special key_id values (function keys, navigation, etc.)
SYNERGY_KEY_ID_MAP: dict[int, int] = {
    0xFF08: e.KEY_BACKSPACE,
    0xFF09: e.KEY_TAB,
    0xFF0D: e.KEY_ENTER,
    0xFF1B: e.KEY_ESC,
    0xFFFF: e.KEY_DELETE,
    0xFF50: e.KEY_HOME,
    0xFF51: e.KEY_LEFT,
    0xFF52: e.KEY_UP,
    0xFF53: e.KEY_RIGHT,
    0xFF54: e.KEY_DOWN,
    0xFF55: e.KEY_PAGEUP,
    0xFF56: e.KEY_PAGEDOWN,
    0xFF57: e.KEY_END,
    0xFF63: e.KEY_INSERT,
    0xFFBE: e.KEY_F1,  0xFFBF: e.KEY_F2,  0xFFC0: e.KEY_F3,  0xFFC1: e.KEY_F4,
    0xFFC2: e.KEY_F5,  0xFFC3: e.KEY_F6,  0xFFC4: e.KEY_F7,  0xFFC5: e.KEY_F8,
    0xFFC6: e.KEY_F9,  0xFFC7: e.KEY_F10, 0xFFC8: e.KEY_F11, 0xFFC9: e.KEY_F12,
    0xFFE1: e.KEY_LEFTSHIFT,
    0xFFE2: e.KEY_LEFTSHIFT,
    0xFFE3: e.KEY_LEFTCTRL,
    0xFFE4: e.KEY_LEFTCTRL,
    0xFFE5: e.KEY_CAPSLOCK,
    0xFFE7: e.KEY_LEFTMETA,
    0xFFE8: e.KEY_LEFTMETA,
    0xFFEB: e.KEY_LEFTMETA,  # Mac deskflow sends left Command as right Meta
    0xFFEC: e.KEY_LEFTMETA,  # right Command (if also mis-mapped)
    0xFFE9: e.KEY_LEFTALT,
    0xFFEA: e.KEY_LEFTALT,
}

# Modifier key ecodes that must be held (not tapped)
MODIFIER_ECODES: set[int] = {
    e.KEY_LEFTSHIFT, e.KEY_RIGHTSHIFT,
    e.KEY_LEFTCTRL, e.KEY_RIGHTCTRL,
    e.KEY_LEFTALT, e.KEY_RIGHTALT,
    e.KEY_LEFTMETA, e.KEY_RIGHTMETA,
}

def key_id_to_ecode(key_id: int) -> int | None:
    """Convert synergy key_id (keysym/Unicode) to evdev keycode."""
    # Try direct lookup first
    if key_id in SYNERGY_KEY_ID_MAP:
        return SYNERGY_KEY_ID_MAP[key_id]
    if key_id in KEY_ID_TO_ECODE:
        return KEY_ID_TO_ECODE[key_id]
    base = SHIFTED_TO_BASE.get(key_id)
    if base is not None and base in KEY_ID_TO_ECODE:
        return KEY_ID_TO_ECODE[base]

    # Mac deskflow sends X11 keysyms offset by -0x1000 (0xEFxx = 0xFFxx - 0x1000)
    if 0xEF00 <= key_id <= 0xEFFF:
        adjusted = key_id + 0x1000
        if adjusted in SYNERGY_KEY_ID_MAP:
            return SYNERGY_KEY_ID_MAP[adjusted]
        adjusted_base = SHIFTED_TO_BASE.get(adjusted)
        if adjusted_base is not None and adjusted_base in KEY_ID_TO_ECODE:
            return KEY_ID_TO_ECODE[adjusted_base]

    # Try as direct evdev keycode (some servers send raw button codes)
    if 1 <= key_id <= 255:
        return key_id

    return None


def _make_niri_dkdn(orig_dkdn):
    """Wrap on_dkdn to prefer key_id mapping, fallback to original synergy logic."""

    @wraps(orig_dkdn)
    async def wrapper(self, msg, client):
        logger.opt(lazy=True).debug(
            '{log}', log=lambda: f'[niri] DKDN: key_id={msg.key_id}({hex(msg.key_id)}) button={msg.key_button}'
        )
        ecode = key_id_to_ecode(msg.key_id)
        if ecode is not None:
            needs_shift = msg.key_id in SHIFTED_TO_BASE
            if needs_shift:
                self.keyboard.send_key(e.KEY_LEFTSHIFT, True)
                self._logically_held.add(e.KEY_LEFTSHIFT)

            self._logically_held.add(ecode)
            if ecode in MODIFIER_ECODES:
                self.keyboard.send_key(ecode, True)
            else:
                self.keyboard.tap_key(ecode)
        else:
            # Fallback to original key_button logic
            from pynergy_client.keymaps import hid_to_ecode, synergy_to_hid
            key_code = msg.key_button
            hid = synergy_to_hid(key_code)
            ecode2 = hid_to_ecode(hid)
            if ecode2 is not None:
                self._logically_held.add(ecode2)
                if ecode2 in MODIFIER_ECODES:
                    self.keyboard.send_key(ecode2, True)
                else:
                    self.keyboard.tap_key(ecode2)

    return wrapper


def _make_niri_dkdl(orig_dkdl):
    """Wrap on_dkdl to prefer key_id mapping."""

    @wraps(orig_dkdl)
    async def wrapper(self, msg, client):
        logger.opt(lazy=True).debug(
            '{log}', log=lambda: f'[niri] DKDL: key_id={msg.key_id}({hex(msg.key_id)})'
        )
        ecode = key_id_to_ecode(msg.key_id)
        if ecode is not None:
            self._logically_held.add(ecode)
            if ecode in MODIFIER_ECODES:
                self.keyboard.send_key(ecode, True)
            else:
                self.keyboard.tap_key(ecode)
        else:
            from pynergy_client.keymaps import hid_to_ecode, synergy_to_hid
            key_code = msg.key_button
            hid = synergy_to_hid(key_code)
            ecode2 = hid_to_ecode(hid)
            if ecode2 is not None:
                self._logically_held.add(ecode2)
                if ecode2 in MODIFIER_ECODES:
                    self.keyboard.send_key(ecode2, True)
                else:
                    self.keyboard.tap_key(ecode2)

    return wrapper


def _make_niri_dkrp(orig_dkrp):
    """Wrap on_dkrp to use key_id mapping and tap_key on repeat."""

    @wraps(orig_dkrp)
    async def wrapper(self, msg, client):
        logger.opt(lazy=True).debug(
            '{log}', log=lambda: f'[niri] DKRP: key_id={msg.key_id}({hex(msg.key_id)})'
        )
        ecode = key_id_to_ecode(msg.key_id)
        if ecode is not None and ecode in self._logically_held:
            if ecode not in MODIFIER_ECODES:
                self.keyboard.tap_key(ecode)

    return wrapper


def _make_niri_dkup(orig_dkup):
    """Wrap on_dkup to use key_id mapping and properly release shifted keys."""

    @wraps(orig_dkup)
    async def wrapper(self, msg, client):
        logger.opt(lazy=True).debug(
            '{log}', log=lambda: f'[niri] DKUP: key_id={msg.key_id}({hex(msg.key_id)}) button={msg.key_button}'
        )
        ecode = key_id_to_ecode(msg.key_id)
        if ecode is not None:
            needs_shift = msg.key_id in SHIFTED_TO_BASE
            self._logically_held.discard(ecode)
            if ecode in MODIFIER_ECODES:
                self.keyboard.send_key(ecode, False)
            if needs_shift:
                self._logically_held.discard(e.KEY_LEFTSHIFT)
                self.keyboard.send_key(e.KEY_LEFTSHIFT, False)
        else:
            from pynergy_client.keymaps import hid_to_ecode, synergy_to_hid
            key_code = msg.key_button
            ecode2 = hid_to_ecode(synergy_to_hid(key_code))
            if ecode2 is not None:
                self._logically_held.discard(ecode2)

    return wrapper


def _make_niri_cinn(orig_cinn):
    """Wrap on_cinn — normalize entry coords to mouse's ABS range and defer to original."""

    @wraps(orig_cinn)
    async def wrapper(self, msg, client):
        actual_w, actual_h = self.ctx.screen_size
        abs_max_w, abs_max_h = 1920, 1080  # UInputMouseDevice default ABS range
        # Only normalize if coords exceed ABS range (avoids double-normalization)
        if msg.entry_x > abs_max_w or msg.entry_y > abs_max_h:
            scale_x = abs_max_w / actual_w
            scale_y = abs_max_h / actual_h
            norm_x = int(msg.entry_x * scale_x)
            norm_y = int(msg.entry_y * scale_y)
            logger.info(
                '[niri] CEnter: raw=({}, {}) screen={} -> norm=({}, {})',
                msg.entry_x, msg.entry_y, self.ctx.screen_size, norm_x, norm_y,
            )
            msg.entry_x = norm_x
            msg.entry_y = norm_y
        await orig_cinn(self, msg, client)

    return wrapper


def _make_niri_dmmv(orig_dmmv):
    """Wrap on_dmmv — normalize move coords to mouse's ABS range and defer to original."""

    @wraps(orig_dmmv)
    async def wrapper(self, msg, client):
        actual_w, actual_h = self.ctx.screen_size
        abs_max_w, abs_max_h = 1920, 1080  # UInputMouseDevice default ABS range
        if msg.x > abs_max_w or msg.y > abs_max_h:
            scale_x = abs_max_w / actual_w
            scale_y = abs_max_h / actual_h
            norm_x = int(msg.x * scale_x)
            norm_y = int(msg.y * scale_y)
            msg.x = norm_x
            msg.y = norm_y
        await orig_dmmv(self, msg, client)

    return wrapper

def patch_handler(handler_class):
    """
    Monkey-patch PynergyHandler to add Mac deskflow key_id support and niri compatibility.

    Call this once at startup before connecting:
        from pynergy_client.niri_compat import patch_handler
        from pynergy_client.client.handlers import PynergyHandler
        patch_handler(PynergyHandler)
    """
    handler_class.on_dkdn = _make_niri_dkdn(handler_class.on_dkdn)
    handler_class.on_dkdl = _make_niri_dkdl(handler_class.on_dkdl)
    handler_class.on_dkrp = _make_niri_dkrp(handler_class.on_dkrp)
    handler_class.on_dkup = _make_niri_dkup(handler_class.on_dkup)
    handler_class.on_cinn = _make_niri_cinn(handler_class.on_cinn)
    handler_class.on_dmmv = _make_niri_dmmv(handler_class.on_dmmv)
    logger.info('[niri] PynergyHandler patched for Mac deskflow + niri compatibility')


# Auto-patch if environment variable is set
_auto_patched = False
if os.environ.get('PYNERGY_NIRI_COMPAT', '').lower() in ('1', 'true', 'yes'):
    try:
        from pynergy_client.client.handlers import PynergyHandler
        patch_handler(PynergyHandler)
        _auto_patched = True
    except ImportError:
        pass
