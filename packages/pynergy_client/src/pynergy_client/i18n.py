import gettext
import locale
import os
from pathlib import Path


def _get_translator():
    # 1. Determine language code
    # Check environment variable first, convenient for manual switching on NixOS (e.g., LANG=en_US pynergy)
    default_lang = locale.getlocale()[0] or 'en_US'
    lang = os.environ.get('LANG', default_lang).split('.')[0]

    # 2. Locate locales directory relative to current file
    # Structure: pynergy_client/locales/zh_CN/LC_MESSAGES/pynergy.mo
    locale_dir = Path(__file__).parent.resolve() / 'locales'

    # 3. Load translation object
    # Note: domain must match the DOMAIN in the script
    translation = gettext.translation(
        domain='pynergy', localedir=str(locale_dir), languages=[lang], fallback=True
    )
    return translation.gettext


# Singleton export
_ = _get_translator()
