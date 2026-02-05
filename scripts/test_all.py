#!/usr/bin/env python
import sys
from pathlib import Path

import pytest


def main():
    # 1. 路径自动定位
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 2. 定义默认参数
    # 如果用户没传参数，就用你给出的这一串“全家桶”
    if len(sys.argv) <= 1:
        args = ['--cov=src/', '--cov-report=html', 'tests/']
        print('📊 运行默认测试套件 (含覆盖率报告)...')
    else:
        # 如果用户传了参数（如 ./run_test.py tests/my_test.py），则以用户为准
        args = sys.argv[1:]
        print(f'🛠️ 运行自定义测试: {" ".join(args)}')

    # 3. 执行
    exit_code = pytest.main(args)

    if exit_code == 0:
        print('\n✨ ✅ 测试全部通过！报告已生成在 htmlcov/ 目录。')

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
