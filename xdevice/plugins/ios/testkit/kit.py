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
import plistlib
import re

from xdevice import AppInstallError
from xdevice import FilePermission
from xdevice import ITestKit
from xdevice import ParamError
from xdevice import Plugin
from xdevice import get_config_value
from xdevice import get_file_absolute_path
from xdevice import platform_logger
from xdevice import DeviceTestType

from ios.constants import CKit

LOG = platform_logger("Kit")

__all__ = ["IosAppInstallKit", "IosPushKit", "IosShellKit"]


@Plugin(type=Plugin.TEST_KIT, id=CKit.ios_app_install)
class IosAppInstallKit(ITestKit):
    def __init__(self):
        self.app_list = ""
        self.app_list_name = ""
        self.is_clean = ""
        self.alt_dir = ""
        self.ex_args = ""
        self.installed_app = set()
        self.paths = ""
        self.env_index_list = None

    def __check_config__(self, options):
        self.app_list = get_config_value('test-file-name', options)
        self.app_list_name = get_config_value('test-file-packName', options)
        self.is_clean = get_config_value('cleanup-apps', options, False)
        self.alt_dir = get_config_value('alt-dir', options, False)
        if self.alt_dir and self.alt_dir.startswith("resource/"):
            self.alt_dir = self.alt_dir[len("resource/"):]
        self.ex_args = get_config_value('install-arg', options, False)
        self.installed_app = set()
        self.paths = get_config_value('paths', options)
        self.env_index_list = get_config_value('env-index', options)

    def __setup__(self, device, **kwargs):
        request = kwargs.get("request", None)
        del kwargs
        LOG.debug("IosAppInstallKit setup, device:{}".format(device.device_sn))
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
            result = self.install_app(device, app_file, self.ex_args)
            if result is not True:
                raise AppInstallError(
                    "Failed to install {} on {}. Reason:{}".format
                    (app_file, device.__get_serial__(), result))
            self.installed_app.add(app_file)
        # arkuix跨平台测试需要一个入口文件来启动，通过查找app包名获取文件路径
        if request.root.source.test_type == DeviceTestType.arkuix_jsunit_test:
            for app in self.installed_app:
                app_name = get_app_name(app)
                if app_name == request.config.bundle_name:
                    request.config.testargs.update({"app_file": app})
                    break

    def __teardown__(self, device):
        LOG.debug("IosAppInstallKit teardown: device:{}".format(device.device_sn))
        if self.is_clean and str(self.is_clean).lower() == "true":
            if self.app_list_name and len(self.app_list_name) > 0:
                for app_name in self.app_list_name:
                    result = device.uninstall_package(app_name)
                    if result and "OK" in result:
                        LOG.debug("uninstalling package Success. result is {}".format(result))
                    else:
                        LOG.warning("Error uninstalling package {} {}".format(device.__get_serial__(), result))
            else:
                for app in self.installed_app:
                    app_name = get_app_name(app)
                    if app_name:
                        result = device.uninstall_package(app_name)
                        if result and "OK" in result:
                            LOG.debug("uninstalling package Success. result is {}".format(result))
                        else:
                            LOG.warning("Error uninstalling package {} {}".format(device.__get_serial__(), result))
                    else:
                        LOG.warning("Can't find app name for {}".format(app))

    @staticmethod
    def install_app(device, app_file, ex_args):
        result = device.install_package(app_file, ex_args)
        if "Installed package" not in result:
            LOG.debug("Install {} failed, try again.".format(app_file))
            return IosAppInstallKit.retry_install_app(device, app_file, ex_args)
        else:
            LOG.debug("Install {} success".format(app_file))
            return True

    @staticmethod
    def retry_install_app(device, app_file, ex_args):
        result = device.install_package(app_file, ex_args)
        if "Installed package" not in result:
            LOG.debug("Install {} failed.".format(app_file))
            return result
        else:
            LOG.debug("Install {} success".format(app_file))
            return True


