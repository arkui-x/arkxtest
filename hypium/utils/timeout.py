#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import sys
import threading
from functools import wraps


class KThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.killed = False
        self._stop_event = threading.Event()
        self.__run_backup = None

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run  # Force the Thread to install our trace.
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the
        trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class Timeout(Exception):
    """function run timeout"""
    pass


def timeout(seconds, daemon=False):
    """超时装饰器，指定超时时间
    若被装饰的方法在指定的时间内未返回，则抛出Timeout异常"""

    def timeout_decorator(func):
        """真正的装饰器"""

        def _new_func(oldfunc, result, oldfunc_args, oldfunc_kwargs):
            result.append(oldfunc(*oldfunc_args, **oldfunc_kwargs))

        @wraps(func)
        def _(*args, **kwargs):
            result = []
            new_kwargs = {  # create new args for _new_func, because we want to get the func return val to result list
                'oldfunc': func,
                'result': result,
                'oldfunc_args': args,
                'oldfunc_kwargs': kwargs
            }
            thd = KThread(target=_new_func, args=(), kwargs=new_kwargs, daemon=daemon)
            thd.start()
            thd.join(seconds)
            alive = thd.is_alive()
            thd.kill()  # kill the child thread
            if alive:
                raise Timeout(u'function run too long, timeout %d seconds.' % seconds)
            else:
                if len(result) == 0:
                    raise Exception(u'testcase failed')
                else:
                    return result[0]

        return _

    return timeout_decorator


def release_lock_after_timeout(logger):
    if not isinstance(logger, logging.Logger) or not hasattr(logger, "handlers"):
        return
    for hdl in logger.handlers:
        lock = hdl.lock
        if lock._is_owned():
            lock.release()
