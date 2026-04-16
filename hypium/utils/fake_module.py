# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
#
# Description: 支持部分不存在的模块正常导入, 在调用时报告自定义错误

class FakeModule:
    """支持正常导入，在调用的时候报错"""
    def __init__(self, msg):
        self.msg = msg

    def __getattr__(self, item):
        raise RuntimeError(self.msg)

