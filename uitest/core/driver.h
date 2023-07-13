/*
 * Copyright (c) 2023 Huawei Device Co., Ltd.
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

#ifndef DRIVER_H
#define DRIVER_H

#include "foundation/appframework/arkui/uicontent/component_info.h"

namespace OHOS::UiTest {
using namespace std;

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
    LONGCLICKABLE
};

enum MatchPattern : int32_t {
    EQUALS = 0,
    CONTAINS,
    STARTS_WITH,
    ENDS_WITH
};

struct Point {
    int x;
    int y;
};

/**
 * Options of the UI operations, initialized with system default values.
 **/
class UiOpArgs {
public:
    const uint32_t maxSwipeVelocityPps_ = 15000;
    const uint32_t minSwipeVelocityPps_ = 200;
    const uint32_t defaultVelocityPps_ = 600;
    const uint32_t minFlingVelocityPps_ = 200;
    const uint32_t maxFlingVelocityPps_ = 40000;
    uint32_t clickHoldMs_ = 100;
    uint32_t longClickHoldMs_ = 1500;
    uint32_t doubleClickIntervalMs_ = 200;
    uint16_t swipeStepsCounts_ = 50;
};

class On {
public:
    On* Text(const string &text, MatchPattern pattern);
    On* Id(const string &id);
    On* Type(const string &type);
    On* Enabled(bool enabled);
    On* Focused(bool focused);
    On* Selected(bool selected);
    On* Clickable(bool clickable);
    On* LongClickable(bool longClickable);
    On* Scrollable(bool scrollable);
    On* Checkable(bool checkable);
    On* Checked(bool checked);

    std::vector<OHOS::UiTest::CommonType> commonType;
    string id;
    string text;
    string type;
    bool clickable;
    bool longClickable;
    bool scrollable;
    bool enabled;
    bool focused;
    bool selected;
    bool checked;
    bool checkable;
    MatchPattern pattern_ = MatchPattern::EQUALS;
};

class Component {
public:
    void Click();
    void DoubleClick();
    void LongClick();
    string GetId();
    string GetText();
    string GetType();
    unique_ptr<bool> IsClickable();
    unique_ptr<bool> IsLongClickable();
    unique_ptr<bool> IsScrollable();
    unique_ptr<bool> IsEnabled();
    unique_ptr<bool> IsFocused();
    unique_ptr<bool> IsSelected();
    unique_ptr<bool> IsChecked();
    unique_ptr<bool> IsCheckable();
    void InputText(const string &text);
    void ClearText();
    void ScrollToTop(int speed);
    void ScrollToBottom(int speed);
    void SetComponentInfo(OHOS::Ace::Platform::ComponentInfo& com);
    unique_ptr<Component> ScrollSearch(On on);
    Point GetBoundsCenter();

private:
    OHOS::Ace::Platform::ComponentInfo componentInfo_;
};

class Driver {
public:
    Driver() = default;
    ~Driver() = default;

    bool AssertComponentExist(On &on);
    void PressBack();
    void DelayMs(int dur);
    void Click(int x, int y);
    void DoubleClick(int x, int y);
    void LongClick(int x, int y);
    void Swipe(int startx, int starty, int endx, int endy, int speed);
    void Fling(Point& from, Point& to, int stepLen, int speed);
    unique_ptr<Component> FindComponent(On on);
    vector<unique_ptr<Component>> FindComponents(On on);
};
} // namespace OHOS::UiTest

#endif // DRIVER_H
