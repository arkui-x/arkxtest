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

#ifndef TEST_TESTFWK_ARKXTEST_UITEST_CAPABILITY_TOUCH_INJECT_ANDROID_JAVA_JNI_TOUCH_INJECT_JNI_H
#define TEST_TESTFWK_ARKXTEST_UITEST_CAPABILITY_TOUCH_INJECT_ANDROID_JAVA_JNI_TOUCH_INJECT_JNI_H

#include "jni.h"

#include "base/utils/noncopyable.h"

namespace OHOS::UiTest {
class TouchInjectJni final {
public:
    static bool Register(void* env);
    static void NativeInit(JNIEnv* env, jobject jobj);
    static bool InjectTouchEvent(int action, float x, float y, int64_t downTime, int64_t eventTime);

private:
    ACE_DISALLOW_COPY_AND_MOVE(TouchInjectJni);
    static void OnJniRegistered();
};
} // namespace OHOS::UiTest

#endif // TEST_TESTFWK_ARKXTEST_UITEST_CAPABILITY_TOUCH_INJECT_ANDROID_JAVA_JNI_TOUCH_INJECT_JNI_H
