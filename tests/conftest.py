import pytest
from loguru import logger


@pytest.fixture
def propagate_logs(caplog):
    # 定义一个适配器，将 Loguru 的记录发往标准 logging
    handler_id = logger.add(caplog.handler, format='{message}')
    yield caplog
    # 测试结束后移除该 handler，避免污染后续测试
    logger.remove(handler_id)
