import os
import sys
import tomllib
from pathlib import Path

from loguru import logger


def get_version():
    nix_version = os.getenv('APP_VERSION')
    if nix_version:
        return nix_version

    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent.parent

    toml_path = base_path / 'pyproject.toml'

    if toml_path.exists():
        try:
            with open(toml_path, 'rb') as f:
                return tomllib.load(f).get('project', {}).get('version', '0.1.0')
        except FileNotFoundError as e:
            print(e)

    try:
        from importlib.metadata import version

        return version('pynergy-client')
    except Exception as e:
        logger.warning(f'Failed to get version: {e}')
        return 'unknown'


__version__ = get_version()
