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

#ifndef TEST_TESTFWK_ARKXTEST_UITEST_CAPABILITY_SCREEN_CAPTURE_ANDROID_JAVA_JNI_SCREEN_CAPTURE_JNI_H
#define TEST_TESTFWK_ARKXTEST_UITEST_CAPABILITY_SCREEN_CAPTURE_ANDROID_JAVA_JNI_SCREEN_CAPTURE_JNI_H

#include <memory>
#include <string>

#include "common_type.h"
#include "jni.h"

#include "base/utils/noncopyable.h"

namespace OHOS::UiTest {
class ScreenCaptureJni final {
public:
    static bool Register(void* env);
    static void NativeInit(JNIEnv* env, jobject jobj);
    static bool CaptureScreen(const std::string& savePath, const Rect& rect);

private:
    ACE_DISALLOW_COPY_AND_MOVE(ScreenCaptureJni);

    static void OnJniRegistered();
};
} // namespace OHOS::UiTest

#endif // TEST_TESTFWK_ARKXTEST_UITEST_CAPABILITY_SCREEN_CAPTURE_ANDROID_JAVA_JNI_SCREEN_CAPTURE_JNI_H
