import time
from functools import wraps
from hypium.utils.logger import basic_log
from .typevar import T

def timer(func: T) -> T:
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
        finally:
            end = time.time()
            basic_log.info("%s used: %.2fs" % (func.__name__, end - start))
        return result

    return wrapper