@Plugin(type=Plugin.TEST_KIT, id=CKit.ios_push)
class IosPushKit(ITestKit):
    def __init__(self):
        self.pre_push = ""
        self.push_list = ""
        self.post_push = ""
        self.is_uninstall = ""
        self.paths = ""
        self.pushed_file = []
        self.abort_on_push_failure = True
        self.teardown_push = ""

    def __check_config__(self, config):
        self.pre_push = get_config_value('pre-push', config)
        self.push_list = get_config_value('push', config)
        self.post_push = get_config_value('post-push', config)
        self.teardown_push = get_config_value('teardown-push', config)
        self.is_uninstall = get_config_value('uninstall', config,
                                             is_list=False, default=True)
        self.abort_on_push_failure = get_config_value(
            'abort-on-push-failure', config, is_list=False, default=True)
        if isinstance(self.abort_on_push_failure, str):
            self.abort_on_push_failure = False if \
                self.abort_on_push_failure.lower() == "false" else True

        self.paths = get_config_value('paths', config)
        self.pushed_file = []

    def __setup__(self, device, **kwargs):
        del kwargs
        LOG.debug("PushKit setup, device:{}".format(device.device_sn))
        for command in self.pre_push:
            run_command(device, command)
        dst = None
        for push_info in self.push_list:
            files = re.split('->|=>', push_info)
            if len(files) != 2:
                LOG.error("The push spec is invalid: {}".format(push_info))
                continue
            src = files[0].strip()
            bundle_id = files[1].strip().split("/")[1]
            if "." in bundle_id:
                dst = files[1].strip().replace("/" + bundle_id + "/", "")
            else:
                bundle_id = None
                dst = files[1].strip()
            LOG.debug(
                "Trying to push the file local {} to remote {}".format(src, dst))
            try:
                real_src_path = get_file_absolute_path(src, self.paths)
            except ParamError as error:
                if self.abort_on_push_failure:
                    raise error
                else:
                    LOG.warning(error, error_no=error.error_no)
                    continue
            ret = device.push_file(real_src_path, dst, bundle_id)
            if "Error" in ret:
                LOG.error("push file fail.")
            else:
                LOG.debug("push file successfully.")
            self.pushed_file.append(files[1].strip())
        for command in self.post_push:
            run_command(device, command)
        return self.pushed_file, dst

    def __teardown__(self, device):
        LOG.debug("PushKit teardown: device:{}".format(device.device_sn))
        for command in self.teardown_push:
            run_command(device, command)
        if self.is_uninstall:
            for file_name in self.pushed_file:
                LOG.debug("Trying to remove file {}".format(file_name))
                file_name = file_name.replace("\\", "/")
                bundle_id = file_name.strip().split("/")[1]
                if "." in bundle_id:
                    dst = file_name.strip().replace("/" + bundle_id + "/", "")
                else:
                    bundle_id = None
                    dst = file_name.strip()

                if bundle_id:
                    command = ["--bundle_id", bundle_id, "--rm", dst]
                else:
                    command = ["-f", "-R", dst]

                for _ in range(3):
                    ret = device.execute_shell_command(command)
                    if "Error" not in ret:
                        LOG.debug(
                            "Removed file {} successfully".format(file_name))
                        break
                else:
                    LOG.error("Failed to remove file {}".format(file_name))


@Plugin(type=Plugin.TEST_KIT, id=CKit.ios_shell)
class IosShellKit(ITestKit):
    def __init__(self):
        self.command_list = []
        self.tear_down_command = []
        self.paths = None

    def __check_config__(self, config):
        self.command_list = get_config_value('run-command', config)
        self.tear_down_command = get_config_value('teardown-command', config)
        self.paths = get_config_value('paths', config)

    def __setup__(self, device, **kwargs):
        del kwargs
        LOG.debug("ShellKit setup, device:{}".format(device.device_sn))
        if len(self.command_list) == 0:
            LOG.info("No setup_command to run, skipping!")
            return
        for command in self.command_list:
            run_command(device, command)

    def __teardown__(self, device):
        LOG.debug("ShellKit teardown: device:{}".format(device.device_sn))
        if len(self.tear_down_command) == 0:
            LOG.info("No teardown_command to run, skipping!")
            return
        for command in self.tear_down_command:
            run_command(device, command)


def get_app_name(app):
    path = os.path.join(app, "Info.plist")
    app_name = ""
    try:
        app_open = os.open(path, os.O_RDONLY, FilePermission.mode_755)
        with os.fdopen(app_open, mode="rb") as f:
            app_file_info = plistlib.load(f, fmt=plistlib.FMT_BINARY, dict_type=dict)
            app_name = app_file_info.get("CFBundleIdentifier")
    except Exception as e:
        LOG.error("get app name from app error: {}".format(e))
    return app_name


def run_command(device, command):
    LOG.debug("The command:{} is running".format(command))
    stdout = None
    if command.strip() == "reboot":
        device.reboot()
    else:
        stdout = device.execute_shell_command(command)
    LOG.debug("Run command result: {}".format(stdout if stdout else ""))
    return stdout
