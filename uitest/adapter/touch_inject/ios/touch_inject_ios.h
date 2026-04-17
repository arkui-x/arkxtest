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

#ifndef TEST_TESTFWK_ARKXTEST_UITEST_ADAPTER_TOUCH_INJECT_IOS_TOUCH_INJECT_IOS_H
#define TEST_TESTFWK_ARKXTEST_UITEST_ADAPTER_TOUCH_INJECT_IOS_TOUCH_INJECT_IOS_H

#include <cstdint>

namespace OHOS::UiTest {
bool InjectTouchEventOC(int action, float x, float y, int64_t downTime, int64_t eventTime);
} // namespace OHOS::UiTest

#endif // TEST_TESTFWK_ARKXTEST_UITEST_ADAPTER_TOUCH_INJECT_IOS_TOUCH_INJECT_IOS_H
