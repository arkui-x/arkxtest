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

#include <mutex>

#include "inner_api/plugin_utils_inner.h"
#include "screen_capture_delegate.h"
#include "screen_capture_proxy.h"
#include "ui/base/utils/utils.h"

#include "adapter/android/entrance/java/jni/jni_environment.h"
#include "base/log/log_wrapper.h"
#include "base/utils/macros.h"

namespace OHOS::UiTest {
using namespace Ace::Platform;
namespace {
static std::mutex g_screenCaptureJniMutex;
static const char* const SCREEN_CAPTURE_HELPER_CLASS_NAME = "ohos/ace/plugin/screencapture/ScreenCaptureHelperBase";
static const char* const CAPTURE_REGION_CLASS_NAME =
    "ohos/ace/plugin/screencapture/ScreenCaptureHelperBase$CaptureRegion";

static const JNINativeMethod METHODS[] = {
    { "nativeInit", "()V", reinterpret_cast<void*>(ScreenCaptureJni::NativeInit) },
};

static const char METHOD_CAPTURE_SCREEN[] = "captureScreen";
static const char METHOD_REGION_CONSTRUCTOR[] = "<init>";
static const char SIGNATURE_CAPTURE_SCREEN[] =
    "(Ljava/lang/String;Lohos/ace/plugin/screencapture/ScreenCaptureHelperBase$CaptureRegion;I)I";
static const char SIGNATURE_REGION_CONSTRUCTOR[] = "(IIII)V";

jobject g_jobject = nullptr;

struct {
    jmethodID captureScreen;
    jclass captureRegionClass;
    jmethodID captureRegionCtor;
} g_pluginClass;
} // namespace

bool ScreenCaptureJni::Register(void* env)
{
    auto* jniEnv = static_cast<JNIEnv*>(env);
    CHECK_NULL_RETURN(jniEnv, false);

    jclass cls = jniEnv->FindClass(SCREEN_CAPTURE_HELPER_CLASS_NAME);
    CHECK_NULL_RETURN(cls, false);

    bool ret = jniEnv->RegisterNatives(cls, METHODS, sizeof(METHODS) / sizeof(METHODS[0])) == 0;
    jniEnv->DeleteLocalRef(cls);
    CHECK_NULL_RETURN(ret, false);

    OnJniRegistered();
    return true;
}

void ScreenCaptureJni::OnJniRegistered()
{
    ScreenCaptureProxy::GetInstance()->SetDelegate(std::make_unique<ScreenCaptureDelegate>());
}

void ScreenCaptureJni::NativeInit(JNIEnv* env, jobject jobj)
{
    CHECK_NULL_VOID(env);
    CHECK_NULL_VOID(jobj);

    jclass cls = env->GetObjectClass(jobj);
    CHECK_NULL_VOID(cls);

    std::lock_guard<std::mutex> lock(g_screenCaptureJniMutex);
    if (g_jobject != nullptr) {
        env->DeleteGlobalRef(g_jobject);
        g_jobject = nullptr;
    }
    g_jobject = env->NewGlobalRef(jobj);

    g_pluginClass.captureScreen = env->GetMethodID(cls, METHOD_CAPTURE_SCREEN, SIGNATURE_CAPTURE_SCREEN);
    jclass regionCls = env->FindClass(CAPTURE_REGION_CLASS_NAME);

    if (g_pluginClass.captureRegionClass != nullptr) {
        env->DeleteGlobalRef(g_pluginClass.captureRegionClass);
        g_pluginClass.captureRegionClass = nullptr;
    }
    g_pluginClass.captureRegionClass = (jclass)env->NewGlobalRef(regionCls);
    g_pluginClass.captureRegionCtor =
        env->GetMethodID(regionCls, METHOD_REGION_CONSTRUCTOR, SIGNATURE_REGION_CONSTRUCTOR);
    env->DeleteLocalRef(regionCls);
    env->DeleteLocalRef(cls);
}

int32_t ScreenCaptureJni::CaptureScreen(const std::string& savePath, const Rect& rect)
{
    if (savePath.empty()) {
        LOGE("ScreenCaptureJni::CaptureScreen savePath is empty");
        return SCREEN_CAPTURE_STATUS_INVALID_PATH;
    }

    std::lock_guard<std::mutex> lock(g_screenCaptureJniMutex);
    auto env = Ace::Platform::JniEnvironment::GetInstance().GetJniEnv();
    CHECK_NULL_RETURN(env, SCREEN_CAPTURE_STATUS_FAILED);
    CHECK_NULL_RETURN(g_jobject, SCREEN_CAPTURE_STATUS_FAILED);
    CHECK_NULL_RETURN(g_pluginClass.captureScreen, SCREEN_CAPTURE_STATUS_FAILED);

    jstring jPath = env->NewStringUTF(savePath.c_str());
    CHECK_NULL_RETURN(jPath, SCREEN_CAPTURE_STATUS_FAILED);

    jobject regionObj =
        env->NewObject(g_pluginClass.captureRegionClass, g_pluginClass.captureRegionCtor, static_cast<jint>(rect.left),
            static_cast<jint>(rect.top), static_cast<jint>(rect.right), static_cast<jint>(rect.bottom));
    if (regionObj == nullptr) {
        env->DeleteLocalRef(jPath);
        return SCREEN_CAPTURE_STATUS_FAILED;
    }

    jint result = env->CallIntMethod(
        g_jobject, g_pluginClass.captureScreen, jPath, regionObj, static_cast<jint>(rect.displayId));

    if (env->ExceptionCheck()) {
        LOGE("ScreenCaptureJni::CaptureScreen Exception occurred during captureScreen call");
        env->ExceptionDescribe();
        env->ExceptionClear();
        result = SCREEN_CAPTURE_STATUS_FAILED;
    }

    env->DeleteLocalRef(jPath);
    env->DeleteLocalRef(regionObj);

    return static_cast<int32_t>(result);
}
} // namespace OHOS::UiTest
