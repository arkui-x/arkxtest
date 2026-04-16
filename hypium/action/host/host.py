"""
此文件实现host层中无特殊分类的接口
"""
from typing import Any, Union
import zipfile
import os
import time
from devicetest.core.test_case import keyword, checkepr, MESSAGE, EXPECT, ACTUAL
from hypium.utils.utils import Time
from hypium.utils.shell import run_command


@keyword
def shell(cmd: Union[str, list], timeout: float = 300) -> str:
    """
    @func: 在PC端执行shell命令
    @param: cmd: 命令内容
    @param: timeout: 超时时间, 单位秒
    @example: # 在PC端执行dir命令
              echo = host.shell("dir")
              # 在PC端执行netstat命令读取回显结果, 设置超时时间为10秒
              echo = host.shell("netstat", timeout=10)
    """
    return run_command(cmd, timeout)


@checkepr
def check_true(value: bool, fail_msg: str = None):
    """
    @func 检查实际值是否为True，在不一致时抛出TestFailure异常
    @param value: 实际值
    @param fail_msg: 断言失败时打印的提示信息
    @example: # 检查a等于b
              host.check_true(a == b)
    """
    result = (value is True)
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
    return result


@checkepr
def check_equal(value: Any, expect: Any = True, fail_msg: str = None, expect_equal=True):
    """
    @func 检查实际值和期望值相等，在不一致时抛出TestFailure异常, 并打印fail_msg
    @param value: 实际值
    @param expect: 期望值
    @param fail_msg: 断言失败时打印的提示信息
    @param expect_equal: 是否期望相等(不建议使用, 建议直接使用host.check_not_equal)
    @example  # 检查a等于b
              host.check_equal(a, b, "a != b")
    """
    EXPECT("expect equal: %s, expect_value: %s" % (expect_equal, str(expect)))
    is_equal = (value == expect)
    result = (is_equal == expect_equal)
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 == {expect}条件")
    else:
        ACTUAL(f"value = {value}, 满足 == {expect}条件")
    return result


@checkepr
def check_not_equal(value: Any, expect: Any = True, fail_msg: str = None):
    """
    @func 检查实际值于预期值不等
    @param value: 实际值
    @param expect: 期望值
    @param fail_msg: 断言失败时打印的提示信息
    @example: # 检查a不等于b
              host.check_not_equal(a, b, "a == b")
    """
    result = (value != expect)
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 != {expect}条件")
    else:
        ACTUAL(f"value = {value}, 满足 != {expect}条件")
    return result


@checkepr
def check_greater(value: Any, expect: Any, fail_msg: str = None):
    """
    @func: 检查value是否大于expect, 不满足时抛出TestAssertionError异常
    @param: value: 实际值
    @param: expect: 期望值
    @param fail_msg: 断言失败时打印的提示信息
    @example: # 检查a大于b
              host.check_greater(a, b)
    """
    result = value > expect
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 > {expect}条件")
    else:
        ACTUAL(f"value = {value}, 满足 > {expect}条件")
    return result


@checkepr
def check_greater_equal(value: Any, expect: Any, fail_msg: str = None):
    """
    @func: 检查value是否大于等于expect, 不满足时抛出TestAssertionError异常
    @param: value: 实际值
    @param: expect: 期望值
    @param fail_msg: 断言失败时打印的提示信息
    @example: # 检查a大于等于b
              host.check_greater_equal(a, b)
    """
    result = value >= expect
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 >= {expect}条件")
    else:
        ACTUAL(f"value = {value}, 满足 >= {expect}条件")
    return result


@checkepr
def check_starts_with(value: str, expect: str, fail_msg: str = None):
    """
    @func: 检查实际值以期望值开头
    @example # 检查实际值以期望值开头
             host.check_starts_with(value, "发送到")
    """
    result = value.startswith(expect)
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 以 {expect} 开头条件")
    else:
        ACTUAL(f"value = {value}, 满足 以 {expect} 开头条件")
    return result


@checkepr
def check_ends_with(value: str, expect: str, fail_msg: str = None):
    """
    @func: 检查实际值以期望值结尾
    @example # 检查实际值以期望值结尾
             host.check_ends_with(value, "广告")
    """
    result = value.endswith(expect)
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 以 {expect} 结尾 条件")
    else:
        ACTUAL(f"value = {value}, 满足 以 {expect} 结尾 条件")
    return result


@checkepr
def check_contains(value: str, expect: str, fail_msg: str = None):
    """
    @func: 检查实际值包含期望值
    @example # 检查实际值包含期望值
             host.check_ends_with(value, "发送")
    """
    result = expect in value
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 包含 {expect} 条件")
    else:
        ACTUAL(f"value = {value}, 满足 包含 {expect} 条件")
    return result


@checkepr
def check_less(value: Any, expect: Any, fail_msg: str = None):
    """
    @func 检查value是否小于expect, 不满足时抛出TestAssertionError异常
    @param value: 实际值
    @param expect: 期望值
    @param fail_msg: 断言失败时打印的提示信息
    @example  # 检查a小于b
              host.check_less(a, b)
    """
    result = value < expect
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 < {expect}条件")
    else:
        ACTUAL(f"value = {value}, 满足 < {expect}条件")
    return result


@checkepr
def check_less_equal(value: Any, expect: Any, fail_msg: str = None):
    """
    @func 检查value是否小于等于expect, 不满足时抛出TestAssertionError异常
    @param value: 实际值
    @param expect: 期望值
    @param fail_msg: 断言失败时打印的提示信息
    @example: # 检查a小于等于b
              host.check_less_equal(a, b)
    """
    result = value <= expect
    if not result:
        if fail_msg is not None:
            MESSAGE(fail_msg)
        ACTUAL(f"value = {value}, 不满足 <= {expect}条件")
    else:
        ACTUAL(f"value = {value}, 满足 <= {expect}条件")
    return result


@keyword
def datetime_to_timestamp(datetime: str) -> int:
    """
    @func      将输入的日期和时间转换为秒级时间戳
    @param     datetime: 日期和时间，格式为"年-月-日 时:分:秒", 例如"2022-11-12 11:12:15"
                         注意分号为英文分号
    @return   整数表示的系统时间戳，单位为秒
    @example  # 时间日期转换为时间戳
              timestamp = host.datetime_to_timestamp("2022-11-12 11:12:15")
    """
    return Time(datetime).to_timestamp()


@keyword
def timestamp_to_datetime(timestamp: int, is_ms=True):
    """
    @func      将毫秒时间戳转换为系统时间和日期
    @param     timestamp 时间戳
    @param     is_ms 时间戳是否为毫秒, False表示时间戳为秒
    @return:   日期和时间，格式为"年-月-日 时:分:秒", 例如"2022-11-12 11:12:15"
    @example: # 时间戳转换为日期和时间
              timestamp = host.timestamp_to_date(168545584455)
    """
    if is_ms:
        timestamp = int(timestamp / 1000)
    time_array = time.localtime(timestamp)
    return time.strftime("%Y-%m-%d %H:%M:%S", time_array)


@keyword
def unzip_file(file_path: str, output_dir: str):
    """
    @func 解压缩zip格式的压缩文件到指定目录
    @example # 解压缩test.zip文件到output_dir文件夹中
             host.unzip_file("test.zip", "output_dir")
    """
    # 创建解压目标文件夹
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 打开zip文件
    with zipfile.ZipFile(file_path, 'r') as f:
        # 解压所有文件到指定目录
        f.extractall(output_dir)


def get_resource_path(resource_file_path: str, isdir=False) -> str:
    from devicetest.utils import file_util
    return file_util.get_resource_path(resource_file_path, isdir)
