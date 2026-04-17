/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "jni/screen_capture_jni.h"
#include "plugin_utils.h"

extern "C" __attribute__((constructor)) void RegisterAndroidScreenCapturePlugin(void)
{
    const char screenCapturePluginName[] = "ohos.ace.plugin.screencapture.ScreenCaptureHelper";
    ARKUI_X_Plugin_RegisterJavaPlugin(&OHOS::UiTest::ScreenCaptureJni::Register, screenCapturePluginName);
}