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
import socket
import struct
import threading
import time
import shutil
import stat
from dataclasses import dataclass

from xdevice import DeviceOsType
from xdevice import ParamError
from xdevice import ReportException
from xdevice import ExecuteTerminate
from xdevice import platform_logger
from xdevice import Plugin
from xdevice import get_plugin
from xdevice import IShellReceiver
from xdevice import exec_cmd
from xdevice import get_file_absolute_path
from xdevice import FilePermission
from xdevice import DeviceError
from xdevice import HdcError
from xdevice import HdcCommandRejectedException
from xdevice import ShellCommandUnresponsiveException
from xdevice import DeviceState
from xdevice import DeviceConnectorType
from xdevice import convert_serial
from xdevice import is_proc_running
from xdevice import convert_ip
from xdevice import create_dir

from aosp.constants import UsbConst

ID_OKAY = b'OKAY'
ID_FAIL = b'FAIL'
ID_STAT = b'STAT'
ID_RECV = b'RECV'
ID_DATA = b'DATA'
ID_DONE = b'DONE'
ID_SEND = b'SEND'
ID_LIST = b'LIST'
ID_DENT = b'DENT'

DEFAULT_ENCODING = "ISO-8859-1"
SYNC_DATA_MAX = 64 * 1024
REMOTE_PATH_MAX_LENGTH = 1024
SOCK_DATA_MAX = 256

INSTALL_TIMEOUT = 2 * 60 * 1000
DEFAULT_TIMEOUT = 40 * 1000

MAX_CONNECT_ATTEMPT_COUNT = 10
DATA_UNIT_LENGTH = 4
HEXADECIMAL_NUMBER = 16
SPECIAL_FILE_MODE = 41471
FORMAT_BYTES_LENGTH = 4
DEFAULT_OFFSET_OF_INT = 4

INVALID_MODE_CODE = -1
DEFAULT_PORT = 5037
HDC_NAME = "hdc"
LOG = platform_logger("Adb")


