import time
from typing import List
from hypium.utils.logger import basic_log
from hypium.utils.typevar import T


class Runnable:

    def __init__(self, func, args=(), kwargs=None, err_message=""):
        if kwargs is None:
            kwargs = {}
        self.func = func
        self.args = args
        self.func_name = getattr(func, "__name__", "unknown")
        self.kwargs = kwargs
        self.err_message = err_message

    def run(self):
        return self.func(*self.args, **self.kwargs)


def run_multiple_function_with_retry(runnable_list: List[Runnable]):
    last_err = None
    for runnable in runnable_list:
        try:
            return runnable.run()
        except Exception as e:
            last_err = e
            basic_log.warning("Function [%s] failed, err_msg: %s, raw exception: %s" % (runnable.func_name,
                                                                                        runnable.err_message,
                                                                                        repr(last_err)))
    if last_err:
        raise last_err

    return None


def _read_timeout(args, kwargs):
    timeout = 0
    if len(args) >= 0:
        default_timeout = getattr(args[0], "_widget_find_timeout", 0)
        if default_timeout > 0:
            timeout = default_timeout

    if "timeout" in kwargs.keys():
        param_timeout = kwargs.get("timeout")
        kwargs.pop("timeout")
        timeout = param_timeout

    return timeout


def format_args(args):
    return ', '.join(map(str, args))


def support_retry(need_retry, interval=0.5):
    def support_retry_deco(func: T) -> T:
        def wrapper(*args, **kwargs):
            start = time.time()
            wait_time = _read_timeout(args, kwargs)
            should_print_log = kwargs.pop("PRINT_LOG", True)
            func_name = getattr(func, "__qualname__", "unknown")
            if should_print_log:
                func_name_with_args = "%s(%s), kwargs: %s" % (func_name, format_args(args), kwargs)
                basic_log.debug(func_name_with_args)
            result = None
            for i in range(100):
                result = func(*args, **kwargs)
                if not need_retry(result):
                    break
                elif wait_time == 0 or time.time() - start > wait_time:
                    break
                time.sleep(interval)
            if should_print_log:
                basic_log.debug("%s return: %s" % (func_name, result))
            return result

        return wrapper

    return support_retry_deco
