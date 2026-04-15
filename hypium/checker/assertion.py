#!/usr/bin/env python
# Copyright (c) 2023 Huawei Device Co., Ltd.

import re
from devicetest.core.test_case import checkepr, MESSAGE, ACTUAL
from hypium.exception import *
from hypium.action.device.uidriver import AwBase


class Assert(AwBase):
    """
    基础断言操作, 支持断言失败后自动截屏
    from hypium.checker import Assert
    """

    def __init__(self, driver):
        self._driver = driver

    @property
    def driver(self):
        return self._driver

    @checkepr
    def is_true(self, actual: bool, fail_msg: str = None):
        """
        @func: 检查实际值和期望值相等
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example: # 检查实际值和期望值相等
                  driver.Assert.is_true(actual, True)
        """
        result = actual
        if result is not True:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"实际值不为True")
        else:
            ACTUAL(f"实际值为True")
        return result

    @checkepr
    def equal(self, actual: Any, expect: Any = True, fail_msg: str = None):
        """
        @func: 检查实际值和期望值相等
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example: # 检查实际值和期望值相等
                  driver.Assert.equal(actual, "a")
        """
        result = (actual == expect)
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 == {expect}条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 == {expect}条件")
        return result

    @checkepr
    def not_equal(self, actual: Any, expect: Any = True, fail_msg: str = None):
        """
        @func: 检查实际值于预期值不等
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example: # 检查实际值和期望值不相等
                  driver.Assert.not_equal(actual, "a")
        """
        result = (actual != expect)
        if not result:
            MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 != {expect}条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 != {expect}条件")
        return result

    @checkepr
    def starts_with(self, actual: str, expect: str, fail_msg: str = None):
        """
        @func: 检查实际值以期望值开头
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值以期望值开头
                 driver.Assert.starts_with(actual, "发送到")
        """
        result = actual.startswith(expect)
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 以 {expect} 开头条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 以 {expect} 开头条件")
        return result

    @checkepr
    def ends_with(self, actual: str, expect: str, fail_msg: str = None):
        """
        @func 检查实际值以期望值结尾
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值以期望值结尾
                 driver.Assert.ends_with(actual, "广告")
        """
        result = actual.endswith(expect)
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 以 {expect} 结尾 条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 以 {expect} 结尾 条件")
        return result

    @checkepr
    def contains(self, actual: str, expect: str, fail_msg: str = None):
        """
        @func: 检查实际值包含期望值
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值包含期望值
                 driver.Assert.contains(actual, "发送")
        """
        result = expect in actual
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 包含 {expect} 条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 包含 {expect} 条件")
        return result

    @checkepr
    def greater(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否大于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值大于期望值
                 driver.Assert.greater(actual, 100)
        """
        result = actual > expect
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 > {expect}条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 > {expect}条件")
        return result

    @checkepr
    def greater_equal(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否大于等于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值大于期望值
                 driver.Assert.greater_equal(actual, 100)
        """
        result = actual >= expect
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 >= {expect}条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 >= {expect}条件")
        return result

    @checkepr
    def match_regexp(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否匹配正则表达式expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值匹配期望的正则表达式
                 driver.Assert.match_regexp(actual, r"星期.+")
        """
        result = re.search(expect, actual)
        if result is None:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 匹配正则表达式 {expect} 的条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 匹配正则表达式 {expect} 的条件")
        return True if result is not None else False

    @checkepr
    def less(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否小于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值小于期望值
                 driver.Assert.less(actual, 100)
        """
        result = actual < expect
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 < {expect}条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 < {expect}条件")
        return result

    @checkepr
    def less_equal(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否小于等于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值小于等于期望值
                 driver.Assert.less_equal(actual, 100)
        """
        result = actual <= expect
        if not result:
            if fail_msg is not None:
                MESSAGE(fail_msg)
            ACTUAL(f"actual = {actual}, 不满足 <= {expect}条件")
        else:
            ACTUAL(f"actual = {actual}, 满足 <= {expect}条件")
        return result

