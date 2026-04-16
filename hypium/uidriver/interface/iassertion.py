#!/usr/bin/env python
# Copyright (c) 2023 Huawei Device Co., Ltd.
from typing import Any
from abc import ABC, abstractmethod


class IAssert(ABC):
    
    @abstractmethod
    def is_true(self, actual: bool, fail_msg: str = None):
        """
        @func: 检查实际值和期望值相等
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example: # 检查实际值和期望值相等
                  driver.Assert.is_true(actual, True)
        """
        pass

    @abstractmethod
    def equal(self, actual: Any, expect: Any = True, fail_msg: str = None):
        """
        @func: 检查实际值和期望值相等
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example: # 检查实际值和期望值相等
                  driver.Assert.equal(actual, "a")
        """
        pass

    @abstractmethod
    def not_equal(self, actual: Any, expect: Any = True, fail_msg: str = None):
        """
        @func: 检查实际值于预期值不等
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example: # 检查实际值和期望值不相等
                  driver.Assert.not_equal(actual, "a")
        """
        pass

    @abstractmethod
    def starts_with(self, actual: str, expect: str, fail_msg: str = None):
        """
        @func: 检查实际值以期望值开头
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值以期望值开头
                 driver.Assert.starts_with(actual, "发送到")
        """
        pass

    @abstractmethod
    def ends_with(self, actual: str, expect: str, fail_msg: str = None):
        """
        @func 检查实际值以期望值结尾
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值以期望值结尾
                 driver.Assert.ends_with(actual, "广告")
        """
        pass

    @abstractmethod
    def contains(self, actual: str, expect: str, fail_msg: str = None):
        """
        @func: 检查实际值包含期望值
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值包含期望值
                 driver.Assert.ends_with(actual, "发送")
        """
        pass

    @abstractmethod
    def greater(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否大于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值大于期望值
                 driver.Assert.greater(actual, 100)
        """
        pass

    @abstractmethod
    def greater_equal(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否大于等于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值大于期望值
                 driver.Assert.greater_equal(actual, 100)
        """
        pass

    @abstractmethod
    def match_regexp(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否匹配正则表达式expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值匹配期望的正则表达式
                 driver.Assert.match_regexp(actual, r"星期.+")
        """
        pass

    @abstractmethod
    def less(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否小于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值小于期望值
                 driver.Assert.less_equal(actual, 100)
        """
        pass

    @abstractmethod
    def less_equal(self, actual: Any, expect: Any, fail_msg: str = None):
        """
        @func: 检查actual是否小于等于expect, 不满足时抛出TestAssertionError异常
        @param: actual: 实际值
        @param: expect: 期望值
        @param: fail_msg: 检查失败时打印的内容
        @example # 检查实际值小于等于期望值
                 driver.Assert.less_equal(actual, 100)
        """
        pass

