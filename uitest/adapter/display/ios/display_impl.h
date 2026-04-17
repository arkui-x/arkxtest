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

#ifndef OHOS_ACE_UITEST_PLATFORM_DISPLAY_IOS_IMPL_H
#define OHOS_ACE_UITEST_PLATFORM_DISPLAY_IOS_IMPL_H

#include "display_interface.h"

namespace OHOS::UiTest {
class DisplayImpl : public DisplayInterface {
public:
    DisplayImpl() = default;
    ~DisplayImpl() override = default;

    void SetDisplayRotation(const int rotation) override;
};
} // namespace OHOS::UiTest

#endif // OHOS_ACE_UITEST_PLATFORM_DISPLAY_IOS_IMPL_H