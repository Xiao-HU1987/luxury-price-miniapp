"""爬虫工具函数：重试、等待、日志等"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger("lv_crawler.utils")

T = TypeVar("T")


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    name: str = "",
    **kwargs,
) -> Optional[T]:
    """带重试的异步函数执行。

    Args:
        func: 要执行的异步函数
        retries: 最大重试次数（不含首次）
        delay: 首次重试前的延迟（秒）
        backoff: 重试延迟倍增系数
        exceptions: 需要重试的异常类型
        name: 函数名称（用于日志）

    Returns:
        函数返回值；全部重试失败则返回 None
    """
    func_name = name or func.__name__
    last_exception: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.debug("重试 %s 成功 (第 %d 次尝试)", func_name, attempt + 1)
            return result
        except exceptions as e:
            last_exception = e
            if attempt < retries:
                wait_time = delay * (backoff ** attempt)
                logger.warning(
                    "%s 失败 (第 %d/%d 次尝试)，%.1f 秒后重试: %s",
                    func_name, attempt + 1, retries + 1, wait_time, e,
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    "%s 全部 %d 次尝试均失败: %s",
                    func_name, retries + 1, e,
                )

    return None


def sync_retry(
    func: Callable[..., T],
    *args,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    name: str = "",
    **kwargs,
) -> Optional[T]:
    """带重试的同步函数执行。"""
    func_name = name or func.__name__
    last_exception: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 0:
                logger.debug("重试 %s 成功 (第 %d 次尝试)", func_name, attempt + 1)
            return result
        except exceptions as e:
            last_exception = e
            if attempt < retries:
                wait_time = delay * (backoff ** attempt)
                logger.warning(
                    "%s 失败 (第 %d/%d 次尝试)，%.1f 秒后重试: %s",
                    func_name, attempt + 1, retries + 1, wait_time, e,
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    "%s 全部 %d 次尝试均失败: %s",
                    func_name, retries + 1, e,
                )

    return None
