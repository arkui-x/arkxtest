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

#include "jni/touch_inject_jni.h"

#include <mutex>

#include "inner_api/plugin_utils_inner.h"
#include "touch_inject_delegate.h"
#include "touch_inject_proxy.h"

#include "adapter/android/entrance/java/jni/jni_environment.h"
#include "base/log/log_wrapper.h"
#include "base/utils/macros.h"

namespace OHOS::UiTest {
namespace {
static std::mutex g_touchInjectJniMutex;

static const char* const TOUCH_INJECTOR_CLASS_NAME = "ohos/ace/plugin/touchinject/TouchInjectorBase";

static const JNINativeMethod METHODS[] = {
    { "nativeInit", "()V", reinterpret_cast<void*>(TouchInjectJni::NativeInit) },
};

static const char METHOD_INJECT[] = "injectTouchEvent";
static const char SIGNATURE_INJECT[] = "(IFFJJ)Z";

jobject g_jobject = nullptr;

struct {
    jmethodID injectTouchEvent;
} g_pluginClass;
} // namespace

bool TouchInjectJni::Register(void* env)
{
    auto* jniEnv = static_cast<JNIEnv*>(env);
    CHECK_NULL_RETURN(jniEnv, false);

    jclass cls = jniEnv->FindClass(TOUCH_INJECTOR_CLASS_NAME);
    CHECK_NULL_RETURN(cls, false);

    bool ret = jniEnv->RegisterNatives(cls, METHODS, sizeof(METHODS) / sizeof(METHODS[0])) == 0;
    jniEnv->DeleteLocalRef(cls);
    CHECK_NULL_RETURN(ret, false);

    OnJniRegistered();
    return true;
}

void TouchInjectJni::OnJniRegistered()
{
    TouchInjectProxy::GetInstance()->SetDelegate(std::make_unique<TouchInjectDelegate>());
}

void TouchInjectJni::NativeInit(JNIEnv* env, jobject jobj)
{
    CHECK_NULL_VOID(env);
    CHECK_NULL_VOID(jobj);

    jclass cls = env->GetObjectClass(jobj);
    CHECK_NULL_VOID(cls);

    std::lock_guard<std::mutex> lock(g_touchInjectJniMutex);
    if (g_jobject != nullptr) {
        env->DeleteGlobalRef(g_jobject);
        g_jobject = nullptr;
    }
    g_jobject = env->NewGlobalRef(jobj);

    g_pluginClass.injectTouchEvent = env->GetMethodID(cls, METHOD_INJECT, SIGNATURE_INJECT);
    env->DeleteLocalRef(cls);
}

bool TouchInjectJni::InjectTouchEvent(int action, float x, float y, int64_t downTime, int64_t eventTime)
{
    auto env = Ace::Platform::JniEnvironment::GetInstance().GetJniEnv();
    CHECK_NULL_RETURN(env, false);

    std::lock_guard<std::mutex> lock(g_touchInjectJniMutex);
    CHECK_NULL_RETURN(g_jobject, false);
    CHECK_NULL_RETURN(g_pluginClass.injectTouchEvent, false);

    jboolean result = env->CallBooleanMethod(g_jobject, g_pluginClass.injectTouchEvent, static_cast<jint>(action),
        static_cast<jfloat>(x), static_cast<jfloat>(y), static_cast<jlong>(downTime), static_cast<jlong>(eventTime));
    if (env->ExceptionCheck()) {
        LOGE("TouchInjectJni::InjectTouchEvent Java exception occurred");
        env->ExceptionDescribe();
        env->ExceptionClear();
        return false;
    }

    return result == JNI_TRUE;
}
} // namespace OHOS::UiTest
