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
import threading
import time
import shutil

from xdevice import DeviceOsType
from xdevice import platform_logger
from xdevice import Plugin
from xdevice import get_plugin
from xdevice import IShellReceiver
from xdevice import exec_cmd
from xdevice import DeviceState

from ios.constants import UsbConst

DEFAULT_ENCODING = "ISO-8859-1"

INSTALL_TIMEOUT = 2 * 60 * 1000
DEFAULT_TIMEOUT = 40 * 1000

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 27015
LOG = platform_logger("Ios")


class IosMonitor:
    """
    A Device monitor.
    This monitor connects to the Device Connector, gets device and
    debuggable process information from it.
    """
    MONITOR_MAP = {}

    def __init__(self, host="127.0.0.1", port=None, device_connector=None):
        self.channel = dict()
        self.channel.setdefault("host", host)
        self.channel.setdefault("port", port)
        self.is_stop = False
        self.monitoring = False
        self.server = device_connector
        self.devices = []
        self.changed = True
        self.last_msg_len = 0

    @staticmethod
    def get_instance(host, port=None, device_connector=None):
        if host not in IosMonitor.MONITOR_MAP:
            monitor = IosMonitor(host, port, device_connector)
            IosMonitor.MONITOR_MAP[host] = monitor
            LOG.debug("IosMonitor map add host {}, map is {}".format
                      (host, IosMonitor.MONITOR_MAP))

        return IosMonitor.MONITOR_MAP[host]

    def start(self):
        """
        Starts the monitoring.
        """
        if not shutil.which(UsbConst.connector_ace) or not shutil.which(
                UsbConst.connector_ios_deploy) or not shutil.which(UsbConst.connector_idevice_id):
            return
        try:
            LOG.debug("IosMonitor usb type is {}".format(self.server.usb_type))
            server_thread = threading.Thread(target=self.loop_monitor,
                                             name="IosMonitor", args=())
            server_thread.daemon = True
            server_thread.start()
        except FileNotFoundError as _:
            LOG.error("IosMonitor can't find connector, init device "
                      "environment failed!")

    def stop(self):
        """
        Stops the monitoring.
        """
        for host in IosMonitor.MONITOR_MAP:
            LOG.debug("IosMonitor stop host {}".format(host))
            monitor = IosMonitor.MONITOR_MAP[host]
            try:
                monitor.is_stop = True
            except Exception as _:
                LOG.error("IosMonitor close socket exception")
        IosMonitor.MONITOR_MAP.clear()
        LOG.debug("IosMonitor {} monitor stop!".format(IosHelper.CONNECTOR_NAME))
        LOG.debug("IosMonitor map is {}".format(IosMonitor.MONITOR_MAP))

    def loop_monitor(self):
        """
        Monitors the devices. This connects to the Debug Bridge
        """
        LOG.debug("current connector name is {}".format(IosHelper.CONNECTOR_NAME))
        while not self.is_stop:
            self.list_targets()
            time.sleep(1)

    def list_targets(self):
        data = exec_cmd([UsbConst.connector_idevice_id, "-l"])
        if self.last_msg_len != len(data):
            self.last_msg_len = len(data)
            self.changed = True
        else:
            self.changed = False
        self.process_incoming_target_data(data)

    def process_incoming_target_data(self, data):
        local_array_list = []
        if data:
            lines = data.split('\n')
            for line in lines:
                items = line.strip().split('\t')
                # Example: udid
                device_instance = self._get_device_instance(items, DeviceOsType.ios)
                local_array_list.append(device_instance)
        self.update_devices(local_array_list)

    def update_devices(self, param_array_list):
        devices = [item for item in self.devices]
        devices.reverse()
        for local_device1 in devices:
            k = 0
            for local_device2 in param_array_list:
                if local_device1.device_sn == local_device2.device_sn and \
                        local_device1.device_os_type == \
                        local_device2.device_os_type:
                    k = 1
                    if local_device1.device_state != \
                            local_device2.device_state:
                        local_device1.device_state = local_device2.device_state
                        self.server.device_changed(local_device1)
                    param_array_list.remove(local_device2)
                    break

            if k == 0:
                self.devices.remove(local_device1)
                self.server.device_disconnected(local_device1)
        for local_device in param_array_list:
            self.devices.append(local_device)
            self.server.device_connected(local_device)

    def _get_device_instance(self, items, os_type):
        device = get_plugin(plugin_type=Plugin.DEVICE, plugin_id=os_type)[0]
        device_instance = device.__class__()
        device_instance.__set_serial__(items[0])
        device_instance.host = self.channel.get("host")
        device_instance.port = self.channel.get("port")
        if self.changed:
            LOG.debug("Dmlib get device instance {}".format(device_instance.device_sn))
        device_instance.device_state = DeviceState.get_state("device")
        return device_instance