class AdbMonitor:
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
        self.main_adb_connection = None
        self.connection_attempt = 0
        self.is_stop = False
        self.monitoring = False
        self.server = device_connector
        self.devices = []
        self.hdc_version = None

    @staticmethod
    def get_instance(host, port=None, device_connector=None):
        if host not in AdbMonitor.MONITOR_MAP:
            monitor = AdbMonitor(host, port, device_connector)
            AdbMonitor.MONITOR_MAP[host] = monitor
            LOG.debug("AdbMonitor map add host {}, map is {}".format
                      (host, AdbMonitor.MONITOR_MAP))

        return AdbMonitor.MONITOR_MAP[host]

    def start(self):
        """
        Starts the monitoring.
        """
        try:
            LOG.debug("AdbMonitor usb type is {}".format(self.server.usb_type))
            if self.server.usb_type == DeviceConnectorType.hdc and shutil.which(HDC_NAME):
                # 先停止ADB,因为ADB与HDC有冲突
                self.stop_adb(UsbConst.connector)
                AdbHelper.CONNECTOR_NAME = HDC_NAME
                self.init_hdc(AdbHelper.CONNECTOR_NAME)
            else:
                self.stop_adb(HDC_NAME)
                AdbHelper.CONNECTOR_NAME = UsbConst.connector
                if not is_proc_running(UsbConst.connector):
                    self.start_adb(connector=UsbConst.connector,
                                   local_port=self.channel.setdefault("port", DEFAULT_PORT))
                    time.sleep(1)
            server_thread = threading.Thread(target=self.loop_monitor, name="AdbMonitor", args=())
            server_thread.daemon = True
            server_thread.start()
        except FileNotFoundError as _:
            LOG.error("AdbMonitor can't find connector, init device environment failed!")

    def init_hdc(self, connector_name=HDC_NAME):
        env_hdc = shutil.which(connector_name)
        # if not, add xdevice's own hdc path to environ path.
        # tell if hdc has already been in the environ path.
        if env_hdc is None:
            LOG.debug("AdbMonitor can't find HDC, try to find ADB.")
            # use adb
            if shutil.which(UsbConst.connector) is not None:
                connector_name = UsbConst.connector
            else:
                LOG.error("AdbMonitor can't find HDC or ADB, init device environment failed!")
                return
        if not is_proc_running(connector_name, HDC_NAME):
            port = DEFAULT_PORT
            self.start_adb(connector=connector_name, local_port=self.channel.setdefault("port", port))
            time.sleep(1)

    def stop_adb(self, connector="adb"):
        """
        Starts the hdc host side server.
        """
        if shutil.which(HDC_NAME) is not None:
            self.hdc_version = exec_cmd([HDC_NAME, "-v"], error_print=False)
            LOG.debug("AdbMonitor {} version: {}".format(HDC_NAME, self.hdc_version))
        if self.hdc_version and "Ver:" in self.hdc_version:
            LOG.debug("The connector is normalized version, so does not need to be killed.")
            return

        if connector.startswith(HDC_NAME):
            if is_proc_running(connector):
                try:
                    LOG.debug("AdbMonitor {} kill".format(connector))
                    exec_cmd([connector, "kill"])
                except ParamError as error:
                    LOG.debug("AdbMonitor {} kill error: {}".format(connector, error))
                except FileNotFoundError as _:
                    LOG.warning("Cannot kill {} process, please close it manually!".format(connector))
        else:
            if is_proc_running(UsbConst.connector):
                LOG.debug("AdbMonitor {}".format(UsbConst.kill_server))
                exec_cmd([UsbConst.connector, "kill-server"])

    def stop(self):
        """
        Stops the monitoring.
        """
        for host in AdbMonitor.MONITOR_MAP:
            LOG.debug("AdbMonitor stop host {}".format(host))
            monitor = AdbMonitor.MONITOR_MAP[host]
            try:
                monitor.is_stop = True
                if monitor.main_adb_connection is not None:
                    monitor.main_adb_connection.shutdown(2)
                    monitor.main_adb_connection.close()
                    monitor.main_adb_connection = None
            except (socket.error, socket.gaierror, socket.timeout) as _:
                LOG.error("AdbMonitor close socket exception")
        AdbMonitor.MONITOR_MAP.clear()
        LOG.debug("AdbMonitor {} monitor stop!".format(AdbHelper.CONNECTOR_NAME))
        LOG.debug("AdbMonitor map is {}".format(AdbMonitor.MONITOR_MAP))

    def loop_monitor(self):
        """
        Monitors the devices. This connects to the Debug Bridge
        """
        LOG.debug("current connector name is {}".format(AdbHelper.CONNECTOR_NAME))
        while not self.is_stop:
            try:
                if self.main_adb_connection is None:
                    self.main_adb_connection = self.open_adb_connection()
                    if self.main_adb_connection is None:
                        self.connection_attempt += 1

                        if self.connection_attempt > MAX_CONNECT_ATTEMPT_COUNT:
                            self.is_stop = True
                            LOG.error("AdbMonitor attempt {}, can't connect to hdc for Device List Monitoring".format(
                                str(self.connection_attempt)))
                            raise HdcError("AdbMonitor cannot connect {} server({} {}) please check!".format(
                                AdbHelper.CONNECTOR_NAME, self.channel.get("host"), str(self.channel.get("port"))))
                        LOG.debug("AdbMonitor Connection attempts: {}".format(str(self.connection_attempt)))
                        time.sleep(2)
                    else:
                        LOG.debug("AdbMonitor Connected to {} for device monitoring, main_adb_connection is {}".format(
                            AdbHelper.CONNECTOR_NAME, self.main_adb_connection))
                self.track_devices()
            except (HdcError, Exception) as _:
                self.handle_exception_monitor_loop()
                break

    def handle_exception_monitor_loop(self):
        LOG.debug("Handle exception monitor loop: {}".format(self.main_adb_connection))
        if self.main_adb_connection is None:
            return
        self.main_adb_connection.close()
        LOG.debug("Handle exception monitor loop, main {} connection closed, main {} connection: {}".format(
            AdbHelper.CONNECTOR_NAME, AdbHelper.CONNECTOR_NAME, self.main_adb_connection))

    def device_list_monitoring(self):
        request = AdbHelper.form_adb_request("host:track-devices")
        AdbHelper.write(self.main_adb_connection, request)
        resp = AdbHelper.read_adb_response(self.main_adb_connection)
        if not resp.okay:
            LOG.error("AdbMonitor adb rejected shell command")
            raise Exception(resp.message)
        else:
            LOG.debug("AdbMonitor execute command success:send device_list monitoring request")
        return True

    def process_incoming_device_data(self, length):
        local_array_list = []
        if length > 0:
            data_buf = AdbHelper.read(self.main_adb_connection, length)
            data_str = AdbHelper.reply_to_string(data_buf)
            lines = data_str.split("\n")
            for line in lines:
                items = line.strip().split("\t")
                if len(items) != 2:
                    continue
                device_instance = self._get_device_instance(items, DeviceOsType.aosp)
                local_array_list.append(device_instance)
        self.update_devices(local_array_list)

    def _get_device_instance(self, items, os_type):
        device = get_plugin(plugin_type=Plugin.DEVICE, plugin_id=os_type)[0]
        device_instance = device.__class__()
        device_instance.__set_serial__(items[0])
        device_instance.host = self.channel.get("host")
        device_instance.port = self.channel.get("port")
        LOG.debug("Dmlib get device instance {} {} {}".format
                  (device_instance.device_sn,
                   device_instance.host, device_instance.port))
        device_instance.device_state = DeviceState.get_state(items[1])
        return device_instance

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

    def open_adb_connection(self):
        sock = None
        try:
            LOG.debug("AdbMonitor connecting to hdc for Device List Monitoring")
            LOG.debug(
                "AdbMonitor socket connection host: {}, port: {}".format(str(convert_ip(self.channel.get("host"))),
                                                                         str(int(self.channel.get("port")))))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.channel.get("host"), int(self.channel.get("port"))))
            return sock
        except (socket.error, socket.gaierror, socket.timeout) as exception:
            LOG.error("AdbMonitor hdc socket connection Error: {}, host is {}, port is {}"
                      "".format(exception, self.channel.get("host"), self.channel.get("port")))
            return sock

    def start_adb(self, connector=HDC_NAME, kill=False, local_port=None):
        if connector.startswith(HDC_NAME):
            if kill:
                LOG.debug("AdbMonitor {} kill".format(connector))
                exec_cmd([connector, "kill"])
            if self.hdc_version and "Ver:" not in self.hdc_version:
                LOG.debug("AdbMonitor {} reset".format(connector))
                exec_cmd([connector, "reset"], error_print=False, redirect=True)
            else:
                LOG.debug("AdbMonitor {} start".format(connector))
                exec_cmd([connector, "-l5", "start"], error_print=False, redirect=True)
        else:
            if kill:
                LOG.debug("AdbMonitor {}".format(UsbConst.kill_server))
                exec_cmd([UsbConst.connector, "kill-server"])
            LOG.debug("AdbMonitor {}".format(UsbConst.start_server))
            exec_cmd([UsbConst.connector, "start-server"], error_print=False)

    def track_devices(self):
        if self.main_adb_connection and not self.monitoring:
            self.monitoring = self.device_list_monitoring()
        if self.monitoring is True:
            self.connection_attempt = 0
            len_buf = AdbHelper.read(self.main_adb_connection, DATA_UNIT_LENGTH)
            self.server.monitor_lock.acquire()
            len_str = AdbHelper.reply_to_string(len_buf)
            length = int(len_str, HEXADECIMAL_NUMBER)
            if length >= 0:
                self.process_incoming_device_data(length)
            self.server.monitor_lock.release()


