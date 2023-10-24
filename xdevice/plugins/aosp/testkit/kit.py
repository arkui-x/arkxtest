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
from xdevice import AppInstallError
from xdevice import ITestKit
from xdevice import Plugin
from xdevice import get_config_value
from xdevice import get_file_absolute_path
from xdevice import platform_logger
from xdevice import DeviceTestType
from xdevice import get_install_args
from xdevice import get_app_name_by_tool

from aosp.constants import CKit

LOG = platform_logger("Kit")
AAPT_PATH = None

__all__ = ["ApkInstallKit"]


@Plugin(type=Plugin.TEST_KIT, id=CKit.install)
class ApkInstallKit(ITestKit):
    def __init__(self):
        self.app_list = ""
        self.app_list_name = ""
        self.is_clean = ""
        self.alt_dir = ""
        self.ex_args = ""
        self.installed_app = set()
        self.paths = ""
        self.is_pri_app = ""
        self.env_index_list = None

    def __check_config__(self, options):
        self.app_list = get_config_value('test-file-name', options)
        self.app_list_name = get_config_value('test-file-packName', options)
        self.is_clean = get_config_value('cleanup-apks', options, False)
        self.alt_dir = get_config_value('alt-dir', options, False)
        if self.alt_dir and self.alt_dir.startswith("resource/"):
            self.alt_dir = self.alt_dir[len("resource/"):]
        self.ex_args = get_config_value('install-arg', options)
        self.installed_app = set()
        self.paths = get_config_value('paths', options)
        self.is_pri_app = get_config_value('install-as-privapp', options, False, default=False)
        self.env_index_list = get_config_value('env-index', options)

    def __setup__(self, device, **kwargs):
        request = kwargs.get("request", None)
        del kwargs
        LOG.debug("ApkInstallKit setup, device:{}".format(device.device_sn))
        if len(self.app_list) == 0:
            LOG.info("No app to install, skipping!")
            return
        # to disable app install alert
        for app in self.app_list:
            if self.alt_dir:
                app_file = get_file_absolute_path(app, self.paths,
                                                  self.alt_dir)
            else:
                app_file = get_file_absolute_path(app, self.paths)
            if app_file is None:
                LOG.error("The app file {} does not exist".format(app))
                continue
            result = device.install_package(app_file, get_install_args(device, app_file, self.ex_args))
            if "Success" not in result and "successfully" not in result:
                raise AppInstallError(
                    "Failed to install {} on {}. Reason:{}".format
                    (app_file, device.__get_serial__(), result))
            self.installed_app.add(app_file)
        # arkuix跨平台测试需要一个入口文件来启动，通过查找app包名获取文件路径
        if request.root.source.test_type == DeviceTestType.arkuix_jsunit_test:
            for app in self.installed_app:
                app_name = get_app_name_by_tool(app, [get_aapt_path()])
                if app_name == request.config.bundle_name:
                    request.config.testargs.update({"app_file": app})
                    break

    def __teardown__(self, device):
        LOG.debug("ApkInstallKit teardown: device:{}".format(device.device_sn))
        if self.is_clean and str(self.is_clean).lower() == "true":
            if self.app_list_name and len(self.app_list_name) > 0:
                for app_name in self.app_list_name:
                    result = device.uninstall_package(app_name)
                    if result and (result.startswith("Success") or "successfully" in result):
                        LOG.debug("uninstalling package Success. result is {}".format(result))
                    else:
                        LOG.warning("Error uninstalling package {} {}".format(device.__get_serial__(), result))
            else:
                for app in self.installed_app:
                    app_name = get_app_name_by_tool(app, [get_aapt_path()])
                    if app_name:
                        result = device.uninstall_package(app_name)
                        if result and (result.startswith("Success") or "successfully" in result):
                            LOG.debug("uninstalling package Success. result is {}".format(result))
                        else:
                            LOG.warning("Error uninstalling package {} {}".format(device.__get_serial__(), result))
                    else:
                        LOG.warning("Can't find app name for {}".format(app))


def get_aapt_path():
    global AAPT_PATH
    if AAPT_PATH:
        return AAPT_PATH
    sdk = os.environ.get("ANDROID_HOME")
    if not sdk:
        raise EnvironmentError("Can't not find android sdk, please check!")
    build_path = os.path.join(sdk, "build-tools")
    aapt_name = "aapt.exe" if os.name == "nt" else "aapt"
    for tool_dir in os.listdir(build_path):
        aapt_path = os.path.join(build_path, tool_dir, aapt_name)
        if os.path.exists(aapt_path):
            AAPT_PATH = os.path.join(build_path, tool_dir)
            return AAPT_PATH
    return None
