# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.


class Shell:
    def __init__(self, device):
        self.device = device

    def get_os(self):
        device_class_type = type(self.device).__name__
        if device_class_type == "Device":
            return "ohos"
        else:
            return "Unknown"

    def cmd(self, cmd_str) -> str:
        return self.device.connector_command(cmd_str)

    def execute(self, shell_str) -> str:
        return self.device.execute_shell_command(shell_str)