@dataclass
class AdbResponse:
    okay = ID_OKAY
    message = ""


class SyncService:

    def __init__(self, device, host=None, port=None):
        self.device = device
        self.host = host
        self.port = port
        self.sock = None

    def open_sync(self, timeout=DEFAULT_TIMEOUT):
        LOG.debug("Open sync, timeout={}".format(int(timeout / 1000)))
        self.sock = AdbHelper.socket(host=self.host, port=self.port, timeout=timeout)
        AdbHelper.set_device(self.device, self.sock)

        request = AdbHelper.form_adb_request("sync:")
        AdbHelper.write(self.sock, request)

        resp = AdbHelper.read_adb_response(self.sock)
        if not resp.okay:
            self.device.log.error("Got unhappy response from HDC sync req: {}".format(resp.message))
            raise HdcError("Got unhappy response from HDC sync req: {}".format(resp.message))

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except socket.error as error:
                LOG.error("Socket close error: {}".format(error), error_no="00420")
            finally:
                self.sock = None

    def pull_file(self, remote, local, is_create=False):
        """
        Pulls a file.
        The top directory won't be created if is_create is False (by default)
        and vice versa
        """
        mode = self.read_mode(remote)
        self.device.log.debug("Remote file %s mode is %d" % (remote, mode))
        if mode == 0:
            raise HdcError("Remote object doesn't exist!")

        if str(mode).startswith("168"):
            if is_create:
                remote_file_split = os.path.split(remote)[-1] \
                    if os.path.split(remote)[-1] else os.path.split(remote)[-2]
                remote_file_basename = os.path.basename(remote_file_split)
                new_local = os.path.join(local, remote_file_basename)
                create_dir(new_local)
            else:
                new_local = local

            collect_receiver = CollectingOutputReceiver()
            AdbHelper.execute_shell_command(self.device, "ls %s" % remote,
                                            receiver=collect_receiver)
            files = collect_receiver.output.split()
            for file_name in files:
                self.pull_file("%s/%s" % (remote, file_name),
                               new_local, is_create=True)
        elif mode == SPECIAL_FILE_MODE:
            self.device.log.info("skipping special file '%s'" % remote)
        else:
            if os.path.isdir(local):
                local = os.path.join(local, os.path.basename(remote))

            self.do_pull_file(remote, local)

    def do_pull_file(self, remote, local):
        """
        Pulls a remote file
        """
        self.device.log.info(
            "%s pull %s to %s" % (convert_serial(self.device.device_sn),
                                  remote, local))
        remote_path_content = remote.encode(DEFAULT_ENCODING)
        if len(remote_path_content) > REMOTE_PATH_MAX_LENGTH:
            raise HdcError("Remote path is too long.")

        msg = self.create_file_req(ID_RECV, remote_path_content)
        AdbHelper.write(self.sock, msg)
        pull_result = AdbHelper.read(self.sock, DATA_UNIT_LENGTH * 2)
        if not self.check_result(pull_result, ID_DATA) and \
                not self.check_result(pull_result, ID_DONE):
            raise HdcError(self.read_error_message(pull_result))
        if platform.system() == "Windows":
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_BINARY
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        pulled_file_open = os.open(local, flags, FilePermission.mode_755)
        with os.fdopen(pulled_file_open, "wb") as pulled_file:
            while True:
                if self.check_result(pull_result, ID_DONE):
                    break

                if not self.check_result(pull_result, ID_DATA):
                    raise HdcError(self.read_error_message(pull_result))

                try:
                    length = self.swap32bit_from_array(
                        pull_result, DEFAULT_OFFSET_OF_INT)
                except IndexError as index_error:
                    self.device.log.debug("do_pull_file: %s" %
                                          str(pull_result))
                    if pull_result == ID_DATA:
                        pull_result = self.sock.recv(DATA_UNIT_LENGTH)
                        self.device.log.debug(
                            "do_pull_file: %s" % str(pull_result))
                        length = self.swap32bit_from_array(pull_result, 0)
                        self.device.log.debug("do_pull_file: %s" % str(length))
                    else:
                        raise index_error

                if length > SYNC_DATA_MAX:
                    raise HdcError("Receiving too much data.")

                pulled_file.write(AdbHelper.read(self.sock, length))
                pulled_file.flush()
                pull_result = self.sock.recv(DATA_UNIT_LENGTH * 2)

    def push_file(self, local, remote, is_create=False):
        """
        Push a single file.
        The top directory won't be created if is_create is False (by default)
        and vice versa
        """
        if not os.path.exists(local):
            raise HdcError("Local path doesn't exist.")

        if os.path.isdir(local):
            if is_create:
                local_file_split = os.path.split(local)[-1] \
                    if os.path.split(local)[-1] else os.path.split(local)[-2]
                local_file_basename = os.path.basename(local_file_split)
                remote = "{}/{}".format(
                    remote, local_file_basename)
                AdbHelper.execute_shell_command(
                    self.device, "mkdir -p %s" % remote)

            for child in os.listdir(local):
                file_path = os.path.join(local, child)
                if os.path.isdir(file_path):
                    self.push_file(
                        file_path, "%s/%s" % (remote, child),
                        is_create=False)
                else:
                    self.do_push_file(file_path, "%s/%s" % (remote, child))
        else:
            self.do_push_file(local, remote)

    def do_push_file(self, local, remote):
        """
        Push a single file

        Args:
        ------------
        local : string
            the local file to push
        remote : string
            the remote file (length max is 1024)
        """
        mode = self.read_mode(remote)
        self.device.log.debug("Remote file %s mode is %d" % (remote, mode))
        if self.device.usb_type == DeviceConnectorType.hdc:
            self.device.log.debug("%s execute command: hdc push %s %s" % (
                convert_serial(self.device.device_sn), local, remote))
        else:
            self.device.log.debug("%s execute command: %s push %s %s" % (
                convert_serial(self.device.device_sn), UsbConst.push, local, remote))
        if str(mode).startswith("168"):
            remote = "%s/%s" % (remote, os.path.basename(local))

        try:
            try:
                remote_path_content = remote.encode(DEFAULT_ENCODING)
            except UnicodeEncodeError as _:
                remote_path_content = remote.encode("UTF-8")
            if len(remote_path_content) > REMOTE_PATH_MAX_LENGTH:
                raise HdcError("Remote path is too long.")

            # create the header for the action
            # and send it. We use a custom try/catch block to make the
            # difference between file and network IO exceptions.
            msg = self.create_send_file_req(ID_SEND, remote_path_content,
                                            FilePermission.mode_644)

            AdbHelper.write(self.sock, msg)
            flags = os.O_RDONLY
            modes = stat.S_IWUSR | stat.S_IRUSR
            with os.fdopen(os.open(local, flags, modes), "rb") as test_file:
                while True:
                    if platform.system() == "Linux":
                        data = test_file.read(1024 * 4)
                    else:
                        data = test_file.read(SYNC_DATA_MAX)

                    if not data:
                        break

                    buf = struct.pack(
                        "%ds%ds%ds" % (len(ID_DATA), FORMAT_BYTES_LENGTH,
                                       len(data)), ID_DATA,
                        self.swap32bits_to_bytes(len(data)), data)
                    self.sock.send(buf)
        except Exception as exception:
            self.device.log.error("exception %s" % exception)
            raise exception

        msg = self.create_req(ID_DONE, int(time.time()))
        AdbHelper.write(self.sock, msg)
        result = AdbHelper.read(self.sock, DATA_UNIT_LENGTH * 2)
        if not self.check_result(result, ID_OKAY):
            self.device.log.error("exception %s" % result)
            raise HdcError(self.read_error_message(result))

    def read_mode(self, path):
        """
        Returns the mode of the remote file.
        Return an Integer containing the mode if all went well or null
        """
        msg = self.create_file_req(ID_STAT, path)
        AdbHelper.write(self.sock, msg)

        # read the result, in a byte array containing 4 ints
        stat_result = AdbHelper.read(self.sock, DATA_UNIT_LENGTH * 4)
        if not self.check_result(stat_result, ID_STAT):
            return INVALID_MODE_CODE

        return self.swap32bit_from_array(stat_result, DEFAULT_OFFSET_OF_INT)

    def create_file_req(self, command, path):
        """
        Creates the data array for a file request. This creates an array with a
        4 byte command + the remote file name.

        Args:
        ------------
        command :
            the 4 byte command (ID_STAT, ID_RECV, ...)
        path : string
            The path, as a byte array, of the remote file on which to execute
            the command.

        return:
        ------------
            return the byte[] to send to the device through hdc
        """
        if isinstance(path, str):
            try:
                path = path.encode(DEFAULT_ENCODING)
            except UnicodeEncodeError as _:
                path = path.encode("UTF-8")

        return struct.pack(
            "%ds%ds%ds" % (len(command), FORMAT_BYTES_LENGTH, len(path)),
            command, self.swap32bits_to_bytes(len(path)), path)

    def create_send_file_req(self, command, path, mode=0o644):
        # make the mode into a string
        mode_str = ",%s" % str(mode & FilePermission.mode_777)
        mode_content = mode_str.encode(DEFAULT_ENCODING)
        return struct.pack(
            "%ds%ds%ds%ds" % (len(command), FORMAT_BYTES_LENGTH, len(path),
                              len(mode_content)),
            command, self.swap32bits_to_bytes(len(path) + len(mode_content)),
            path, mode_content)

    def create_req(self, command, value):
        """
        Create a command with a code and an int values
        """
        return struct.pack("%ds%ds" % (len(command), FORMAT_BYTES_LENGTH),
                           command, self.swap32bits_to_bytes(value))

    @staticmethod
    def check_result(result, code):
        """
        Checks the result array starts with the provided code

        Args:
        ------------
        result :
            the result array to check
        path : string
            the 4 byte code

        return:
        ------------
        bool
            return true if the code matches
        """
        return result[0:4] == code[0:4]

    def read_error_message(self, result):
        """
        Reads an error message from the opened Socket.

        Args:
        ------------
        result :
            the current hdc result. Must contain both FAIL and the length of
            the message.
        """
        if self.check_result(result, ID_FAIL):
            length = self.swap32bit_from_array(result, 4)
            if length > 0:
                return str(AdbHelper.read(self.sock, length))

        return None

    @staticmethod
    def swap32bits_to_bytes(value):
        """
        Swaps an unsigned value around, and puts the result in an bytes that
        can be sent to a device.

        Args:
        ------------
        value :
            the value to swap.
        """
        return bytes([value & 0x000000FF,
                      (value & 0x0000FF00) >> 8,
                      (value & 0x00FF0000) >> 16,
                      (value & 0xFF000000) >> 24])

    @staticmethod
    def swap32bit_from_array(value, offset):
        """
        Reads a signed 32 bit integer from an array coming from a device.

        Args:
        ------------
        value :
            the array containing the int
        offset:
            the offset in the array at which the int starts

        Return:
        ------------
        int
            the integer read from the array
        """
        result = 0
        result |= (int(value[offset])) & 0x000000FF
        result |= (int(value[offset + 1]) & 0x000000FF) << 8
        result |= (int(value[offset + 2]) & 0x000000FF) << 16
        result |= (int(value[offset + 3]) & 0x000000FF) << 24

        return result


