import json
import os
import subprocess

from loguru import logger

from pynergy_client.device.base import BaseDeviceContext


class WaylandDeviceContext(BaseDeviceContext):
    def __init__(self):
        super().__init__()

    def update_screen_info(self) -> None:
        try:
            result = subprocess.run(['wlr-randr', '--json'], capture_output=True, text=True)
            json_dict = json.loads(result.stdout)
            for mode in json_dict[0]['modes']:
                if mode['current']:
                    self.screen_size = (mode['width'], mode['height'])
                    return
        except Exception:
            logger.opt(lazy=True).warning(
                '{log}', log=lambda: f'Failed to get active screen resolution by wlr-randr: {e}'
            )

        try:
            res = self.get_active_screen_resolution_by_kernel()
            match res:
                case (int(x), int(y)):
                    self.screen_size = (x, y)
                    return
                case _:
                    raise ValueError('Failed to get active screen resolution by kernel')
        except Exception as e:
            err_str = str(e)
            logger.opt(lazy=True).warning('{log}', log=lambda: f'{err_str}')

        self.screen_size = (1920, 1080)
        logger.opt(lazy=True).warning(
            '{log}', log=lambda: f'Using default screen size: {self.screen_size}'
        )

    def get_real_cursor_pos(self) -> tuple[int, int] | None:
        try:
            match os.getenv('XDG_CURRENT_DESKTOP'):
                case 'Hyprland':
                    result = subprocess.run(
                        ['hyprctl', 'cursorpos'], capture_output=True, text=True
                    )
                    x, y = [int(s) for s in result.stdout.split(',')]
                    return x, y
                case _:
                    raise ValueError('Unsupported desktop environment')
        except Exception:
            logger.opt(lazy=True).warning(
                '{log}', log=lambda: f'get cursor pos by hyprctl failed: {e}'
            )

        # Last attempt: use environment variables or default values
        logger.opt(lazy=True).warning(
            '{log}',
            log=lambda: (
                'Warning: Cannot get accurate cursor position in current Wayland environment'
            ),
        )
        # Return center position as fallback
        if self.screen_size[0] > 0 and self.screen_size[1] > 0:
            return self.screen_size[0] // 2, self.screen_size[1] // 2

        return None
