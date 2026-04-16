import time
import traceback
from datetime import datetime
from .typevar import T
from functools import wraps
from devicetest.log.logger import platform_logger

hypium_test_api_log = platform_logger("HypiumTestApi")


class TimeStat:
    """调用时间分析"""
    stat = {}

    @classmethod
    def record_call(cls, name, time_used_s):
        if name in cls.stat.keys():
            item = cls.stat[name]
            item["times"] += 1
            item["total_time"] += time_used_s
            if time_used_s > item["max"]:
                item["max_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                item['max'] = time_used_s
            item["min"] = min(item["min"], time_used_s)
        else:
            item = {
                "times": 1,
                "total_time": time_used_s,
                "max": time_used_s,
                "max_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "min": time_used_s
            }
            cls.stat[name] = item

    @classmethod
    def get_stat(cls):
        return cls.stat

    @classmethod
    def format_stat(cls) -> str:
        output = ""
        for key, value in cls.stat.items():
            value['avg'] = value["total_time"] / value['times']
            output += "#######################\n"
            output += "name: %s\n" % key
            output += "times: %s\n" % value['times']
            output += "total_time: %s\n" % value['total_time']
            output += "max: %s\n" % value["max"]
            output += "min: %s\n" % value["min"]
            output += "avg: %s\n" % value["avg"]
        return output

    @classmethod
    def print_stat(cls):
        for key, value in cls.stat.items():
            value['avg'] = value["total_time"] / value['times']
            print("#######################")
            print("name", key)
            print("times", value['times'])
            print("total_time", value['total_time'])
            print("max", value["max"])
            print("min", value["min"])
            print("avg", value["avg"])

    @classmethod
    def reset(cls):
        cls.stat = {}


class ApiStat:
    """AW调用分析"""

    def __init__(self):
        self.aw_stat = dict()

    def record_api_call(self, api_name: str):
        if api_name in self.aw_stat.keys():
            self.aw_stat[api_name] += 1
        else:
            self.aw_stat[api_name] = 1

    def print_stat(self):
        print(self.aw_stat)


api_stat = ApiStat()


def record_time(func: T) -> T:
    """
    @func 统计调用时间
    """
    func_name = func.__name__

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        TimeStat.record_call(func_name, end - start)
        return result

    return wrapper


def run_fun_with_time_stat(func, args, kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    TimeStat.record_call(func.__name__, end - start)
    return result


def aw_query(func: T) -> T:
    """数据查询类AW"""
    func_name = func.__qualname__

    @wraps(func)
    def wrapper(*args, **kwargs):
        api_stat.record_api_call(func_name)
        result = func(*args, **kwargs)
        return result

    return wrapper


def aw_action(func: T) -> T:
    """操作类AW"""
    func_name = func.__qualname__

    @wraps(func)
    def wrapper(*args, **kwargs):
        api_stat.record_api_call(func_name)
        result = func(*args, **kwargs)
        return result

    return wrapper


def aw_check(func: T) -> T:
    """检查点(断言类)AW"""
    func_name = func.__qualname__

    @wraps(func)
    def wrapper(*args, **kwargs):
        api_stat.record_api_call(func_name)
        result = func(*args, **kwargs)
        return result

    return wrapper


if __name__ == "__main__":
    @aw_query
    def hello():
        print("你好")


    hello()
    api_stat.print_stat()
