/*
 * Copyright (c) 2026 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "display_jni.h"

#include <jni.h>
#include <mutex>
#include <string>

#include "inner_api/plugin_utils_inner.h"
#include "log.h"
#include "plugin_utils.h"

namespace OHOS::UiTest {
namespace {
static std::mutex g_displayJniMutex;

static const char DISPLAY_PLUGIN_CLASS_NAME[] = "ohos/ace/plugin/display/DisplayPlatform";

static const char METHOD_SET_DISPLAY_ROTATION[] = "setDisplayRotation";

static const char SIGNATURE_SET_DISPLAY_ROTATION[] = "(I)V";

struct DisplayJniCache {
    jmethodID setDisplayRotation;
    jmethodID nativeInit;
    jobject globalRefObj;
} g_displayJni;

static const JNINativeMethod METHODS[] = {
    { .name = "nativeInit", .signature = "()V", .fnPtr = reinterpret_cast<void*>(DisplayJni::NativeInit) },
};
} // namespace

void DisplayJni::NativeInit(JNIEnv* env, jobject object)
{
    CHECK_NULL_VOID(env);
    CHECK_NULL_VOID(object);
    jclass clazz = env->GetObjectClass(object);
    CHECK_NULL_VOID(clazz);

    std::lock_guard<std::mutex> lock(g_displayJniMutex);
    if (g_displayJni.globalRefObj != nullptr) {
        env->DeleteGlobalRef(g_displayJni.globalRefObj);
        g_displayJni.globalRefObj = nullptr;
    }
    g_displayJni.globalRefObj = env->NewGlobalRef(object);

    g_displayJni.setDisplayRotation =
        env->GetMethodID(clazz, METHOD_SET_DISPLAY_ROTATION, SIGNATURE_SET_DISPLAY_ROTATION);
    env->DeleteLocalRef(clazz);
}

bool DisplayJni::Register(void* env)
{
    auto* jniEnv = static_cast<JNIEnv*>(env);
    CHECK_NULL_RETURN(jniEnv, false);

    jclass clazz = jniEnv->FindClass(DISPLAY_PLUGIN_CLASS_NAME);
    CHECK_NULL_RETURN(clazz, false);

    bool ret = jniEnv->RegisterNatives(clazz, METHODS, sizeof(METHODS) / sizeof(METHODS[0])) == 0;
    jniEnv->DeleteLocalRef(clazz);
    return ret;
}

void DisplayJni::SetDisplayRotation(int rotation)
{
    auto env = ARKUI_X_Plugin_GetJniEnv();
    CHECK_NULL_VOID(env);
    std::lock_guard<std::mutex> lock(g_displayJniMutex);
    CHECK_NULL_VOID(g_displayJni.globalRefObj);
    CHECK_NULL_VOID(g_displayJni.setDisplayRotation);

    env->CallVoidMethod(g_displayJni.globalRefObj, g_displayJni.setDisplayRotation, rotation);
    if (env->ExceptionCheck()) {
        env->ExceptionDescribe();
        env->ExceptionClear();
        LOGE("SetDisplayRotation: Exception in CallVoidMethod");
    }
}
} // namespace OHOS::UiTest
