import typer

from src.pynergy_client.app import main  # 使用绝对导入

if __name__ == '__main__':
    typer.run(main)
