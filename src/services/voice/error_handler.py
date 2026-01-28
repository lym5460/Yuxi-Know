"""Voice Error Handler.

指数退避重试和错误日志记录。

Validates: Requirements 11.4, 11.5, 11.6
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from src.utils.logging_config import logger

T = TypeVar("T")


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


async def retry_with_backoff(
    func: Callable[[], T],
    config: RetryConfig | None = None,
    context: dict | None = None,
) -> T:
    """指数退避重试
    
    Args:
        func: 要执行的异步函数
        config: 重试配置
        context: 错误日志上下文
        
    Returns:
        函数执行结果
        
    Raises:
        最后一次重试的异常
    """
    config = config or RetryConfig()
    context = context or {}
    
    last_exception = None
    
    for attempt in range(config.max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            # 记录错误日志
            log_error(e, {
                **context,
                "attempt": attempt + 1,
                "max_retries": config.max_retries,
            })
            
            if attempt == config.max_retries - 1:
                break
                
            # 计算延迟
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            logger.info(f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{config.max_retries})")
            await asyncio.sleep(delay)
    
    raise last_exception


def log_error(error: Exception, context: dict | None = None):
    """记录错误日志
    
    Args:
        error: 异常对象
        context: 上下文信息（session_id, user_id, error_type 等）
    """
    context = context or {}
    
    log_data = {
        "timestamp": time.time(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        **context,
    }
    
    logger.error(f"Voice error: {log_data}", exc_info=True)
