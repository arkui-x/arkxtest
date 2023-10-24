#!/usr/bin/env python3
# coding=utf-8

#
# Copyright (c) 2022 Huawei Device Co., Ltd.
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
import platform
import shutil
import subprocess
import threading
import time

from xdevice import IDriver
from xdevice import Plugin
from xdevice import ConfigConst
from xdevice import check_result_report
from xdevice import get_device_log_file
from xdevice import ParamError
from xdevice import JsonParser
from xdevice import platform_logger
from xdevice import DeviceTestType
from xdevice import get_config_value
from xdevice import get_plugin
from xdevice import TestDescription
from xdevice import CommonParserType
from xdevice import ShellHandler
from xdevice import convert_serial
from xdevice import HdcError
from xdevice import ShellCommandUnresponsiveException
from xdevice import DeviceOsType
from xdevice import FilePermission
from xdevice import get_kit_instances
from xdevice import do_module_kit_setup
from xdevice import do_module_kit_teardown
from xdevice import disable_keyguard
from xdevice import ExecuteTerminate

__all__ = ["ARKUIXJSUnitTestDriver"]

LOG = platform_logger("ARKUIX")

TIME_OUT = 300 * 1000


@Plugin(type=Plugin.DRIVER, id=DeviceTestType.arkuix_jsunit_test)
class ARKUIXJSUnitTestDriver(IDriver):
    """
       ARKUIXJSUnitTestDriver is a Test that runs a native test package on
       given device.
    """

    def __init__(self):
        self.timeout = 80 * 1000
        self.start_time = None
        self.result = ""
        self.error_message = ""
        self.kits = []
        self.config = None
        self.runner = None
        self.rerun = True
        self.rerun_all = True
        # log
        self.device_log = None
        self.hi_log = None
        self.log_proc = None
        self.hilog_proc = None

    def __check_environment__(self, device_options):
        pass

    def __check_config__(self, config):
        pass

    def __execute__(self, request):
        try:
            LOG.debug("Start execute ARKUIX JSUnitTest")
            self.result = os.path.join(
                request.config.report_path, "result",
                '.'.join((request.get_module_name(), "xml")))
            self.config = request.config
            self.config.device = request.config.environment.devices[0]

            config_file = request.root.source.config_file
            suite_file = request.root.source.source_file

            if not suite_file:
                raise ParamError(
                    "test source '{}' not exists".format(request.root.source.source_string), error_no="00110")
            LOG.debug("Test case file path: {}".format(suite_file))
            self.config.device.set_device_report_path(request.config.report_path)
            self.config.device.device_log_collector.clear_crash_log()
            log_level = self.config.device_log.get(ConfigConst.tag_loglevel, "DEBUG")
            if self.config.device.device_os_type == DeviceOsType.ios:
                self.device_log = get_device_log_file(request.config.report_path,
                                                      "{}_{}".format(request.config.device.__get_serial__(),
                                                                     request.get_module_name()), "device_log")

                device_log_open = os.open(self.device_log, os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                                          FilePermission.mode_755)
                self.config.device.device_log_collector.add_log_address(self.device_log)
                with os.fdopen(device_log_open, "a") as device_log_file_pipe:
                    self.log_proc = self.config.device.device_log_collector.start_catch_device_log(
                        log_file_pipe=device_log_file_pipe)
                    self._run_arkuix_jsunit(config_file, request)
            else:
                self.hi_log = get_device_log_file(request.config.report_path,
                                                  request.config.device.__get_serial__(),
                                                  "device_hilog_{}".format(request.get_module_name()))
                hi_log_open = os.open(self.hi_log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, FilePermission.mode_755)
                self.device_log = get_device_log_file(request.config.report_path, self.config.device.__get_serial__(),
                                                      "device_log_{}".format(request.get_module_name()))
                device_log_open = os.open(self.device_log, os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                                          FilePermission.mode_755)
                with os.fdopen(hi_log_open, "a") as hilog_file_pipe, \
                        os.fdopen(device_log_open, "a") as device_log_file_pipe:
                    self.log_proc, self.hilog_proc = self.config.device.device_log_collector. \
                        start_catch_device_log(device_log_file_pipe, hilog_file_pipe, log_level=log_level)
                    self.config.device.device_log_collector.add_log_address(self.device_log, self.hi_log)
                    self._run_arkuix_jsunit(config_file, request)
        except Exception as exception:
            self.error_message = exception
            if not getattr(exception, "error_no", ""):
                setattr(exception, "error_no", "03409")
            LOG.exception(self.error_message, exc_info=True, error_no="03409")
            raise exception
        finally:
            try:
                self._handle_logs()
            finally:
                self.result = check_result_report(
                    request.config.report_path, self.result, self.error_message)

    def _run_arkuix_jsunit(self, config_file, request):
        try:
            if not os.path.exists(config_file):
                LOG.error("Error: Test cases don't exist {}.".format(config_file))
                raise ParamError(
                    "Error: Test cases don't exist {}.".format(config_file),
                    error_no="00102")
            json_config = JsonParser(config_file)
            self.runner = ARKUIXJSUnitTestRunner(self.config)
            self.kits = get_kit_instances(json_config,
                                          self.config.resource_path,
                                          self.config.testcases_path)
            self._get_driver_config(json_config)
            do_module_kit_setup(request, self.kits)
            self.runner.suites_name = request.get_module_name()
            if hasattr(self.config, "history_report_path") and self.config.testargs.get("test"):
                self._do_test_retry(request.listeners, self.config.testargs)
            else:
                if self.rerun:
                    self.runner.retry_times = self.runner.MAX_RETRY_TIMES
                # execute test case
                app_file = self.config.testargs.get("app_file")
                if app_file:
                    self._do_test_run(listener=request.listeners, path=app_file)
                else:
                    LOG.error("Not find ace test app file!")
                    raise ExecuteTerminate(error_msg="Not find ace test app file!")
        finally:
            do_module_kit_teardown(request)
            if self.runner.coverage_data:
                LOG.debug("Coverage data: {}".format(self.runner.coverage_data))

    def _get_driver_config(self, json_config):
        package = get_config_value('package-name',
                                   json_config.get_driver(), False)
        module = get_config_value('module-name',
                                  json_config.get_driver(), False)
        bundle = get_config_value('bundle-name',
                                  json_config.get_driver(), False)
        is_rerun = get_config_value('rerun', json_config.get_driver(), False)

        self.config.package_name = package
        self.config.module_name = module
        self.config.bundle_name = bundle
        self.rerun = True if is_rerun == 'true' else False

        if not package and not module:
            raise ParamError("Neither package nor module is found"
                             " in config file.", error_no="03201")
        timeout_config = get_config_value("test-timeout",
                                          json_config.get_driver(), False)
        if timeout_config:
            self.config.timeout = int(timeout_config)
        else:
            self.config.timeout = TIME_OUT

    def _do_test_retry(self, listener, testargs):
        tests_dict = dict()
        case_list = list()
        for test in testargs.get("test"):
            test_item = test.split("#")
            if len(test_item) != 2:
                continue
            case_list.append(test)
            if test_item[0] not in tests_dict:
                tests_dict.update({test_item[0]: []})
            tests_dict.get(test_item[0]).append(
                TestDescription(test_item[0], test_item[1]))
        self.runner.add_arg("class", ",".join(case_list))
        self.runner.expect_tests_dict = tests_dict
        self.config.testargs.pop("test")
        self.runner.run(listener, self.config.testargs.get("app_file"))
        self.runner.notify_finished()

    def _do_test_run(self, listener, path):
        self.runner.run(listener, path)
        self.runner.notify_finished()

    def _handle_logs(self):
        serial = "crash_log_{}_{}".format(str(self.config.device.__get_serial__()), time.time_ns())
        log_tar_file_name = "{}".format(str(serial).replace(":", "_"))
        self.config.device.device_log_collector.start_get_crash_log(log_tar_file_name)
        if self.config.device.device_os_type == DeviceOsType.ios:
            self.config.device.device_log_collector.remove_log_address(self.device_log)
        else:
            self.config.device.device_log_collector.remove_log_address(self.device_log, self.hi_log)
            self.config.device.device_log_collector.stop_catch_device_log(self.hilog_proc)
        self.config.device.device_log_collector.stop_catch_device_log(self.log_proc)

    def __result__(self):
        return self.result if os.path.exists(self.result) else ""


