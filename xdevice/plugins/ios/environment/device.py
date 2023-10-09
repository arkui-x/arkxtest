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

from ios.environment.dmlib import IosHelper
from ios.constants import UsbConst

__all__ = ["DeviceIos"]
TIMEOUT = 300 * 1000
RETRY_ATTEMPTS = 2
DEFAULT_UNAVAILABLE_TIMEOUT = 20 * 1000

LOG = platform_logger("DeviceIos")


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
            except Exception as error:
                self.log.error("error type: {}, error: {}".format
                               (error.__class__.__name__, error))
                callback_to_outer(self, "error:{}, prepare to recover".format(error))
                if not self.recover_device():
                    LOG.debug("Set device {} {} false".format(
                        self.device_sn, ConfigConst.recover_state))
                    self.set_recover_state(False)
                    callback_to_outer(self, "recover failed")
                    raise error
                exception = error
                callback_to_outer(self, "recover success")
        raise exception

    return device_action


@Plugin(type=Plugin.DEVICE, id=DeviceOsType.ios)
class DeviceIos(IDevice):
    """
    Class representing a device.

    Each object of this class represents one device in xDevice,

    Attributes:
        device_sn: A string that's the serial number of the device.
    """

    device_sn = None
    usb_type = UsbConst.connector_type
    test_device_state = None
    device_state_monitor = None
    device_log_proc = None
    label = None
    host = None
    port = None
    device_id = None
    _device_report_path = None
    log = platform_logger("DeviceIos")
    reboot_timeout = 2 * 60 * 1000
    device_os_type = DeviceOsType.ios
    device_allocation_state = DeviceAllocationState.available
    test_platform = Platform.ios
    _device_log_collector = None
    model_dict = {
        'default': ProductForm.phone,
        'tablet': ProductForm.tablet,
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

    def get_device_type(self):
        model = "default"
        product_type = exec_cmd([UsbConst.connector_ideviceinfo, "-u", self.device_sn, "-k", "ProductType"])
        if "iPhone" in product_type:
            model = "default"
        elif "iPad" in product_type:
            model = "tablet"
        self.label = self.model_dict.get(model, None)

    def get(self, key=None, default=None):
        if not key:
            return default
        value = getattr(self, key, None)
        if value:
            return value
        else:
            return self.extend_value.get(key, default)

    def set_device_report_path(self, path):
        self._device_report_path = path

    def get_device_report_path(self):
        return self._device_report_path

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

    @perform_device_action
    def execute_shell_command(self, command, timeout=TIMEOUT, **kwargs):
        return IosHelper.execute_shell_command(self, command, timeout=timeout, **kwargs)

    @perform_device_action
    def install_package(self, package_path, ex_args):
        if package_path is None:
            raise AppInstallError(
                "install package: package path cannot be None!")
        return IosHelper.install_package(self, package_path, ex_args)

    @perform_device_action
    def uninstall_package(self, package_name):
        return IosHelper.uninstall_package(self, package_name)

    @perform_device_action
    def push_file(self, local, remote, package_name=None, **kwargs):
        """
        Push a single file.
        The top directory won't be created if is_create is False (by default)
        and vice versa
        """
        if local is None:
            raise HdcError("XDevice Local path cannot be None!")
        command = []
        if package_name:
            command = ["--bundle_id", package_name, "--upload", local, "--to", remote]
        else:
            command = ["-f", "--upload", local, "--to", remote]
        is_create = kwargs.get("is_create", False)
        timeout = kwargs.get("timeout", TIMEOUT)
        return IosHelper.push_file(self, command, is_create=is_create, timeout=timeout)

    @perform_device_action
    def pull_file(self, remote, local, package_name=None, **kwargs):
        """
        Pull a single file.
        The top directory won't be created if is_create is False (by default)
        and vice versa
        """
        command = []

        if package_name:
            command.extend(["--bundle_id", package_name])
        else:
            command.append("-f")
        if pathlib.Path(remote).is_dir():
            command.extend(["--download={}".format(remote), "--to", local])
        else:
            command.extend(["-w{}".format(remote), "--to", local])

        is_create = kwargs.get("is_create", False)
        timeout = kwargs.get("timeout", TIMEOUT)
        return IosHelper.pull_file(self, command, is_create=is_create, timeout=timeout)

    def take_picture(self, name):
        pass

    def wait_for_device_not_available(self, wait_time):
        return self.device_state_monitor.wait_for_device_not_available(
            wait_time)

    def _wait_for_device_online(self, wait_time=None):
        return self.device_state_monitor.wait_for_device_online(wait_time)

    def _do_reboot(self):
        IosHelper.reboot(self)
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

    @property
    def device_log_collector(self):
        if self._device_log_collector is None:
            self._device_log_collector = DeviceLogCollector(self)
        return self._device_log_collector


class DeviceLogCollector:
    log_file_address = []
    device = None
    restart_log_proc = []

    def __init__(self, device):
        self.device = device

    def restart_catch_device_log(self):
        from xdevice import FilePermission
        for index, _ in enumerate(self.log_file_address):
            device_log_open = os.open(self.log_file_address[index], os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                                      FilePermission.mode_755)
            with os.fdopen(device_log_open, "a") as device_log_file_pipe:
                log_proc = self.start_catch_device_log(log_file_pipe=device_log_file_pipe)
                self.restart_log_proc.append(log_proc)

    def stop_restart_catch_device_log(self):
        # when device free stop restart log proc
        for _, proc in enumerate(self.restart_log_proc):
            self.stop_catch_device_log(proc)
        self.restart_log_proc.clear()
        self.log_file_address.clear()

    def start_catch_device_log(self, log_file_pipe=None):
        """
        Starts ios log for each device in separate subprocesses and save
        the logs in files.
        """
        device_log_proc = None
        if log_file_pipe:
            device_log_proc = start_standing_subprocess(self._syslog_cmd(), log_file_pipe)
        return device_log_proc

    def stop_catch_device_log(self, proc):
        """
        Stops all ios log subprocesses.
        """
        if proc:
            stop_standing_subprocess(proc)
            self.device.log.debug("Stop catch device log.")

    def _syslog_cmd(self):
        cmd = [UsbConst.connector_idevicesyslog, "-d", self.device.device_sn]
        return cmd

    def _get_log(self, log_cmd):
        pass

    def start_get_crash_log(self, file_name, **kwargs):
        IosHelper.start_get_crash_log(self.device, file_name)

    def clear_crash_log(self):
        IosHelper.clear_crash_log(self.device)

    def add_log_address(self, log_file_address):
        # record to restart catch log when reboot device
        if log_file_address:
            self.log_file_address.append(log_file_address)

    def remove_log_address(self, log_file_address):
        if log_file_address and log_file_address in self.log_file_address:
            self.log_file_address.remove(log_file_address)
