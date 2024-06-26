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

#include <memory>
#include <map>
#include "component_info.h"

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
    LONGCLICKABLE,
    ISBEFORE,
    ISAFTER,
    WITHIN
};

enum UiDirection : int32_t {
    LEFT = 0,
    RIGHT,
    UP,
    DOWN
};

enum MatchPattern : int32_t {
    EQUALS = 0,
    CONTAINS,
    STARTS_WITH,
    ENDS_WITH
};

struct Point {
    int x = 0;
    int y = 0;
};

struct PointPair {
    Point from;
    Point to;
};

/*
left 控件边框的左上角的X坐标。
top 控件边框的左上角的Y坐标。
right 控件边框的右下角的X坐标。
bottom 控件边框的右下角的Y坐标。
*/
struct Rect {
    int left;
    int top;
    int right;
    int bottom;
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

class PointerMatrix;
class Component;

class On {
public:
    On* Text(const string& text, MatchPattern pattern);
    On* Id(const string& id);
    On* Type(const string& type);
    On* Enabled(bool enabled);
    On* Focused(bool focused);
    On* Selected(bool selected);
    On* Clickable(bool clickable);
    On* LongClickable(bool longClickable);
    On* Scrollable(bool scrollable);
    On* Checkable(bool checkable);
    On* Checked(bool checked);
    On* IsBefore(On* on);
    On* IsAfter(On* on);
    On* WithIn(On* on);

    shared_ptr<string> id;
    shared_ptr<string> text;
    shared_ptr<string> type;
    shared_ptr<bool> clickable;
    shared_ptr<bool> longClickable;
    shared_ptr<bool> scrollable;
    shared_ptr<bool> enabled;
    shared_ptr<bool> focused;
    shared_ptr<bool> selected;
    shared_ptr<bool> checked;
    shared_ptr<bool> checkable;
    shared_ptr<On> isBefore;
    shared_ptr<On> isAfter;
    shared_ptr<On> withIn;
    MatchPattern pattern_ = MatchPattern::EQUALS;

    bool CompareText(const string& text) const;
    bool isEnter = false;
};

bool operator == (const On& on, const OHOS::Ace::Platform::ComponentInfo& info);

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
    void InputText(const string& text);
    void ClearText();
    void ScrollToTop(int speed);
    void ScrollToBottom(int speed);

    Rect GetBounds();
    void PinchOut(float scale);
    void PinchIn(float scale);

    void SetComponentInfo(const OHOS::Ace::Platform::ComponentInfo& com);
    OHOS::Ace::Platform::ComponentInfo GetComponentInfo();
    unique_ptr<Component> ScrollSearch(const On& on);
    Point GetBoundsCenter();
private:
    OHOS::Ace::Platform::ComponentInfo componentInfo_;
    shared_ptr<Component> parentComponent_;
};

class Driver {
public:
    Driver() = default;
    ~Driver() = default;

    bool AssertComponentExist(const On& on);
    void PressBack();

    void TriggerKey(int keyCode);
    void TriggerCombineKeys(int key0, int key1, int key2 = -1);
    bool InjectMultiPointerAction(PointerMatrix& pointers, uint32_t speed = 0);
    
    void DelayMs(int dur);
    void Click(int x, int y);
    void DoubleClick(int x, int y);
    void LongClick(int x, int y);
    void Swipe(int startx, int starty, int endx, int endy, uint32_t speed);
    void Fling(const Point& from, const Point& to, int stepLen, uint32_t speed = 0);
    void Fling(UiDirection direction, uint32_t speed = 0);
    unique_ptr<Component> FindComponent(const On& on);
    vector<unique_ptr<Component>> FindComponents(const On& on);
    void CalculateDirection(const OHOS::Ace::Platform::ComponentInfo& info,
        const UiDirection& direction, Point& from, Point& to);
};

class PointerMatrix {
public:
    PointerMatrix() = default;
    ~PointerMatrix() = default;
    PointerMatrix* Create(uint32_t fingers, uint32_t steps);
    void SetPoint(uint32_t finger, uint32_t step, Point& point);
    PointerMatrix& operator=(PointerMatrix&& other);
    uint32_t GetSteps() const;
    // finger, (step, point)
    std::map<int, std::map<int, Point>> fingerPointMap_;
private:
    uint32_t fingerNum_ = 0;
    uint32_t stepNum_ = 0;
};

} // namespace OHOS::UiTest

#endif // DRIVER_H
