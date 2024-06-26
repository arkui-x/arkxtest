#!/usr/bin/env python3
# coding=utf-8

#
# Copyright (c) 2020-2022 Huawei Device Co., Ltd.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import sys
import time

from _core.logger import platform_logger
from _core.report.reporter_helper import ExecInfo
from _core.report.reporter_helper import ReportConstant
from _core.report.result_reporter import ResultReporter
from _core.utils import is_python_satisfied

LOG = platform_logger("ReportMain")


def main_report():
    if not is_python_satisfied():
        return

    args = sys.argv
    if args is None or len(args) < 2:
        report_path = input("report path >>> ")
    else:
        report_path = args[1]

    exec_dir = os.getcwd()
    if not os.path.isabs(report_path):
        report_path = os.path.abspath(os.path.join(exec_dir, report_path))

    if not os.path.exists(report_path):
        LOG.error("Report path %s not exists", report_path)
        return

    LOG.info("Report path: %s", report_path)
    task_info = ExecInfo()
    task_info.platform = "None"
    task_info.test_type = "Test"
    task_info.device_name = "None"
    task_info.test_time = time.strftime(ReportConstant.time_format,
                                        time.localtime())
    result_report = ResultReporter()
    result_report.__generate_reports__(report_path, task_info=task_info)


if __name__ == "__main__":
    main_report()
