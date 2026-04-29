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

#ifndef TEST_TESTFWK_ARKXTEST_UITEST_CORE_COMMON_TYPE_H
#define TEST_TESTFWK_ARKXTEST_UITEST_CORE_COMMON_TYPE_H

#include <cstdint>

namespace OHOS::UiTest {
constexpr int32_t DEFAULT_LONG_CLICK_DURATION_MS = 1500;
inline constexpr char SCREEN_CAPTURE_INTERNAL_ERROR_MSG[] = "Failed to get display pixelMap";

enum CommonType : int32_t {
    ID = 0,
    TEXT,
    TYPE,
    CLICKABLE,
    CHECKABLE,
    CHECKED,
    SELECTED,
    SCROLLABLE,
    ENABLED,
    FOCUSED,
    LONGCLICKABLE,
    ISBEFORE,
    ISAFTER,
    WITHIN
};

enum UiDirection : int32_t { LEFT = 0, RIGHT, UP, DOWN };

enum MatchPattern : int32_t { EQUALS = 0, CONTAINS, STARTS_WITH, ENDS_WITH };

enum DisplayRotation : int32_t { ROTATION_0 = 0, ROTATION_90, ROTATION_180, ROTATION_270 };

struct Point {
    int x = 0;
    int y = 0;
};

struct PointPair {
    Point from;
    Point to;
};

struct Rect {
    int left;
    int top;
    int right;
    int bottom;
    int displayId;
};

enum UiTestErrCode : int32_t {
    ERR_OK = 0,
    ERROR_INVALID_DISPLAY_ID = -1,
    ERR_INTERNAL = -2,
    SCREEN_CAPTURE_INTERNAL_ERROR = 17000006,
};
} // namespace OHOS::UiTest

#endif // TEST_TESTFWK_ARKXTEST_UITEST_CORE_COMMON_TYPE_H
