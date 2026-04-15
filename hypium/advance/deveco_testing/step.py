# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023. All rights reserved.


import threading
from typing import Any
import json
import os
import traceback
import time
from devicetest.core.test_case import Step as xdevice_step
from datetime import datetime
from hypium import UiDriver
from hypium.advance.deveco_testing.dvt_logger import DvtLogger, deveco_log
from devicetest.core.variables import DeccVariable
from hypium.advance.deveco_testing.utils import ThreadLocalVar
from .task_event_manager import TaskManager, TaskEventFactory, TaskEventListener


ThreadLocalVar.case_result = ("pass", None)


class TestCaseManager:
    testcases = []
    current = 0

    @classmethod
    def init(cls, testcase):
        cls.testcases = testcase
        cls.current = 0

    @classmethod
    def next_case(cls):
        cls.current += 1
        return cls.get_current_case()

    @classmethod
    def get_current_case(cls):
        if len(cls.testcases) > cls.current:
            return cls.testcases[cls.current]
        else:
            return None

    @classmethod
    def get_last_case(cls):
        if len(cls.testcases) >= 1:
            return cls.testcases[-1]
        else:
            return None


class IdGenerator():
    start_id = 0

    @classmethod
    def create_new_id(cls, ):
        IdGenerator.start_id += 1
        return IdGenerator.start_id


def _create_step_logger(log_path=None):
    """适配拨测服务1.0版本日志"""
    if log_path is None:
        log_path = DvtLogger.log_path
    return DvtLogger.get_logger("step", log_path)


class DevEcoTestingStep:
    mode = "deveco_testing"

    def __init__(self, testcase, name, desc=''):
        self.id = IdGenerator.create_new_id()
        self.name = name
        self.result = "running"  # fail
        self.start_time = ""
        self.end_time = ""
        self.desc = desc
        self.error_message = None
        self.case_id = testcase.__class__.__name__
        self.time_used = 0
        self.screenshot = []

        # 保存当前步骤所属的测试用例对象
        self._testcase = testcase
        self._start_timestamp = 0
        self._step_logger = None

    def log_step_start(self):
        """打印开始控制台日志"""
        self.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        self._start_timestamp = time.time()
        TaskManager.on_event(TaskEventFactory.create_step_start(
            self.name,
            self.id,
            self.desc
        ))
        if TaskManager.mode == 0:
            msg = "Step%s %s start, description: %s" % (self.id, self.name, self.desc)
            deveco_log.info(msg)
            self._add_process_log()

    def log_step_end(self, error_msg: str = None):
        """打印结束控制台日志"""
        self.time_used = time.time() - self._start_timestamp
        self.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        self.result = "pass" if error_msg is None or len(error_msg) == 0 else "fail"
        self.error_message = error_msg
        TaskManager.on_event(TaskEventFactory.create_step_end(
            self.name,
            self.id,
            self.result,
            self.error_message,
            self.screenshot
        ))
        if TaskManager.mode == 0:
            msg = "Step%s %s end, time used %.2f s, result: %s" % (self.id, self.name, self.time_used, self.result)
            if error_msg is not None:
                self.error_message = error_msg
                msg += ', error: ' + error_msg
                deveco_log.error(msg)
            else:
                deveco_log.info(msg)
            self._add_process_log()

    def __enter__(self):
        self.log_step_start()
        return self

    def to_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            data[key] = value
        return data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.result = "fail"
            # 如果with语句块中有异常抛出，则在这里处理异常
            error_message = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            self.error_message = error_message
        else:
            self.result = "pass"
        self.take_screenshot()
        self.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        self._update_result()
        if exc_type is not None:
            error_message = "%s(%s)" % (exc_type.__class__.__name__, str(exc_val))
        else:
            error_message = None
        self.log_step_end(error_message)

    def _create_drivers(self):
        if not hasattr(self._testcase, "drivers"):
            drivers = []
            for device in self._testcase.devices:
                drivers.append(UiDriver(device))
            setattr(self._testcase, "drivers", drivers)

    def _do_take_screenshot(self, screenshot_dir):
        for driver in self._testcase.drivers:
            timestamp = int(time.time() * 1000)
            screenshot_path = os.path.join(screenshot_dir, f"{driver.sn}_{timestamp}.jpeg")
            driver.capture_screen(screenshot_path)
            self.screenshot.append(screenshot_path)

    def _create_screenshot_dir(self):
        if TaskManager.mode == 0:
            # 应用拨测兼容
            if hasattr(self._testcase, "configs"):
                configs = self._testcase.configs
            else:
                configs = {}
            screenshot_dir = configs.get('screenshot_dir', 'screenshot')
        else:
            report_path = self._testcase.get_case_report_path()
            screenshot_dir = os.path.join(report_path, "screenshot")
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        return screenshot_dir

    def take_screenshot(self):
        # 从测试用例中读取参数
        if self._testcase is None:
            self._testcase = DeccVariable.cur_case().testcase
            if self._testcase is None:
                deveco_log.warning("No testcase, Fail to take screenshot")
                return
        screenshot_dir = self._create_screenshot_dir()
        self._create_drivers()
        self._do_take_screenshot(screenshot_dir)

    def _add_process_log(self):
        """应用拨测1.0使用"""
        if TaskManager.mode != 0:
            return
        if self._step_logger is None:
            self._step_logger = _create_step_logger()
        text = self._gen_log_text()
        self._step_logger.info(text)

    def _update_result(self):
        log_file = DvtLogger.log_path
        process_texts = []

        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                process_texts.append(line)

        row_index = self._find_row_index_by_step_id(process_texts)

        if row_index >= 0:
            del process_texts[row_index]
            new_text = self._gen_log_text()
            process_texts.insert(row_index, new_text)
            content = ''.join(process_texts)
            self._update_process_log(content)

    def _update_process_log(self, content):
        log_file = DvtLogger.log_path
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def _gen_log_text(self):
        step_json = json.dumps(self.to_dict(), ensure_ascii=False)
        return step_json

    def _find_row_index_by_step_id(self, process_texts):
        target = '"id": {},'.format(str(self.id))

        for i in range(len(process_texts) - 1, -1, -1):
            if target in process_texts[i]:
                return i

        return -1


