# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.

import sys
from hypium.dfx.init_status_manager import main as hypium_extra_command_main
from xdevice.__main__ import main_process

if __name__ == "__main__":
    try:
        from hypium.advance.deveco_testing.dvt_step_info import register_task_event_listener
        register_task_event_listener()
    except Exception as e:
        print("TaskEvent listener is not installed")
    command_handled = False
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in ["init", "telemetry"]:
            hypium_extra_command_main()
            command_handled = True
        elif command in ["-h", "--help"]:
            help_info = hypium_extra_command_main(get_help_info=True)
            print(help_info)
    if not command_handled:
        main_process()
