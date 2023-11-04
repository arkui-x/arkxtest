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

import pathlib
import os
import platform
import threading

from xdevice import DeviceOsType
from xdevice import AppInstallError
from xdevice import TestDeviceState
from xdevice import ProductForm
from xdevice import ReportException
from xdevice import IDevice
from xdevice import platform_logger
from xdevice import Plugin
from xdevice import exec_cmd
from xdevice import ConfigConst
from xdevice import HdcError
from xdevice import DeviceAllocationState
from xdevice import convert_serial
from xdevice import start_standing_subprocess
from xdevice import stop_standing_subprocess
from xdevice import Platform
from xdevice import DeviceConnectorType
from xdevice import check_path_legal

from aosp.environment.dmlib import AdbHelper
from aosp.environment.dmlib import CollectingOutputReceiver
from aosp.constants import UsbConst

__all__ = ["DeviceAosp"]
TIMEOUT = 300 * 1000
RETRY_ATTEMPTS = 2
DEFAULT_UNAVAILABLE_TIMEOUT = 20 * 1000
BACKGROUND_TIME = 2 * 60 * 1000

LOG = platform_logger("DeviceAosp")
LOGLEVEL = ["VERBOSE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]


def perform_device_action(func):
    def callback_to_outer(device, msg):
        # callback to decc ui
        if getattr(device, "callback_method", None):
            device.callback_method(msg)

    def device_action(self, *args, **kwargs):
        if not self.get_recover_state():
            LOG.debug("Device {} {} is false".format(self.device_sn,
                                                     ConfigConst.recover_state))
            return None
        # avoid infinite recursion, such as device reboot
        abort_on_exception = bool(kwargs.get("abort_on_exception", False))
        if abort_on_exception:
            result = func(self, *args, **kwargs)
            return result

        tmp = int(kwargs.get("retry", RETRY_ATTEMPTS))
        retry = tmp + 1 if tmp > 0 else 1
        exception = None
        for _ in range(retry):
            try:
                result = func(self, *args, **kwargs)
                return result
            except ReportException as error:
                self.log.exception("Generate report error!", exc_info=False)
                exception = error
            except (ConnectionResetError,
                    ConnectionRefusedError,
                    ConnectionAbortedError) as error:
                self.log.error("error type: {}, error: {}".format(error.__class__.__name__, error))
                if self.usb_type == DeviceConnectorType.hdc:
                    cmd = ["hdc", "reset"]
                    self.log.info("re-execute hdc reset")
                else:
                    cmd = [UsbConst.connector, "start-server"]
                    self.log.info("re-execute {}".format(cmd))
                exec_cmd(cmd)
                callback_to_outer(self, "error:{}, prepare to recover".format(error))
                if not self.recover_device():
                    LOG.debug("Set device {} {} false".format(self.device_sn, ConfigConst.recover_state))
                    self.set_recover_state(False)
                    callback_to_outer(self, "recover failed")
                    raise error
                exception = error
                callback_to_outer(self, "recover success")
            except HdcError as error:
                self.log.error("error type: {}, error: {}".format(error.__class__.__name__, error))
                callback_to_outer(self, "error:{}, prepare to recover".format(error))
                if not self.recover_device():
                    LOG.debug("Set device {} {} false".format(self.device_sn, ConfigConst.recover_state))
                    self.set_recover_state(False)
                    callback_to_outer(self, "recover failed")
                    raise error
                exception = error
                callback_to_outer(self, "recover success")
            except Exception as error:
                self.log.exception("error type: {}, error: {}".format(error.__class__.__name__, error), exc_info=False)
                exception = error
        raise exception

    return device_action


@Plugin(type=Plugin.DEVICE, id=DeviceOsType.aosp)
class DeviceAosp(IDevice):
    """
    Class representing a device.

    Each object of this class represents one device in xDevice,

    Attributes:
        device_sn: A string that's the serial number of the device.
    """

    device_sn = None
    host = None
    port = None
    usb_type = None
    is_timeout = False
    device_log_proc = None
    device_hilog_proc = None
    device_os_type = DeviceOsType.aosp
    test_device_state = None
    device_allocation_state = DeviceAllocationState.available
    label = None
    log = platform_logger("DeviceAosp")
    device_state_monitor = None
    reboot_timeout = 2 * 60 * 1000
    _device_log_collector = None
    _device_report_path = None
    test_platform = Platform.aosp
    device_id = None
    model_dict = {
        'default': ProductForm.phone,
        'car': ProductForm.car,
        'tv': ProductForm.television,
        'watch': ProductForm.watch,
        'tablet': ProductForm.tablet,
        'nosdcard': ProductForm.phone
    }

    def __init__(self):
        self.extend_value = {}
        self.device_lock = threading.RLock()
        self.forward_ports = []
        self.proxy_listener = None

    def __eq__(self, other):
        return self.device_sn == other.__get_serial__() and \
               self.device_os_type == other.device_os_type

    def __set_serial__(self, device_sn=""):
        self.device_sn = device_sn
        return self.device_sn

    def set_state(self, state):
        self.test_device_state = state

    def __get_serial__(self):
        return self.device_sn

    def get(self, key=None, default=None):
        if not key:
            return default
        value = getattr(self, key, None)
        if value:
            return value
        else:
            return self.extend_value.get(key, default)

    def recover_device(self):
        if not self.get_recover_state():
            LOG.debug("Device {} {} is false, cannot recover device".format(
                self.device_sn, ConfigConst.recover_state))
            return False

        LOG.debug("Wait device {} to recover".format(self.device_sn))
        result = self.device_state_monitor.wait_for_device_available(self.reboot_timeout)
        if result:
            self.device_log_collector.restart_catch_device_log()
        return result

    def get_device_type(self):
        model = self.get_property("ro.build.characteristics", abort_on_exception=True)
        self.label = self.model_dict.get(model, None)

    def get_property(self, prop_name, retry=RETRY_ATTEMPTS, abort_on_exception=False):
        """
        Hdc command, ddmlib function
        """
        command = "getprop {}".format(prop_name)
        stdout = self.execute_shell_command(command, timeout=5 * 1000, output_flag=False, retry=retry,
                                            abort_on_exception=abort_on_exception).strip()
        if stdout:
            LOG.debug(stdout)
        return stdout

    @perform_device_action
    def connector_command(self, command, **kwargs):
        timeout = int(kwargs.get("timeout", TIMEOUT)) / 1000
        error_print = bool(kwargs.get("error_print", True))
        join_result = bool(kwargs.get("join_result", False))
        timeout_msg = '' if timeout == 300.0 else " with timeout {}s".format(timeout)
        if self.usb_type == DeviceConnectorType.hdc:
            LOG.debug("{} execute command hdc {}{}".format(convert_serial(self.device_sn), command, timeout_msg))
            if self.host != "127.0.0.1":
                cmd = [AdbHelper.CONNECTOR_NAME, "-s", "{}:{}".format(self.host, self.port), "-t", self.device_sn]
            else:
                cmd = [AdbHelper.CONNECTOR_NAME, "-t", self.device_sn]
        else:
            LOG.debug("{} execute command {} {}{}".format(convert_serial(self.device_sn), UsbConst.connector, command,
                                                          timeout_msg))
            cmd = [UsbConst.connector, "-s", self.device_sn, "-H", self.host, "-P", str(self.port)]

        if isinstance(command, list):
            cmd.extend(command)
        else:
            command = command.strip()
            cmd.extend(command.split(" "))
        result = exec_cmd(cmd, timeout, error_print, join_result)
        if not result:
            return result
        for line in str(result).split("\n"):
            if line.strip():
                LOG.debug(line.strip())
        return result

    @perform_device_action
    def execute_shell_command(self, command, timeout=TIMEOUT, receiver=None, **kwargs):
        if not receiver:
            collect_receiver = CollectingOutputReceiver()
            AdbHelper.execute_shell_command(self, command, timeout=timeout, receiver=collect_receiver, **kwargs)
            return collect_receiver.output
        else:
            return AdbHelper.execute_shell_command(self, command, timeout=timeout, receiver=receiver, **kwargs)

    def execute_shell_cmd_background(self, command, timeout=TIMEOUT, receiver=None):
        status = AdbHelper.execute_shell_command(self, command, timeout=timeout, receiver=receiver)
        self.wait_for_device_not_available(DEFAULT_UNAVAILABLE_TIMEOUT)
        self.device_state_monitor.wait_for_device_available(BACKGROUND_TIME)
        cmd = "target mount" if self.usb_type == DeviceConnectorType.hdc else "remount"
        self.connector_command(cmd)
        self.device_log_collector.restart_catch_device_log()
        return status

    def wait_for_device_not_available(self, wait_time):
        return self.device_state_monitor.wait_for_device_not_available(wait_time)

    def _wait_for_device_online(self, wait_time=None):
        return self.device_state_monitor.wait_for_device_online(wait_time)

    def _do_reboot(self):
        AdbHelper.reboot(self)
        if not self.wait_for_device_not_available(DEFAULT_UNAVAILABLE_TIMEOUT):
            LOG.error(
                "Did not detect device {} becoming unavailable after reboot".format(convert_serial(self.device_sn)))

    def _reboot_until_online(self):
        self._do_reboot()
        self._wait_for_device_online()

    def reboot(self):
        self._reboot_until_online()
        self.device_state_monitor.wait_for_device_available(self.reboot_timeout)
        self.device_log_collector.restart_catch_device_log()

    @perform_device_action
    def install_package(self, package_path, command=""):
        if package_path is None:
            raise HdcError(
                "install package: package path cannot be None!")
        # 临时规避push方案在macos上推送失败，导致安装失败的问题
        if platform.system() == "Darwin":
            result = self.connector_command("install {} {}".format(command, package_path))
            if "error" in result:
                LOG.error("exception {}".format(result))
                raise HdcError(result)
            return result
        else:
            return AdbHelper.install_package(self, package_path, command)

    @perform_device_action
    def uninstall_package(self, package_name):
        return AdbHelper.uninstall_package(self, package_name)

    @perform_device_action
    def push_file(self, local, remote, **kwargs):
        """
        Push a single file.
        The top directory won't be created if is_create is False (by default)
        and vice versa
        """
        if local is None:
            raise HdcError("XDevice Local path cannot be None!")
        remote_is_dir = kwargs.get("remote_is_dir", False)
        if remote_is_dir:
            ret = self.execute_shell_command("test -d {} && echo 0".format(remote))
            if not (ret != "" and len(str(ret).split()) != 0 and str(ret).split()[0] == "0"):
                self.execute_shell_command("mkdir -p {}".format(remote))

        # 临时规避push方案在macos上推送失败
        if platform.system() == "Darwin":
            result = self.connector_command("push {} {}".format(local, remote))
            if "error" in result:
                LOG.error("exception {}".format(result))
                raise HdcError(result)
        else:
            is_create = kwargs.get("is_create", False)
            timeout = kwargs.get("timeout", TIMEOUT)
            AdbHelper.push_file(self, local, remote, is_create=is_create, timeout=timeout)
        if not self.is_file_exist(remote):
            LOG.error("Push {} to {} failed".format(local, remote))
            raise HdcError("push {} to {} failed".format(local, remote))

    @perform_device_action
    def pull_file(self, remote, local, **kwargs):
        """
        Pull a single file.
        The top directory won't be created if is_create is False (by default)
        and vice versa
        """
        is_create = kwargs.get("is_create", False)
        timeout = kwargs.get("timeout", TIMEOUT)
        AdbHelper.pull_file(self, remote, local, is_create=is_create, timeout=timeout)

    def is_directory(self, path):
        path = check_path_legal(path)
        output = self.execute_shell_command("ls -ld {}".format(path))
        if output and output.startswith('d'):
            return True
        return False

    def is_file_exist(self, file_path):
        file_path = check_path_legal(file_path)
        output = self.execute_shell_command("ls {}".format(file_path))
        if output and "No such file or directory" not in output:
            return True
        return False

    def get_recover_result(self, retry=RETRY_ATTEMPTS):
        command = "getprop dev.bootcomplete"
        try:
            stdout = self.execute_shell_command(command, timeout=5 * 1000, output_flag=False, retry=retry,
                                                abort_on_exception=True).strip()
            if stdout:
                LOG.debug(stdout)
        except HdcError as error:
            self.device.log.error("get_recover_result exception: {}".format(error))
            if self.usb_type == DeviceConnectorType.hdc:
                cmd = ["hdc", "list", "targets"]
            else:
                cmd = [UsbConst.connector, "devices"]
            result = exec_cmd(cmd)
            LOG.debug("exec_cmd result: {}, current device_sn: {}".format(result, self.device_sn))
            if self.device_sn in result:
                stdout = "1"
            else:
                stdout = "0"
        return stdout

    def set_recover_state(self, state):
        with self.device_lock:
            setattr(self, ConfigConst.recover_state, state)
            if not state:
                self.test_device_state = TestDeviceState.NOT_AVAILABLE
                self.device_allocation_state = DeviceAllocationState.unavailable

    def get_recover_state(self, default_state=True):
        with self.device_lock:
            state = getattr(self, ConfigConst.recover_state, default_state)
            return state

    def set_device_report_path(self, path):
        self._device_report_path = path

    def get_device_report_path(self):
        return self._device_report_path

    @classmethod
    def check_recover_result(cls, recover_result):
        return "1" == recover_result

    def take_picture(self, name):
        pass

    @property
    def device_log_collector(self):
        if self._device_log_collector is None:
            self._device_log_collector = DeviceLogCollector(self)
        return self._device_log_collector


class DeviceLogCollector:
    hilog_file_address = []
    log_file_address = []
    device = None
    restart_hilog_proc = []
    restart_log_proc = []
    device_log_level = None

    def __init__(self, device):
        self.device = device

    def restart_catch_device_log(self):
        if len(self.hilog_file_address) != len(self.log_file_address):
            self.device.log.warning("hilog address not equals to log address.")
            return
        from xdevice import FilePermission
        for index, _ in enumerate(self.log_file_address):
            hilog_open = os.open(self.hilog_file_address[index], os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                                 FilePermission.mode_755)
            device_log_open = os.open(self.log_file_address[index], os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                                      FilePermission.mode_755)
            with os.fdopen(hilog_open, "a") as hilog_file_pipe, \
                    os.fdopen(device_log_open, "a") as device_log_file_pipe:
                log_proc, hilog_proc = self.start_catch_device_log(log_file_pipe=device_log_file_pipe,
                                                                   hilog_file_pipe=hilog_file_pipe, clear_log=False)
                self.restart_hilog_proc.append(hilog_proc)
                self.restart_log_proc.append(log_proc)

    def stop_restart_catch_device_log(self):
        # when device free stop restart log proc
        for _, proc in enumerate(self.restart_hilog_proc):
            self.stop_catch_device_log(proc)
        for _, proc in enumerate(self.restart_log_proc):
            self.stop_catch_device_log(proc)
        self.restart_hilog_proc.clear()
        self.restart_log_proc.clear()
        self.hilog_file_address.clear()
        self.log_file_address.clear()

    def start_catch_device_log(self, log_file_pipe=None, hilog_file_pipe=None, clear_log=True, **kwargs):
        """
        Starts hdc log for each device in separate subprocesses and save
        the logs in files.
        """
        # 设置日志级别
        if not self.device_log_level:
            log_level = kwargs.get("log_level", "DEBUG")
            if log_level not in LOGLEVEL:
                self.device_log_level = "DEBUG"
            else:
                self.device_log_level = log_level

        device_log_proc = None
        device_hilog_proc = None
        if log_file_pipe:
            if clear_log:
                self.device.execute_shell_command("logcat -c")
            self.device.execute_shell_command("setprop persist.log.tag {}".format(self.device_log_level))
            command = ["logcat", "-v", "threadtime"]
            device_log_proc = start_standing_subprocess(self._common_cmd(command), log_file_pipe)
        if hilog_file_pipe:
            if clear_log:
                self.device.execute_shell_command("hilogcat -c")
            self.device.execute_shell_command("setprop persist.hilog.tag {}".format(self.device_log_level))
            command = ["hilogcat"]
            device_hilog_proc = start_standing_subprocess(self._common_cmd(command), hilog_file_pipe)
        return device_log_proc, device_hilog_proc

    def stop_catch_device_log(self, proc):
        """
        Stops all hdc log subprocesses.
        """
        if proc:
            stop_standing_subprocess(proc)
            self.device.log.debug("Stop catch device log.")

    def _common_cmd(self, command=None):
        if self.device.usb_type == DeviceConnectorType.hdc:
            if self.device.host != "127.0.0.1":
                cmd = [AdbHelper.CONNECTOR_NAME, "-s", "{}:{}".format(self.device.host, self.device.port), "-t",
                       self.device.device_sn, "shell"] + command
            else:
                cmd = [AdbHelper.CONNECTOR_NAME, "-t", self.device.device_sn, "shell"] + command
        else:
            cmd = [UsbConst.connector, "-s", self.device.device_sn, "-H", self.device.host, "-P", str(self.device.port),
                   "shell"] + command
        return cmd

    def _get_log(self, log_cmd):
        data_list = list()
        log_name_array = list()
        log_result = self.device.execute_shell_command(log_cmd)
        if log_result is not None and len(log_result) != 0:
            log_name_array = log_result.strip().replace("\r", "").split("\n")
        for log_name in log_name_array:
            log_name = log_name.strip()
            data_list.append(log_name)
        return data_list

    def start_get_crash_log(self, task_name, **kwargs):
        log_array = self._get_log("ls /data/log/faultlog/faultlogger")
        self.device.log.debug("crash log file list is {}".format(log_array))
        if len(log_array) <= 0:
            return
        module_name = kwargs.get("module_name", None)
        if module_name:
            log_path = "{}/log/{}/crash_log_{}/".format(self.device.get_device_report_path(), module_name, task_name)
        else:
            log_path = "{}/log/crash_log_{}/".format(self.device.get_device_report_path(), task_name)
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        self.device.pull_file("/data/log/faultlog/faultlogger", log_path)

    def clear_crash_log(self):
        clear_faultlog_crash_cmd = "rm -f /data/log/faultlog/faultlogger/*"
        self.device.execute_shell_command(clear_faultlog_crash_cmd)

    def add_log_address(self, log_file_address, hilog_file_address):
        # record to restart catch log when reboot device
        if log_file_address:
            self.log_file_address.append(log_file_address)
        if hilog_file_address:
            self.hilog_file_address.append(hilog_file_address)

    def remove_log_address(self, log_file_address, hilog_file_address):
        if log_file_address and log_file_address in self.log_file_address:
            self.log_file_address.remove(log_file_address)
        if hilog_file_address and hilog_file_address in self.hilog_file_address:
            self.hilog_file_address.remove(hilog_file_address)

    def pull_extra_log_files(self, task_name, module_name, dirs: str):
        if dirs is None:
            return
        dir_list = dirs.split(";")
        for dir_path in dir_list:
            extra_log_path = "{}/log/{}/{}_extra_log/".format(self.device.get_device_report_path(), module_name,
                                                              task_name)
            self.device.pull_file(dir_path, extra_log_path)