class AdbHelper:
    CONNECTOR_NAME = ""

    @staticmethod
    def push_file(device, local, remote, is_create=False, timeout=DEFAULT_TIMEOUT):
        if device.usb_type == DeviceConnectorType.hdc:
            device.log.info("{} execute command: {} file send {} {}".format(
                convert_serial(device.device_sn), AdbHelper.CONNECTOR_NAME, local, remote))
        else:
            device.log.info("{} execute command: {} {} {} {}".format(
                convert_serial(device.device_sn), AdbHelper.CONNECTOR_NAME, UsbConst.push, local, remote))
        service = None
        try:
            service = SyncService(device, host=device.host, port=device.port)
            service.open_sync(timeout)
            service.push_file(local, remote, is_create=is_create)
        finally:
            if service is not None:
                service.close()

    @staticmethod
    def pull_file(device, remote, local, is_create=False, timeout=DEFAULT_TIMEOUT):
        if device.usb_type == DeviceConnectorType.hdc:
            device.log.info("{} execute command: {} file recv {} to {}".format(
                convert_serial(device.device_sn), AdbHelper.CONNECTOR_NAME, remote, local))
        else:
            device.log.info("{} execute command: {} {} to {}".format(
                convert_serial(device.device_sn), UsbConst.pull, remote, local))
        service = None
        try:
            service = SyncService(device, host=device.host, port=device.port)
            service.open_sync(timeout)
            service.pull_file(remote, local, is_create=is_create)
        finally:
            if service is not None:
                service.close()

    @staticmethod
    def _install_remote_package(device, remote_file_path, command):
        receiver = CollectingOutputReceiver()
        cmd = "pm install %s %s" % (command.strip(), remote_file_path)
        AdbHelper.execute_shell_command(device, cmd, INSTALL_TIMEOUT, receiver)
        return receiver.output

    @staticmethod
    def install_package(device, package_file_path, command):
        device.log.info("%s install %s" % (convert_serial(device.device_sn),
                                           package_file_path))
        remote_file_path = "/data/local/tmp/%s" % os.path.basename(
            package_file_path)

        service = None
        try:
            service = SyncService(device, host=device.host, port=device.port)
            service.open_sync()
            service.push_file(package_file_path, remote_file_path)
        finally:
            if service is not None:
                service.close()

        result = AdbHelper._install_remote_package(device, remote_file_path, command)

        AdbHelper.execute_shell_command(device, "rm %s " % remote_file_path)
        return result

    @staticmethod
    def uninstall_package(device, package_name):
        receiver = CollectingOutputReceiver()
        command = "pm uninstall %s " % package_name
        device.log.info("%s %s" % (convert_serial(device.device_sn), command))
        AdbHelper.execute_shell_command(device, command, INSTALL_TIMEOUT,
                                        receiver)
        return receiver.output

    @staticmethod
    def reboot(device, into=None):
        if device.usb_type == DeviceConnectorType.hdc:
            device.log.info("{} execute command: {} target boot".format(
                convert_serial(device.device_sn), AdbHelper.CONNECTOR_NAME))
        else:
            device.log.info("{} execute command: {}".format(
                convert_serial(device.device_sn), UsbConst.reboot))
        with AdbHelper.socket(host=device.host, port=device.port) as sock:
            AdbHelper.set_device(device, sock)
            if into is None:
                request = AdbHelper.form_adb_request("reboot:")
            else:
                request = AdbHelper.form_adb_request("reboot:{}".format(into))
            AdbHelper.write(sock, request)

    @staticmethod
    def execute_shell_command(device, command, timeout=DEFAULT_TIMEOUT,
                              receiver=None, **kwargs):
        """
        Executes a shell command on the device and retrieve the output.

        Args:
        ------------
        device : IDevice
            on which to execute the command.
        command : string
            the shell command to execute
        timeout : int
            max time between command output. If more time passes between
            command output, the method will throw
            ShellCommandUnresponsiveException (ms).
        """
        try:
            if not timeout:
                timeout = DEFAULT_TIMEOUT

            with AdbHelper.socket(host=device.host, port=device.port,
                                  timeout=timeout) as sock:
                output_flag = kwargs.get("output_flag", True)
                timeout_msg = " with timeout %ss" % str(timeout / 1000)
                if device.usb_type == DeviceConnectorType.hdc:
                    message = "{} execute command: hdc shell {}{}".format(
                        convert_serial(device.device_sn), command, timeout_msg)
                else:
                    message = "{} execute command: {} {}{}".format(
                        convert_serial(device.device_sn), UsbConst.shell, command, timeout_msg)
                if output_flag:
                    LOG.info(message)
                else:
                    LOG.debug(message)
                from xdevice import Scheduler
                AdbHelper.set_device(device, sock)
                request = AdbHelper.form_adb_request("shell:{}".format(command))
                AdbHelper.write(sock, request)
                resp = AdbHelper.read_adb_response(sock)
                if not resp.okay:
                    device.log.error(
                        "[AdbHelper] {} rejected shell command ({}): {}".format(AdbHelper.CONNECTOR_NAME, command,
                                                                                resp.message))
                    raise HdcCommandRejectedException(resp.message)

                data = sock.recv(SOCK_DATA_MAX)
                while data != b'':
                    ret = AdbHelper.reply_to_string(data)
                    if ret:
                        if receiver:
                            receiver.__read__(ret)
                        else:
                            LOG.debug(ret)
                    if not Scheduler.is_execute:
                        raise ExecuteTerminate()
                    data = AdbHelper.read(sock, SOCK_DATA_MAX)
                return resp
        except socket.timeout as error:
            device.log.error("ShellCommandUnresponsiveException: {} shell {} timeout[{}S]".format(
                convert_serial(device.device_sn), command, str(timeout / 1000)))
            raise error
        finally:
            if receiver:
                receiver.__done__()

    @staticmethod
    def set_device(device, sock):
        """
        Tells hdc to talk to a specific device
        if the device is not -1, then we first tell hdc we're looking to talk
        to a specific device
        """
        msg = "host:transport:%s" % device.device_sn
        device_query = AdbHelper.form_adb_request(msg)
        AdbHelper.write(sock, device_query)
        resp = AdbHelper.read_adb_response(sock)
        if not resp.okay:
            raise HdcCommandRejectedException(resp.message)

    @staticmethod
    def form_adb_request(req):
        """
        Create an ASCII string preceded by four hex digits.
        """
        try:
            req = req.encode("utf-8").decode("latin1")
            result_str = "%04X%s" % (len(req), req)
            result = result_str.encode(DEFAULT_ENCODING)
        except UnicodeEncodeError as ex:
            LOG.error(ex)
            raise ex
        return result

    @staticmethod
    def read_adb_response(sock, read_diag_string=False):
        """
        Reads the response from ADB after a command.

        Args:
        ------------
        read_diag_string :
            If true, we're expecting an OKAY response to be followed by a
            diagnostic string. Otherwise, we only expect the diagnostic string
            to follow a FAIL.
        """
        resp = AdbResponse()
        reply = AdbHelper.read(sock, DATA_UNIT_LENGTH)
        if AdbHelper.is_okay(reply):
            resp.okay = True
        else:
            read_diag_string = True
            resp.okay = False

        while read_diag_string:
            len_buf = AdbHelper.read(sock, DATA_UNIT_LENGTH)
            len_str = AdbHelper.reply_to_string(len_buf)
            msg = AdbHelper.read(sock, int(len_str, HEXADECIMAL_NUMBER))
            resp.message = AdbHelper.reply_to_string(msg)
            break

        return resp

    @staticmethod
    def write(sock, req, timeout=10):
        if isinstance(req, str):
            req = req.encode(DEFAULT_ENCODING)
        elif isinstance(req, list):
            req = bytes(req)

        start_time = time.time()
        while req:
            if time.time() - start_time > timeout:
                LOG.debug("Socket write timeout, timeout:%ss" % timeout)
                break

            size = sock.send(req)
            if size < 0:
                raise DeviceError("channel EOF")

            req = req[size:]
            time.sleep(5 / 1000)

    @staticmethod
    def read(sock, length, timeout=10):
        data = b''
        recv_len = 0
        start_time = time.time()
        exc_num = 3
        while length - recv_len > 0:
            if time.time() - start_time > timeout:
                LOG.debug("Socket read timeout, timout:%ss" % timeout)
                break
            try:
                recv = sock.recv(length - recv_len)
                if len(recv) > 0:
                    time.sleep(5 / 1000)
                else:
                    break
            except ConnectionResetError as error:
                if exc_num <= 0:
                    raise error
                exc_num = exc_num - 1
                recv = b''
                time.sleep(1)
                LOG.debug("ConnectionResetError occurs")

            data += recv
            recv_len += len(recv)

        return data

    @staticmethod
    def is_okay(reply):
        """
        Checks to see if the first four bytes in "reply" are OKAY.
        """
        return reply[0:4] == ID_OKAY

    @staticmethod
    def reply_to_string(reply):
        """
        Converts an HDC reply to a string.
        """
        try:
            return str(reply, encoding=DEFAULT_ENCODING)
        except (ValueError, TypeError) as _:
            return ""

    @staticmethod
    def socket(host=None, port=None, timeout=None):
        end = time.time() + 10 * 60
        sock = None
        adb_connection = AdbMonitor.MONITOR_MAP.get(host, "127.0.0.1")
        while host not in AdbMonitor.MONITOR_MAP or \
                adb_connection.main_adb_connection is None:
            LOG.debug("Host: %s, port: %s, AdbMonitor map is %s" % (
                host, port, AdbMonitor.MONITOR_MAP))
            if host in AdbMonitor.MONITOR_MAP:
                LOG.debug("Monitor main {} connection is {}".format(AdbHelper.CONNECTOR_NAME,
                          adb_connection.main_hdc_connection))
            if time.time() > end:
                raise HdcError("Cannot detect {} monitor!".format(AdbHelper.CONNECTOR_NAME))
            time.sleep(2)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))
        except socket.error as exception:
            LOG.exception("Connect hdc server error: %s" % str(exception),
                          exc_info=False)
            raise exception

        if sock is None:
            raise HdcError("Cannot connect hdc server!")

        if timeout is not None:
            sock.setblocking(False)
            sock.settimeout(timeout / 1000)

        return sock


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
        connector_name = UsbConst.connector
        AdbHelper.CONNECTOR_NAME = connector_name
        if port:
            self.port = int(port)
        elif usb_type == DeviceConnectorType.hdc:
            self.port = int(os.getenv("HDC_SERVER_PORT", DEFAULT_PORT))
        else:
            self.port = int(os.getenv(UsbConst.server_port, DEFAULT_PORT))

    def start(self):
        self.device_monitor = AdbMonitor.get_instance(
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
        LOG.debug("DeviceConnector device connected:host %s, port %s, "
                  "device sn %s " % (self.host, self.port, device.device_sn))
        if device.host != self.host or device.port != self.port:
            LOG.debug("DeviceConnector device error")
        for listener in self.device_listeners:
            listener.device_connected(device)

    def device_disconnected(self, device):
        LOG.debug("DeviceConnector device disconnected:host %s, port %s, "
                  "device sn %s" % (self.host, self.port, device.device_sn))
        if device.host != self.host or device.port != self.port:
            LOG.debug("DeviceConnector device error")
        for listener in self.device_listeners:
            listener.device_disconnected(device)

    def device_changed(self, device):
        LOG.debug("DeviceConnector device changed:host %s, port %s, "
                  "device sn %s" % (self.host, self.port, device.device_sn))
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
