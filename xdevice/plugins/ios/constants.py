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

from dataclasses import dataclass

__all__ = ["UsbConst", "CKit"]


@dataclass
class UsbConst:
    connector = "ios"
    connector_type = "usb-ios"
    connector_ace = "ace"
    connector_ios_deploy = "ios-deploy"
    connector_idevice_id = "idevice_id"
    connector_libimobiledevice = "libimobiledevice"
    connector_idevicesyslog = "idevicesyslog"
    connector_idevicecrashreport = "idevicecrashreport"
    connector_ideviceinfo = "ideviceinfo"
    connector_idevicediagnostics = "idevicediagnostics"


@dataclass
class CKit:
    ios_app_install = "IosAppInstallKit"
    ios_push = "IosPushKit"
    ios_shell = "IosShellKit"
