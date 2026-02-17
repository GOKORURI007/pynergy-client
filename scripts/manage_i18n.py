import subprocess
import sys
from pathlib import Path

# 路径配置
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / 'packages' / 'pynergy_client' / 'src'
LOCALES_DIR = SRC_DIR / 'pynergy_client' / 'locales'
BABEL_CFG = ROOT_DIR / 'babel.cfg'
POT_FILE = ROOT_DIR / 'messages.pot'
DOMAIN = 'pynergy'
LANGUAGES = ['zh_CN', 'en_US']


def run_command(cmd):
    """运行 shell 命令并处理错误"""
    try:
        print(f'执行: {" ".join(cmd)}')
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f'错误: 命令执行失败 - {e}')
        sys.exit(1)


def main():
    # 1. 确保目录存在
    LOCALES_DIR.mkdir(parents=True, exist_ok=True)

    # 2. 提取文案
    print('\n--- [1/3] 提取源码中的待翻译字符串 ---')
    run_command(['pybabel', 'extract', '-F', str(BABEL_CFG), '-o', str(POT_FILE), str(SRC_DIR)])

    # 3. 更新或初始化语言文件
    print('\n--- [2/3] 更新/初始化语言文件 (.po) ---')
    for lang in LANGUAGES:
        po_file = LOCALES_DIR / lang / 'LC_MESSAGES' / f'{DOMAIN}.po'
        if not po_file.exists():
            print(f'初始化新语言: {lang}')
            run_command([
                'pybabel',
                'init',
                '-i',
                str(POT_FILE),
                '-d',
                str(LOCALES_DIR),
                '-l',
                lang,
                '-D',
                DOMAIN,
            ])
        else:
            print(f'更新现有语言: {lang}')
            run_command([
                'pybabel',
                'update',
                '-i',
                str(POT_FILE),
                '-d',
                str(LOCALES_DIR),
                '-D',
                DOMAIN,
            ])

    # 4. 编译二进制文件
    print('\n--- [3/3] 编译二进制翻译文件 (.mo) ---')
    run_command(['pybabel', 'compile', '-d', str(LOCALES_DIR), '-D', DOMAIN])

    print('\n✅ 所有任务已完成！')


if __name__ == '__main__':
    main()