class ARKUIXJSUnitTestRunner:
    MAX_RETRY_TIMES = 3

    def __init__(self, config):
        self.arg_list = {}
        self.suites_name = None
        self.config = config
        self.rerun_attemp = 3
        self.suite_recorder = {}
        self.finished = False
        self.expect_tests_dict = dict()
        self.finished_observer = None
        self.retry_times = 1
        self.compile_mode = ""
        self.coverage_data = ""

    def run(self, listener, path):
        handler = self._get_shell_handler(listener)
        command = self._get_run_command(self.config.device)
        self.execute_arkuix_command(self.config.device, command, timeout=self.config.timeout, receiver=handler, retry=0,
                                    path=path)

    @staticmethod
    def execute_arkuix_command(device, command, timeout=TIME_OUT, receiver=None, **kwargs):
        if not shutil.which("ace"):
            raise HdcError(error_msg="Can not find acetools, please check.")
        stop_event = threading.Event()
        path = kwargs.get("path", None)
        output_flag = kwargs.get("output_flag", True)
        run_command = command + ["--timeout", str(timeout)] + ["-d", device.device_sn] + ["--path", path]
        try:
            if device.device_os_type == DeviceOsType.aosp:
                disable_keyguard(device)
            if output_flag:
                LOG.info(" ".join(run_command))
            else:
                LOG.debug(" ".join(run_command))
            if platform.system() == "Windows":
                proc = subprocess.Popen(["C:\\Windows\\System32\\cmd.exe", "/c", " ".join(run_command)],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                                        shell=False)
                proc.stdin.write(b"\r\n")
            else:
                proc = subprocess.Popen(run_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
            timeout_thread = threading.Thread(target=ARKUIXJSUnitTestRunner.kill_proc, args=(proc, timeout, stop_event))
            timeout_thread.daemon = True
            timeout_thread.start()
            while True:
                output = proc.stdout.readline()
                if b'Test failed' in output or b'test failed' in output:
                    raise ExecuteTerminate(error_msg="Test failed!")
                if output == b'' and proc.poll() is not None:
                    break
                if output and b'OHOS_REPORT' in output:
                    if receiver:
                        receiver.__read__(output.strip().decode('utf-8') + "\n")
                    else:
                        LOG.debug(output.strip().decode('utf-8'))
            if stop_event.is_set():
                device.log.error(
                    "ShellCommandUnresponsiveException: {} command {}".format(convert_serial(device.device_sn),
                                                                              run_command))
                LOG.exception("execute timeout!", exc_info=False)
                raise ShellCommandUnresponsiveException(error_msg="execute timeout!")
        except Exception as error:
            device.log.error("execute_arkuix_command exception: {} command {}".format(
                convert_serial(device.device_sn), run_command))
            LOG.exception(error, exc_info=False)
            raise ExecuteTerminate(error_msg="execute_arkuix_command exception, reason: {}".format(error)) from error
        finally:
            stop_event.set()
            if receiver:
                receiver.__done__()

    @staticmethod
    def kill_proc(proc, timeout, stop_event):
        # test-timeout单位用的是毫秒
        end_time = time.time() + int(timeout / 1000)
        while time.time() < end_time and not stop_event.is_set():
            time.sleep(1)
        if proc.poll() is None:
            proc.kill()
            stop_event.set()

    def notify_finished(self):
        if self.finished_observer:
            self.finished_observer.notify_task_finished()
        self.retry_times -= 1

    def _get_shell_handler(self, listener):
        parsers = get_plugin(Plugin.PARSER, CommonParserType.oh_jsunit)
        if parsers:
            parsers = parsers[:1]
        parser_instances = []
        for parser in parsers:
            parser_instance = parser.__class__()
            parser_instance.suites_name = self.suites_name
            parser_instance.listeners = listener
            parser_instance.runner = self
            parser_instances.append(parser_instance)
            self.finished_observer = parser_instance
        handler = ShellHandler(parser_instances)
        return handler

    def add_arg(self, name, value):
        if not name or not value:
            return
        self.arg_list[name] = value

    def remove_arg(self, name):
        if not name:
            return
        if name in self.arg_list:
            del self.arg_list[name]

    def _get_run_command(self, device):
        if device.device_os_type == DeviceOsType.ios:
            test_product = "ios"
        else:
            test_product = "apk"
        command = ["ace", "test", test_product, "--b", self.config.bundle_name, "--m", self.config.module_name,
                   "--unittest", "OpenHarmonyTestRunner", "--skipInstall"]
        return command