class IosHelper:
    CONNECTOR_NAME = ""

    @staticmethod
    def push_file(device, command, is_create=False, timeout=DEFAULT_TIMEOUT):
        return exec_cmd([UsbConst.connector_ios_deploy, "-i", device.device_sn] + command)

    @staticmethod
    def pull_file(device, command, is_create=False, timeout=DEFAULT_TIMEOUT):
        return exec_cmd([UsbConst.connector_ios_deploy, "-i", device.device_sn] + command)

    @staticmethod
    def install_package(device, package_file_path, ex_args):
        command = [UsbConst.connector_ios_deploy, "--id", device.device_sn, "--bundle", package_file_path]
        if ex_args:
            command.append(["--args", "\"{}\"".format(ex_args)])
        return exec_cmd(command)

    @staticmethod
    def uninstall_package(device, package_name):
        return exec_cmd([UsbConst.connector_ios_deploy, "--id", device.device_sn, "--uninstall_only", "--bundle_id", package_name])

    @staticmethod
    def reboot(device):
        return exec_cmd([UsbConst.connector_idevicediagnostics, "-u", device.device_sn, "restart"])

    @staticmethod
    def clear_crash_log(device):
        tmp_path = os.path.join(device.get_device_report_path(), "crash_tmp")
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)
        exec_cmd([UsbConst.connector_idevicecrashreport, "-u", device.device_sn, tmp_path])
        shutil.rmtree(tmp_path)

    @staticmethod
    def start_get_crash_log(device, file_name):
        crash_path = os.path.join(os.path.join(device.get_device_report_path(), "log"), file_name)
        if not os.path.exists(crash_path):
            os.mkdir(crash_path)
        exec_cmd([UsbConst.connector_idevicecrashreport, "-u", device.device_sn, crash_path])

    @staticmethod
    def execute_shell_command(device, command, timeout=DEFAULT_TIMEOUT, **kwargs):
        if isinstance(command, list):
            return exec_cmd([UsbConst.connector_ios_deploy, "--id", device.device_sn] + command)
        elif isinstance(command, str):
            return exec_cmd([UsbConst.connector_ios_deploy, "--id", device.device_sn] + command.split(" "))
        else:
            return False


class DeviceConnector(object):
    __instance = None
    __init_flag = False

    def __init__(self, host=None, port=None, usb_type=None):
        if DeviceConnector.__init_flag:
            return
        self.device_listeners = []
        self.device_monitor = None
        self.monitor_lock = threading.Condition()
        self.host = host if host else "127.0.0.1"
        self.usb_type = usb_type
        connector_name = "ios"
        IosHelper.CONNECTOR_NAME = connector_name
        if port:
            self.port = int(port)
        else:
            self.port = DEFAULT_PORT

    def start(self):
        self.device_monitor = IosMonitor.get_instance(
            self.host, self.port, device_connector=self)
        self.device_monitor.start()

    def terminate(self):
        if self.device_monitor:
            self.device_monitor.stop()
        self.device_monitor = None

    def add_device_change_listener(self, device_change_listener):
        self.device_listeners.append(device_change_listener)

    def remove_device_change_listener(self, device_change_listener):
        if device_change_listener in self.device_listeners:
            self.device_listeners.remove(device_change_listener)

    def device_connected(self, device):
        LOG.debug("DeviceConnector device connected:host {}, port {}, "
                  "device sn {} ".format(self.host, self.port, device.device_sn))
        if device.host != self.host or device.port != self.port:
            LOG.debug("DeviceConnector device error")
        for listener in self.device_listeners:
            listener.device_connected(device)

    def device_disconnected(self, device):
        LOG.debug("DeviceConnector device disconnected:host {}, port {}, "
                  "device sn {}".format(self.host, self.port, device.device_sn))
        if device.host != self.host or device.port != self.port:
            LOG.debug("DeviceConnector device error")
        for listener in self.device_listeners:
            listener.device_disconnected(device)

    def device_changed(self, device):
        LOG.debug("DeviceConnector device changed:host {}, port {}, "
                  "device sn {}".format(self.host, self.port, device.device_sn))
        if device.host != self.host or device.port != self.port:
            LOG.debug("DeviceConnector device error")
        for listener in self.device_listeners:
            listener.device_changed(device)


class CollectingOutputReceiver(IShellReceiver):
    def __init__(self):
        self.output = ""

    def __read__(self, output):
        self.output = "%s%s" % (self.output, output)

    def __error__(self, message):
        pass

    def __done__(self, result_code="", message=""):
        pass


class DisplayOutputReceiver(IShellReceiver):
    def __init__(self):
        self.output = ""
        self.unfinished_line = ""

    def _process_output(self, output, end_mark="\n"):
        content = output
        if self.unfinished_line:
            content = "".join((self.unfinished_line, content))
            self.unfinished_line = ""
        lines = content.split(end_mark)
        if content.endswith(end_mark):
            # get rid of the tail element of this list contains empty str
            return lines[:-1]
        else:
            self.unfinished_line = lines[-1]
            # not return the tail element of this list contains unfinished str,
            # so we set position -1
            return lines[:-1]

    def __read__(self, output):
        self.output = "%s%s" % (self.output, output)
        lines = self._process_output(output)
        for line in lines:
            line = line.strip()
            if line:
                LOG.info(line)

    def __error__(self, message):
        pass

    def __done__(self, result_code="", message=""):
        pass


def process_command_ret(ret, receiver):
    try:
        if ret != "" and receiver:
            receiver.__read__(ret)
            receiver.__done__()
    except Exception as error:
        LOG.exception("Error generating log report.", exc_info=False)
        raise error

    if ret != "" and not receiver:
        lines = ret.split("\n")
        for line in lines:
            line = line.strip()
            if line:
                LOG.debug(line)
