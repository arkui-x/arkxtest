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

#include "touch_inject_proxy.h"

namespace OHOS::UiTest {
TouchInjectProxy* TouchInjectProxy::GetInstance()
{
    static TouchInjectProxy instance;
    return &instance;
}

bool TouchInjectProxy::InjectTouchEvent(int action, float x, float y, int64_t downTime, int64_t eventTime)
{
    if (!delegate_) {
        return false;
    }
    return delegate_->InjectTouchEvent(action, x, y, downTime, eventTime);
}
void TouchInjectProxy::SetDelegate(std::unique_ptr<TouchInjectInterface> delegate)
{
    delegate_ = std::move(delegate);
}
} // namespace OHOS::UiTest