def log_step_start(name, desc="", testcase=None):
    if testcase is None:
        current_step = DevEcoTestingStep(DeccVariable.cur_case().testcase, name, desc)
    else:
        current_step = DevEcoTestingStep(testcase, name, desc)
    current_step.log_step_start()
    ThreadLocalVar.current_step = current_step


def log_step_end(err_msg: str = None):
    if ThreadLocalVar.current_step is None:
        return
    current_step: DevEcoTestingStep = ThreadLocalVar.current_step
    try:
        current_step.take_screenshot()
    except Exception as e:
        deveco_log.warning("Fail to take screenshot: %s", str(e))
    current_step.log_step_end(err_msg)


def start_case_init_step():
    """应用拨测1.0兼容函数"""
    testcase = TestCaseManager.next_case()
    if testcase is not None:
        log_step_start("用例初始化", desc="用例%s初始化操作" % testcase.__class__.__name__, testcase=testcase)
    else:
        testcase = TestCaseManager.get_last_case()
        if testcase is not None:
            log_step_start("测试任务收尾工作", testcase=testcase)


def step_failed_callback(error: Exception):
    """用例失败回调"""
    ThreadLocalVar.case_result = ("fail", error)
    EndStep("%s(%s)" % (error.__class__.__name__, str(error)))


def case_end_callback(error=""):
    """用例完成回调"""
    EndStep(error)
    if TaskManager.mode == 0:
        start_case_init_step()


def register_callback():
    if DeccVariable.cur_case() is None:
        return
    testcase = DeccVariable.cur_case().testcase
    if hasattr(testcase, "execption_callback"):
        testcase.execption_callback = step_failed_callback
    if TaskManager.mode == 0:
        if hasattr(testcase, "case_end_callback"):
            testcase.case_end_callback = case_end_callback


def Step(name: str, desc: str = ""):
    """
    @func 描述一个步骤
    @param: name: 步骤名称
    @param: desc: 步骤详细描述
    @example: Step("输入100.123.123.123")
    """
    if DevEcoTestingStep.mode == "factory" or DvtLogger.log_path == "":
        xdevice_step(name)
        return
    # 事件通知模式, 0表示使用应用拨测1.0的日志格式, 1表示使用新模式
    register_callback()
    log_step_end()
    log_step_start(name, desc)


def EndStep(err_msg: str = None):
    """
    @func 标记一个步骤结束, 在用例结束时使用, 表示该用例后续没有步骤。默认情况下, 下一个Step开始时会自动结束上一个步骤，当本用例
          的所有步骤结束时, 需要调用该接口来表示最后一个步骤结束
    @param err_msg: 当前步骤失败原因, 设置为None表示步骤成功
    @example Step("回到桌面首页")
             # 该用例结束
             EndStep()
    """
    log_step_end(err_msg)
    ThreadLocalVar.current_step = None


# 兼容性符号
step_failed_call_back = step_failed_callback
step_finish_call_back = case_end_callback


def get_case_result():
    return ThreadLocalVar.case_result


if __name__ == '__main__':
    Step("hello")
    Step("hello2")
