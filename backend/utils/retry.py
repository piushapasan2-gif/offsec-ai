"""Decorator for exponential-backoff retries on flaky API calls."""
import time
import functools
from backend.utils.logger import get_logger

log = get_logger("retry")


def with_retry(retries: int = 3, base_delay: float = 1.0, backoff: float = 2.0,
               exceptions: tuple = (Exception,)):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_err = None
            for attempt in range(retries):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_err = e
                    log.warning(f"[{fn.__name__}] attempt {attempt+1}/{retries} failed: {e}")
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay *= backoff
            raise last_err
        return wrapper
    return decorator
