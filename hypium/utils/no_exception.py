from typing import TypeVar

T = TypeVar('T')


def no_exception(func: T) -> T:
    func_name = func.__name__
    def wrapper(*args, **kwargs):
        driver = None
        # 读取driver参数
        if len(args) == 1:
            driver = args[0]
        elif len(args) >= 2:
            driver = args[0] if hasattr(args[0], "log_error") else args[1]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if hasattr(driver, "log_error"):
                driver.log_error("%s Error: %s %s" % (func_name, e.__class__.__name__, str(e)))
            else:
                print("%s Error: %s %s" % (func_name, e.__class__.__name__, str(e)))
            return None
    return wrapper
