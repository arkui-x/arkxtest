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

#include "screen_capture_proxy.h"

#include "base/utils/utils.h"

namespace OHOS::UiTest {
ScreenCaptureProxy* ScreenCaptureProxy::GetInstance()
{
    static ScreenCaptureProxy instance;
    return &instance;
}

void ScreenCaptureProxy::SetDelegate(std::unique_ptr<ScreenCaptureInterface>&& delegate)
{
    delegate_ = std::move(delegate);
}

bool ScreenCaptureProxy::CaptureScreen(const std::string& savePath, const Rect& rect)
{
    CHECK_NULL_RETURN(delegate_, false);
    return delegate_->CaptureScreen(savePath, rect);
}
} // namespace OHOS::UiTest
