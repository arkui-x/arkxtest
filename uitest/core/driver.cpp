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

#include "driver.h"

#include <future>
#include <vector>
#include <math.h>
#include "ability_delegator/ability_delegator_registry.h"
#include "accessibility_node.h"
#include "core/event/key_event.h"
#include "core/event/touch_event.h"
#include "ui_content.h"
#include "utils/log.h"

namespace OHOS::UiTest {
using namespace std;

static constexpr const int32_t DOUBLE_CLICK = 2;
static constexpr const char UPPER_A = 'A';
static constexpr const char LOWER_A = 'a';
static constexpr const char DEF_NUMBER = '0';
static constexpr const int32_t DELAY_TIME= 100;
constexpr size_t INDEX_ZERO = 0;
constexpr size_t INDEX_ONE = 1;
constexpr size_t INDEX_TWO = 2;
constexpr size_t INDEX_THREE = 3;
constexpr size_t INDEX_FOUR = 4;
constexpr size_t INDEX_FIVE = 5;
constexpr size_t INDEX_SIX = 6;
static bool BEFORE_FLAG = false;
static bool AFTER_FLAG = false;

int32_t Findkeycode(const char text)
{
    if(isupper(text)) {
        return (text - UPPER_A + static_cast<int32_t>(Ace::KeyCode::KEY_A));
    }

    if(islower(text)) {
        return (text - LOWER_A + static_cast<int32_t>(Ace::KeyCode::KEY_A));
    }

    if (isdigit(text)) {
        return (text - DEF_NUMBER + static_cast<int32_t>(Ace::KeyCode::KEY_0));
    }

    HILOG_DEBUG("Please enter lowercase letters and numbers");
    return -1;
}

int64_t getCurrentTimeMillis()
{
    auto now = std::chrono::system_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
}

inline Ace::TimeStamp TimeStamp(int64_t currentTimeMillis)
{
    return Ace::TimeStamp(std::chrono::milliseconds(currentTimeMillis));
}

Ace::Platform::UIContent* GetUIContent()
{
    auto delegator = AppExecFwk::AbilityDelegatorRegistry::GetAbilityDelegator();
    if (delegator == nullptr) {
        HILOG_ERROR("Driver GetUIContent failed. delegator is not initialized");
        return nullptr;
    }
    auto topAbility = delegator->GetCurrentTopAbility();
    CHECK_NULL_RETURN(topAbility, nullptr);
    return delegator->GetUIContent(topAbility->instanceId_);
}

static void PackagingEvent(Ace::TouchEvent& event, Ace::TimeStamp time, Ace::TouchType type, const Point& point)
{
    event.time = time;
    event.type = type;
    event.x = point.x;
    event.y = point.y;
    event.screenX = point.x;
    event.screenY = point.y;
    event = event.UpdatePointers();
}

Rect GetBounds(const OHOS::Ace::Platform::ComponentInfo& component)
{
    Rect rect;
    rect.left = component.left;
    rect.right = component.left + component.width;
    rect.top = component.top;
    rect.bottom = component.top + component.height;
    return rect;
}

bool Driver::AssertComponentExist(const On& on)
{
    HILOG_DEBUG("Driver::AssertComponentExist");
    auto component = make_unique<Component>();
    component = FindComponent(on);
    return component != nullptr;
}

void Driver::PressBack()
{
    HILOG_DEBUG("Driver::PressBack called");
    auto uicontent = GetUIContent();
    CHECK_NULL_VOID(uicontent);
    uicontent->ProcessBackPressed();
}

void Driver::TriggerKey(int keyCode)
{
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    if (keyCode == -1) {
        return;
    }
    HILOG_DEBUG("Driver::TriggerKey: %{public}d", keyCode);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(keyCode), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(keyCode), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    DelayMs(DELAY_TIME);
}

void Driver::TriggerCombineKeys(int key0, int key1, int key2)
{
    auto uiContent = GetUIContent();
    if (key0 == -1 && key1 == -1) {
        return;
    }
    HILOG_DEBUG("Driver::TriggerCombineKeys: %{public}d %{public}d %{public}d", key0, key1, key2);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(key0), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(key1), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    if (key2 != -1) {
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key2), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    }
    DelayMs(DELAY_TIME);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(key0), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(key1), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    if (key2 != -1) {
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key2), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    }
}

bool Driver::InjectMultiPointerAction(PointerMatrix& pointers, uint32_t speed)
{
    uint32_t fingers = pointers.GetFingers();
    uint32_t steps = pointers.GetSteps();
    if (steps <= 1) {
        HILOG_ERROR("Driver::InjectMultiPointerAction no move.");
        return false;
    }

    // pair Point for ready
    vector<PointPair> pointPairVec;
    for (uint16_t step = 0; step < steps - 1; step++) {
        for (auto it : pointers.GetPointMap()) {
            PointPair listTemp;
            listTemp.from = it.second[step];
            listTemp.to = it.second[step + 1];
            pointPairVec.push_back(listTemp);
        }
    }

    auto uiContent = GetUIContent();
    CHECK_NULL_RETURN(uiContent, false);
    UiOpArgs options;
    uint32_t injectSpeed = speed;
    if (speed < options.minFlingVelocityPps_ || speed > options.maxFlingVelocityPps_) {
        injectSpeed = options.defaultVelocityPps_;
    }
    std::vector<Ace::TouchEvent> injectEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();
    for (auto it : pointPairVec) {
        Point start = it.from;
        Point end = it.to;
        Ace::TouchEvent downEvent;
        PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, start);
        injectEvents.push_back(downEvent);

        const int distanceX = end.x - start.x;
        const int distanceY = end.y - start.y;
        const int distance = sqrt(distanceX * distanceX + distanceY * distanceY);
        const uint32_t timeCostMs = (uint32_t)((distance * 1000) / injectSpeed);
        const uint32_t timeOffsetMs = timeCostMs / INDEX_TWO;
        Ace::TouchEvent moveEvent;
        moveEvent = moveEvent.UpdatePointers();
        PackagingEvent(moveEvent, TimeStamp(currentTimeMillis + timeOffsetMs),
            Ace::TouchType::MOVE, end);
        injectEvents.push_back(moveEvent);

        Ace::TouchEvent upEvent;
        PackagingEvent(upEvent, TimeStamp(currentTimeMillis + timeCostMs), Ace::TouchType::UP, end);
        injectEvents.push_back(upEvent);

    }
    uiContent->ProcessBasicEvent(injectEvents);

    return true;
}

void Driver::DelayMs(int dur)
{
    HILOG_DEBUG("Driver::DelayMs duration=%d", dur);
    if (dur > 0) {
        this_thread::sleep_for(chrono::milliseconds(dur));
    }
}

void Driver::Click(int x, int y)
{
    HILOG_DEBUG("Driver::Click x=%d, y=%d", x, y);
    std::vector<Ace::TouchEvent> clickEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, { x, y });
    clickEvents.push_back(downEvent);

    Ace::TouchEvent upEvent;
    UiOpArgs options;
    PackagingEvent(upEvent, TimeStamp(currentTimeMillis + options.clickHoldMs_), Ace::TouchType::UP, { x, y });
    clickEvents.push_back(upEvent);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessBasicEvent(clickEvents);
}

void Driver::DoubleClick(int x, int y)
{
    HILOG_DEBUG("Driver::Click x=%d, y=%d", x, y);
    std::vector<Ace::TouchEvent> clickEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    for (int i = 0; i < DOUBLE_CLICK; i++) {
        Ace::TouchEvent downEvent;
        PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, { x, y });
        clickEvents.push_back(downEvent);

        Ace::TouchEvent upEvent;
        UiOpArgs options;
        PackagingEvent(upEvent, TimeStamp(currentTimeMillis + options.clickHoldMs_), Ace::TouchType::UP, { x, y });
        clickEvents.push_back(upEvent);
    }

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessBasicEvent(clickEvents);
}

void Driver::LongClick(int x, int y)
{
    HILOG_DEBUG("Driver::LongClick x=%d, y=%d", x, y);
    std::vector<Ace::TouchEvent> clickEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, { x, y });
    clickEvents.push_back(downEvent);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessBasicEvent(clickEvents);
}

void Driver::Swipe(int startx, int starty, int endx, int endy, uint32_t speed)
{
    HILOG_DEBUG("Driver::Swipe from (%d, %d) to (%d, %d), speed:%d", startx, starty, endx, endy, speed);
    std::vector<Ace::TouchEvent> swipeEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, { startx, starty });
    swipeEvents.push_back(downEvent);

    UiOpArgs options;
    uint32_t swipeSpeed = speed;
    if (speed < options.minSwipeVelocityPps_ || speed > options.maxSwipeVelocityPps_) {
        swipeSpeed = options.defaultVelocityPps_;
    }

    const int distanceX = endx - startx;
    const int distanceY = endy - starty;
    const int distance = sqrt(distanceX * distanceX + distanceY * distanceY);
    const uint32_t timeCostMs = (uint32_t)((distance * 1000) / swipeSpeed);

    if (distance < 1) {
        HILOG_ERROR("Driver::Swipe ignored. distance value is illegal");
        return;
    }

    const uint16_t steps = options.swipeStepsCounts_;

    for (uint16_t step = 1; step < steps; step++) {
        const float pointX = startx + (distanceX * step) / steps;
        const float pointY = starty + (distanceY * step) / steps;
        const uint32_t timeOffsetMs = (timeCostMs * step) / steps;

        Ace::TouchEvent moveEvent;
        moveEvent = moveEvent.UpdatePointers();
        PackagingEvent(moveEvent, TimeStamp(currentTimeMillis + timeOffsetMs),
            Ace::TouchType::MOVE, { pointX, pointY });
        swipeEvents.push_back(moveEvent);
    }

    Ace::TouchEvent upEvent;
    PackagingEvent(upEvent, TimeStamp(currentTimeMillis + timeCostMs), Ace::TouchType::UP, { endx, endy });
    swipeEvents.push_back(upEvent);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    uiContent->ProcessBasicEvent(swipeEvents);
}

void Driver::Fling(const Point& from, const Point& to, int stepLen, uint32_t speed)
{
    HILOG_DEBUG(
        "Driver::Fling from (%d, %d) to (%d, %d), stepLen:%d, speed:%d", from.x, from.y, to.x, to.y, stepLen, speed);
    std::vector<Ace::TouchEvent> flingEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, from);
    flingEvents.push_back(downEvent);

    UiOpArgs options;
    uint32_t flingSpeed = speed;

    if (speed < options.minFlingVelocityPps_ || speed > options.maxFlingVelocityPps_) {
        flingSpeed = options.defaultVelocityPps_;
    }

    const int distanceX = to.x - from.x;
    const int distanceY = to.y - from.y;
    const int distance = sqrt(distanceX * distanceX + distanceY * distanceY);
    const uint32_t timeCostMs = (uint32_t)((distance * 1000) / flingSpeed);
    if (distance < stepLen) {
        HILOG_ERROR("Driver::Fling ignored. stepLen is illegal");
        return;
    }
    const uint16_t steps = distance / stepLen;

    for (uint16_t step = 1; step < steps; step++) {
        const float pointX = from.x + (distanceX * step) / steps;
        const float pointY = from.y + (distanceY * step) / steps;
        const uint32_t timeOffsetMs = (timeCostMs * step) / steps;
        Ace::TouchEvent moveEvent;
        PackagingEvent(moveEvent, TimeStamp(currentTimeMillis + timeOffsetMs),
            Ace::TouchType::MOVE, { pointX, pointY });
        flingEvents.push_back(moveEvent);
    }

    Ace::TouchEvent upEvent;
    PackagingEvent(upEvent, TimeStamp(currentTimeMillis + timeCostMs), Ace::TouchType::UP, to);
    flingEvents.push_back(upEvent);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    uiContent->ProcessBasicEvent(flingEvents);
}
// 默认左上角原点
void Driver::CalculateDirection(const OHOS::Ace::Platform::ComponentInfo& info,
    const UiDirection& direction, Point& from, Point& to)
{
    // 滑动距离要大于1/2才能更有效的滑动屏幕，尤其在左右滑动时
    switch (direction) {
        case UiDirection::LEFT : // 往左滑
            from.x = info.top + info.width / INDEX_SIX;
            from.y = info.left + info.height / INDEX_TWO; // 横向居中
            to.x = from.x - info.width * INDEX_TWO / INDEX_THREE;
            to.y = from.y;
            break;
        case UiDirection::RIGHT : // 往右滑
            from.x = info.top + info.width * INDEX_FIVE / INDEX_SIX;
            from.y = info.left + info.height / INDEX_TWO; // 横向居中
            to.x = from.x + info.width * INDEX_TWO / INDEX_THREE;
            to.y = from.y;
            break;
        case UiDirection::UP : // 往上滑
            from.x = info.top + info.width / INDEX_TWO; // 纵向居中
            from.y = info.left + info.height / INDEX_SIX;
            to.x = from.x;
            to.y = from.y - info.height * INDEX_TWO / INDEX_THREE;
            break;
        case UiDirection::DOWN : // 往下滑
            from.x = info.top + info.width / INDEX_TWO; // 纵向居中
            from.y = info.left + info.height * INDEX_FIVE / INDEX_SIX;
            to.x = from.x;
            to.y = from.y + info.height * INDEX_TWO / INDEX_THREE;
            break;
        default:
            from.x = info.top + info.width / INDEX_SIX;
            from.y = info.left + info.height / INDEX_TWO; // 横向居中
            to.x = from.x - info.width * INDEX_TWO / INDEX_THREE;
            to.y = from.y;
    }
}

void Driver::Fling(UiDirection direction, uint32_t speed)
{
    UiOpArgs options;
    uint32_t flingSpeed = speed;
    if (speed < options.minFlingVelocityPps_ || speed > options.maxFlingVelocityPps_) {
        flingSpeed = options.defaultVelocityPps_;
    }
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    uiContent->GetAllComponents(0, info);
    Point from, to;
    CalculateDirection(info, direction, from, to);
    const int distanceX = from.x - to.x;
    const int distanceY = from.y - to.y;
    const int distance = sqrt(distanceX * distanceX + distanceY * distanceY);
    if (distance == 0) {
        HILOG_ERROR("Driver::Fling direction ignored. distance is illegal");
        return;
    }
    const uint32_t timeCostMs = (uint32_t)((distance * 1000) / flingSpeed);

    std::vector<Ace::TouchEvent> flingEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();
    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, from);
    flingEvents.push_back(downEvent);

    const float pointX = from.x + distanceX;
    const float pointY = from.y + distanceY;
    Ace::TouchEvent moveEvent;
    PackagingEvent(moveEvent, TimeStamp(currentTimeMillis + timeCostMs),
        Ace::TouchType::MOVE, { pointX, pointY });
    flingEvents.push_back(moveEvent);

    Ace::TouchEvent upEvent;
    PackagingEvent(upEvent, TimeStamp(currentTimeMillis + timeCostMs), Ace::TouchType::UP, to);
    flingEvents.push_back(upEvent);

    uiContent->ProcessBasicEvent(flingEvents);
}

void Component::Click()
{
    HILOG_DEBUG("Component::Click");
    Point point = GetBoundsCenter();
    Driver driver;
    driver.Click(point.x, point.y);
}

void Component::DoubleClick()
{
    HILOG_DEBUG("Component::DoubleClick");
    Point point = GetBoundsCenter();
    Driver driver;
    driver.DoubleClick(point.x, point.y);
}

void Component::LongClick()
{
    HILOG_DEBUG("Component::LongClick");
    Point point = GetBoundsCenter();
    Driver driver;
    driver.LongClick(point.x, point.y);
}

string Component::GetId()
{
    HILOG_DEBUG("Component::GetId");
    return componentInfo_.compid;
}

string Component::GetText()
{
    HILOG_DEBUG("Component::GetText");
    return componentInfo_.text;
}

string Component::GetType()
{
    HILOG_DEBUG("Component::GetType");
    return componentInfo_.type;
}

unique_ptr<bool> Component::IsClickable()
{
    auto clickable = make_unique<bool>();
    *clickable = componentInfo_.clickable;
    HILOG_DEBUG("Component::Clickable: %{public}d", *clickable);
    return clickable;
}

unique_ptr<bool> Component::IsLongClickable()
{
    auto longClickable = make_unique<bool>();
    *longClickable = componentInfo_.longClickable;
    HILOG_DEBUG("Component::LongClickable: %{public}d", *longClickable);
    return longClickable;
}

unique_ptr<bool> Component::IsScrollable()
{
    auto scrollable = make_unique<bool>();
    *scrollable = componentInfo_.scrollable;
    HILOG_DEBUG("Component::scrollable: %{public}d", *scrollable);
    return scrollable;
}

unique_ptr<bool> Component::IsEnabled()
{
    auto enabled = make_unique<bool>();
    *enabled = componentInfo_.enabled;
    HILOG_DEBUG("Component::enabled: %{public}d", *enabled);
    return enabled;
}

unique_ptr<bool> Component::IsFocused()
{
    auto focused = make_unique<bool>();
    *focused = componentInfo_.focused;
    HILOG_DEBUG("Component::focused: %{public}d", *focused);
    return focused;
}

unique_ptr<bool> Component::IsSelected()
{
    auto selected = make_unique<bool>();
    *selected = componentInfo_.selected;
    HILOG_DEBUG("Component::selected: %{public}d", *selected);
    return selected;
}

unique_ptr<bool> Component::IsChecked()
{
    auto checked = make_unique<bool>();
    *checked = componentInfo_.checked;
    HILOG_DEBUG("Component::checked: %{public}d", *checked);
    return checked;
}

unique_ptr<bool> Component::IsCheckable()
{
    auto checkable = make_unique<bool>();
    *checkable = componentInfo_.checkable;
    HILOG_DEBUG("Component::checkable: %{public}d", *checkable);
    return checkable;
}

void Component::InputText(const string& text)
{
    HILOG_DEBUG("Component::InputText");
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_MOVE_END), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_MOVE_END), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    Driver driver;
    for (uint32_t i = 0; i < text.length(); i++) {
        int32_t keycode = Findkeycode(text[i]);
        if (keycode == -1) {
            continue;
        }
        componentInfo_.text += text[i];
        HILOG_DEBUG("Component::InputText: %{public}d", keycode);
        driver.DelayMs(DELAY_TIME);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(keycode), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(keycode), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    }
}

void Component::ClearText()
{
    HILOG_DEBUG("Component::ClearText length:%d", componentInfo_.text.length());
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_MOVE_END), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_MOVE_END), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    Driver driver;
    for (int i = 0; i < componentInfo_.text.length(); i++) {
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DEL), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DEL), static_cast<int32_t>(Ace::KeyAction::UP), 0);
        driver.DelayMs(DELAY_TIME);
    }
}

void Component::ScrollToTop(int speed)
{
    HILOG_DEBUG("Component::ScrollToTop speed:%d", speed);
    if (!IsScrollable()) {
        HILOG_ERROR("Component::ScrollToTop current component is not scrollable");
        return;
    }

    HILOG_DEBUG("Component::ScrollToTop child.size:%d", componentInfo_.children.size());
    if (componentInfo_.children.size() < 1) {
        HILOG_ERROR("Component::ScrollToTop current scollable component has no child");
        return;
    }

    OHOS::Ace::Platform::ComponentInfo flex = componentInfo_.children.front();
    HILOG_DEBUG("Component::ScrollToTop flex.size:%d", flex.children.size());
    if (flex.children.size() < 1) {
        HILOG_ERROR("Component::ScrollToTop flex has no child");
        return;
    }

    if (flex.children.front().top >= (componentInfo_.top)) {
        HILOG_ERROR("Component::ScrollToTop component is already in the top");
        return;
    }

    auto startx = componentInfo_.left + componentInfo_.width / 2;
    auto endx = startx;
    auto starty = componentInfo_.top + componentInfo_.height / 2;
    auto stepLen = std::min(200.0f, componentInfo_.height / 4);
    auto endy = starty + stepLen;

    auto top = componentInfo_.top;
    auto firstChildTop = flex.children.front().top;
    auto firstHeight = flex.children.front().height;

    auto swipeTimes = std::abs((top - firstChildTop + firstHeight) / (endy - starty)) + 1;
    int step = 0;
    Driver driver;
    while (step < swipeTimes) {
        driver.Swipe(startx, starty, endx, endy, speed);
        step++;
    }
}

void Component::ScrollToBottom(int speed)
{
    HILOG_DEBUG("Component::ScrollToBottom speed:%d", speed);
    if (!IsScrollable()) {
        HILOG_ERROR("Component::ScrollToBottom current component is not scrollable");
        return;
    }

    HILOG_DEBUG("Component::scrollToBottom child.size:%d", componentInfo_.children.size());
    if (componentInfo_.children.size() < 1) {
        HILOG_ERROR("Component::ScrollToBottom current scollable component has no child");
        return;
    }

    OHOS::Ace::Platform::ComponentInfo flex = componentInfo_.children.front();
    HILOG_DEBUG("Component::scrollToBottom flex.size:%d", flex.children.size());
    if (flex.children.size() < 1) {
        HILOG_ERROR("Component::ScrollToBottom flex has no child");
        return;
    }

    if (flex.children.back().top <= (componentInfo_.top + componentInfo_.height)) {
        HILOG_ERROR("Component::ScrollToBottom component is already in the bottom");
        return;
    }

    auto startx = componentInfo_.left + componentInfo_.width / 2;
    auto endx = startx;
    auto starty = componentInfo_.top + componentInfo_.height / 2;
    auto stepLen = std::min(200.0f, componentInfo_.height / 4);
    auto endy = starty - stepLen;

    auto bottom = componentInfo_.top + componentInfo_.height;
    auto lastBottom = flex.children.back().top + flex.children.back().height;
    auto lastHeight = flex.children.back().height;

    auto swipeTimes = std::abs((lastBottom - bottom + lastHeight) / (endy - starty)) + 1;
    int step = 0;
    Driver driver;
    while (step < swipeTimes) {
        driver.Swipe(startx, starty, endx, endy, speed);
        step++;
    }
}
/*
componentInfo_:
left    number    矩形区域的左边界，单位为px，该参数为整数。
top number    矩形区域的上边界，单位为px，该参数应为整数。
width   number    矩形区域的宽度，单位为px，该参数应为整数。
height  number    矩形区域的高度，单位为px，该参数应为整数。

Rect:
left    number  控件边框的左上角的X坐标。
top    number  控件边框的左上角的Y坐标。
right    number  控件边框的右下角的X坐标。
bottom    number  控件边框的右下角的Y坐标。
*/
Rect Component::GetBounds()
{
    Rect rect;
    rect.left = componentInfo_.left;
    rect.right = componentInfo_.left + componentInfo_.width;
    rect.top = componentInfo_.top;
    rect.bottom = componentInfo_.top + componentInfo_.height;
    return rect;
}

void MakeTouchEvent(int64_t curTimeMillis, uint32_t timeCostMs, Point from, Point to,
    std::vector<Ace::TouchEvent>& moveEvents)
{
     Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(curTimeMillis), Ace::TouchType::DOWN, from);
    moveEvents.push_back(downEvent);

    Ace::TouchEvent moveEvent;
    PackagingEvent(moveEvent, TimeStamp(curTimeMillis + timeCostMs),
        Ace::TouchType::MOVE, to);
    moveEvents.push_back(moveEvent);

    Ace::TouchEvent upEvent;
    PackagingEvent(upEvent, TimeStamp(curTimeMillis + timeCostMs), Ace::TouchType::UP, to);
    moveEvents.push_back(upEvent);
}

void Component::PinchOut(float scale)
{
    HILOG_DEBUG("Component::PinchOut");
    if (scale <= 1.0f) {
        HILOG_DEBUG("Component::PinchOut scale[%f] <= 1.0f", scale);
        return;
    }
    float scaleOpt = scale - 1.0;
    Rect rect = GetBounds();
    // 捏合 两指操作距离 = 两指起点距离 * 倍数
    Point fromUp, toUp, fromDown, toDown;
    Point center = GetBoundsCenter();
    // 纵向捏合放大，默认起点两指距离为高度的一半
    float disH = componentInfo_.height * scaleOpt / INDEX_TWO;
    fromUp.x = center.x;
    fromUp.y = center.y - componentInfo_.height / INDEX_FOUR;
    fromDown.x = center.x;
    fromDown.y = center.y + componentInfo_.height / INDEX_FOUR;
    toUp.x = fromUp.x;
    toUp.y = fromUp.y - disH;
    toDown.x = fromDown.x;
    toDown.y = fromDown.y + disH;

    const int distanceX = fromUp.x - toUp.x;
    const int distanceY = fromUp.y - toUp.y;
    const int distance = sqrt(distanceX * distanceX + distanceY * distanceY);
    if (distance == 0) {
        HILOG_ERROR("Driver::PinchOut direction ignored. distance is illegal");
        return;
    }
    UiOpArgs options;
    uint32_t flingSpeed = options.defaultVelocityPps_;
    const uint32_t timeCostMs = (uint32_t)((distance * 1000) / flingSpeed);
    int64_t currentTimeMillis = getCurrentTimeMillis();
    std::vector<Ace::TouchEvent> flingEvents, flingEvents2;
    MakeTouchEvent(currentTimeMillis, timeCostMs, fromUp, toUp, flingEvents);
    MakeTouchEvent(currentTimeMillis, timeCostMs, fromDown, toDown, flingEvents2);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    uiContent->ProcessBasicEvent(flingEvents);
    uiContent->ProcessBasicEvent(flingEvents2);

    // set new
    componentInfo_.width = componentInfo_.width * scale;
    componentInfo_.height = componentInfo_.height * scale;
    componentInfo_.left = center.x - componentInfo_.width / 2;
    componentInfo_.top = center.y - componentInfo_.height / 2;
    HILOG_DEBUG("Component::PinchOut left:%f top:%f width:%f height:%f  x:%d  y:%d",
        componentInfo_.left, componentInfo_.top, componentInfo_.width, componentInfo_.height,
        center.x, center.y);
}

void Component::PinchIn(float scale)
{
    HILOG_DEBUG("Component::PinchIn");
    if (scale >= 1.0f || scale <= 0.001f) {
        HILOG_DEBUG("Component::PinchIn scale[%f] invalid", scale);
        return;
    }
    Rect rect = GetBounds();
    // 捏合 两指操作距离 = 两指起点距离 * 倍数
    Point fromUp, toUp, fromDown, toDown;
    Point center = GetBoundsCenter();
    // 纵向捏合缩小，默认起点两指距离为高度减1
    float disH = (componentInfo_.height - INDEX_TWO) * scale;
    fromUp.x = center.x;
    fromUp.y = rect.top + INDEX_ONE;
    fromDown.x = center.x;
    fromDown.y = rect.bottom - INDEX_ONE;
    toUp.x = fromUp.x;
    toUp.y = fromUp.y + disH;
    toDown.x = fromDown.x;
    toDown.y = fromDown.y - disH;

    const int distanceX = fromUp.x - toUp.x;
    const int distanceY = fromUp.y - toUp.y;
    const int distance = sqrt(distanceX * distanceX + distanceY * distanceY);
    if (distance == 0) {
        HILOG_ERROR("Driver::Fling direction ignored. distance is illegal");
        return;
    }
    UiOpArgs options;
    uint32_t flingSpeed = options.defaultVelocityPps_;
    const uint32_t timeCostMs = (uint32_t)((distance * 1000) / flingSpeed);
    int64_t currentTimeMillis = getCurrentTimeMillis();
    std::vector<Ace::TouchEvent> flingEvents, flingEvents2;
    MakeTouchEvent(currentTimeMillis, timeCostMs, fromUp, toUp, flingEvents);
    MakeTouchEvent(currentTimeMillis, timeCostMs, fromDown, toDown, flingEvents2);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    uiContent->ProcessBasicEvent(flingEvents);
    uiContent->ProcessBasicEvent(flingEvents2);

    // set new
    componentInfo_.width = componentInfo_.width * scale;
    componentInfo_.height = componentInfo_.height * scale;
    componentInfo_.left = center.x - componentInfo_.width / 2;
    componentInfo_.top = center.y - componentInfo_.height / 2;
    HILOG_DEBUG("Component::PinchOut left:%f top:%f width:%f height:%f  x:%d  y:%d",
        componentInfo_.left, componentInfo_.top, componentInfo_.width, componentInfo_.height,
        center.x, center.y);
}

void Component::SetComponentInfo(const OHOS::Ace::Platform::ComponentInfo& com)
{
    componentInfo_ = com;
}

OHOS::Ace::Platform::ComponentInfo Component::GetComponentInfo()
{
    return componentInfo_;
}

void Component::SetParentComponent(const shared_ptr<Component> parent)
{
    parentComponent_ = parent;
}

shared_ptr<Component> Component::GetParentComponent()
{
    return parentComponent_;
}

Point Component::GetBoundsCenter()
{
    HILOG_DEBUG("Component::GetBoundsCenter");
    Point point;
    point.x = componentInfo_.left + componentInfo_.width / 2;
    point.y = componentInfo_.top + componentInfo_.height / 2;
    HILOG_DEBUG("Component::GetBoundsCenter left:%f  top:%f width:%f height:%f  x:%d  y:%d", componentInfo_.left,
        componentInfo_.top, componentInfo_.width, componentInfo_.height, point.x, point.y);
    return point;
}

On* On::Text(const string& text, MatchPattern pattern)
{
    HILOG_DEBUG("On::Text");
    if (pattern >= MatchPattern::EQUALS && pattern <= MatchPattern::ENDS_WITH) {
        this->text = std::make_shared<string>(text);
        this->pattern_ = pattern;
        this->isEnter = true;
        HILOG_DEBUG("On::Text success");
    } else {
        this->isEnter = false;
    }
    return this;
}

On* On::Id(const string& id)
{
    HILOG_DEBUG("On::Onid");
    this->id = std::make_shared<string>(id);
    this->isEnter = true;
    return this;
}

On* On::Type(const string& type)
{
    HILOG_DEBUG("On::Ontype");
    this->type = std::make_shared<string>(type);
    this->isEnter = true;
    return this;
}

On* On::Enabled(bool enabled)
{
    HILOG_DEBUG("On::Onenabled");
    this->enabled = std::make_shared<bool>(enabled);
    this->isEnter = true;
    return this;
}

On* On::Focused(bool focused)
{
    HILOG_DEBUG("Ons::Onfocused");
    this->focused = std::make_shared<bool>(focused);
    this->isEnter = true;
    return this;
}

On* On::Selected(bool selected)
{
    HILOG_DEBUG("Driver::Onselected");
    this->selected = std::make_shared<bool>(selected);
    this->isEnter = true;
    return this;
}

On* On::Clickable(bool clickable)
{
    HILOG_DEBUG("Driver::Onclickable");
    this->clickable = std::make_shared<bool>(clickable);
    this->isEnter = true;
    return this;
}

On* On::LongClickable(bool longClickable)
{
    HILOG_DEBUG("Driver::OnlongClickable");
    this->longClickable = std::make_shared<bool>(longClickable);
    this->isEnter = true;
    return this;
}

On* On::Scrollable(bool scrollable)
{
    HILOG_DEBUG("Driver::Onscrollable");
    this->scrollable = std::make_shared<bool>(scrollable);
    this->isEnter = true;
    return this;
}

On* On::Checkable(bool checkable)
{
    HILOG_DEBUG("Driver::Oncheckable");
    this->checkable = std::make_shared<bool>(checkable);
    this->isEnter = true;
    return this;
}

On* On::Checked(bool checked)
{
    HILOG_DEBUG("Driver::Onchecked");
    this->checked = std::make_shared<bool>(checked);
    this->isEnter = true;
    return this;
}

static bool GetBeforeComponent(OHOS::Ace::Platform::ComponentInfo& component,
    const On& on, OHOS::Ace::Platform::ComponentInfo& ret)
{
    if (BEFORE_FLAG) {
        ret = component;
        return true;
    }

    if (on == component) {
        BEFORE_FLAG =  true;
    }

    for (auto iter = component.children.rbegin(); iter != component.children.rend(); iter++) {
        if (GetBeforeComponent(*iter, on, ret)) {
            return true;
        }
    }
    return false;
}

static bool GetAfterComponent(OHOS::Ace::Platform::ComponentInfo& component,
    const On& on, OHOS::Ace::Platform::ComponentInfo& ret)
{
    if (AFTER_FLAG) {
        ret = component;
        return true;
    }

    if (on == component) {
        AFTER_FLAG =  true;
    }

    for (auto& child : component.children) {        
        if (GetAfterComponent(child, on, ret)){
            return true;
        }
    }
    return false;
}

On* On::IsBefore(On* on)
{
    HILOG_INFO("Driver::IsBefore")
    if (!on->isBefore.empty() || !on->isAfter.empty() || !on->within.empty()) {
        HILOG_ERROR("Nesting ON usage is not supported");
        this->isEnter = false;
        return nullptr;
    }
    this->isBefore.emplace_back(on);
    this->isEnter = true;
    return this;
}

On* On::IsAfter(On* on)
{
    HILOG_INFO("Driver::IsAfter")
    if (!on->isBefore.empty() || !on->isAfter.empty() || !on->within.empty()) {
        HILOG_ERROR("Nesting ON usage is not supported");
        this->isEnter = false;
        return nullptr;
    }
    this->isAfter.emplace_back(on);
    this->isEnter = true;
    return this;
}

On* On::Within(On* on)
{
    HILOG_INFO("Driver::Within")
    if (!on->isBefore.empty() || !on->isAfter.empty() || !on->within.empty()) {
        HILOG_ERROR("Nesting ON usage is not supported");
        this->isEnter = false;
        return nullptr;
    }
    this->within.emplace_back(on);
    this->isEnter = true;
    return this;
}

bool On::CompareText(const string& text) const
{
    if (this->pattern_ == MatchPattern::EQUALS) {
        return text == *this->text;
    } else if (this->pattern_ == MatchPattern::CONTAINS) {
        return text.find(*this->text) != string::npos;
    } else if (this->pattern_ == MatchPattern::STARTS_WITH) {
        return text.find(*this->text) == 0;
    } else if (this->pattern_ == MatchPattern::ENDS_WITH) {
        auto ret = text.find(*this->text);
        if ( ret != -1) {
            return (ret == (text.length() - this->text->length()));
        }
    }
    return false;
}

bool operator == (const On& on, const OHOS::Ace::Platform::ComponentInfo& info)
{
    if (!on.isEnter) {
        return false;
    }
    bool res = true;
    if (on.id) {
        res = *on.id == info.compid && res;
    }
    if (on.text) {
        res = on.CompareText(info.text) && res;
    }
    if (on.type) {
        res = *on.type == info.type && res;
    }
    if (on.clickable) {
        res = *on.clickable == info.clickable && res;
    }
    if (on.longClickable) {
        res = *on.longClickable == info.longClickable && res;
    }
    if (on.scrollable) {
        res = *on.scrollable == info.scrollable && res;
    }
    if (on.enabled) {
        res = *on.enabled == info.enabled && res;
    }
    if (on.focused) {
        res = *on.focused == info.focused && res;
    }
    if (on.selected) {
        res = *on.selected == info.selected && res;
    }
    if (on.checked) {
        res = *on.checked == info.checked && res;
    }
    if (on.checkable) {
        res = *on.checkable == info.checkable && res;
    }
    return res;
}

static void GetComponentvalue(OHOS::Ace::Platform::ComponentInfo& component,const On& on,
     OHOS::Ace::Platform::ComponentInfo& ret, Rect& rect)
{
    Rect rect1 = GetBounds(component);
    if (on == component) {
        ret = component; // float数比较，取小于1个像素，为不可见
        if (component.width < 1.0f || component.height < 1.0f) {
            HILOG_DEBUG("GetComponentvalue return invisible ");
            return;
        } else if (component.width >= 1.0f && component.height >= 1.0f) {
            HILOG_DEBUG("GetComponentvalue return visible");
            return;
        }
    }

    for (auto& child : component.children) {
        GetComponentvalue(child, on, ret, rect1);
    }
}

bool IsRectOverlap(Rect& rect1, Rect& rect2)
{
    // 判断两个控件是否有交集
    if (rect1.left >= rect2.right || rect1.right <= rect2.left ||
        rect1.top >= rect2.bottom || rect1.bottom <= rect2.top) {
        return false; // 没有交集
    } else {
        return true; // 有交集
    }
}

static void GetAllComponentInfos(OHOS::Ace::Platform::ComponentInfo& componentInfo,
    Rect& rect, vector<shared_ptr<Component>>& allComponents,
    shared_ptr<Component> parentComponent)
{
    HILOG_DEBUG("GetAllComponentInfos begin. allComponents.size()=%d", allComponents.size());
    Rect rect1 = GetBounds(componentInfo);

    auto component = make_shared<Component>();
    component->SetComponentInfo(componentInfo);
    component->SetParentComponent(parentComponent);
    if (IsRectOverlap(rect1, rect)) {
        allComponents.emplace_back(component);
    }
    for (auto &child : componentInfo.children) {
        GetAllComponentInfos(child, rect1, allComponents, component);
    }
    HILOG_DEBUG("GetAllComponentInfos end. allComponents.size()=%d", allComponents.size());
}

static vector<shared_ptr<Component>> GetComponentsInRange(const On& on,
    vector<shared_ptr<Component>>& allComponents)
{
    HILOG_DEBUG("GetComponentsInRange begin.");
    int firstIndex = 0;
    int lastIndex = allComponents.size() - 1;
    if (on.isBefore.size() > 0) {
        bool gettingBefores = true;
        for (int index = 0; gettingBefores && index < allComponents.size(); index++) {
            for (On* isBeforeOn : on.isBefore) {
                if (*isBeforeOn == allComponents[index]->GetComponentInfo()) {
                    lastIndex = index - 1;
                    gettingBefores = false;
                    break;
                }
            }
        }
    }
    if (on.isAfter.size() > 0) {
        bool gettingAfters = true;
        for (int index = allComponents.size() - 1; gettingAfters && index >= 0; index--) {
            for (On* isAfterOn : on.isAfter) {
                if (*isAfterOn == allComponents[index]->GetComponentInfo()) {
                    firstIndex = index + 1;
                    gettingAfters = false;
                    break;
                }
            }
        }
    }
    vector<shared_ptr<Component>> componentsInRange;
    for(int index = firstIndex; index <= lastIndex; index++){
        componentsInRange.push_back(allComponents[index]);
    }
    HILOG_DEBUG("GetComponentsInRange end. Rest size of componentsInRange is = %d", componentsInRange.size());
    return componentsInRange;
}

bool IsWithinComponent(const On& on, shared_ptr<Component>& component) {
    HILOG_DEBUG("IsWithinComponent begin.");
    for (int withinIndex = 0; withinIndex < on.within.size(); withinIndex++) {
        shared_ptr<Component> parentComponent = component->GetParentComponent();
        while (parentComponent != nullptr) {
            if(*on.within[withinIndex] == parentComponent->GetComponentInfo()) {
                break;
            }
            parentComponent = parentComponent->GetParentComponent();
        }
        if (parentComponent == nullptr) {
            HILOG_DEBUG("IsWithinComponent end. Component not within specified parent component.");
            return false;
        }
    }
    HILOG_DEBUG("IsWithinComponent end.");
    return true;
}

unique_ptr<Component> GetComponentvalue(const On& on, vector<shared_ptr<Component>>& componentsInRange)
{    
    HILOG_DEBUG("GetComponentvalue begin.");
    for (int index=0; index < componentsInRange.size(); index++) {
        if (on == componentsInRange[index]->GetComponentInfo() &&
            IsWithinComponent(on,componentsInRange[index])) {
            HILOG_DEBUG("Component found.");
            auto component = make_unique<Component>();
            component->SetComponentInfo(componentsInRange[index]->GetComponentInfo());
            component->SetParentComponent(componentsInRange[index]->GetParentComponent());
            return component;
        }
    }
    HILOG_DEBUG("GetComponentvalue end.");
    return nullptr;
}

unique_ptr<Component> Driver::FindComponent(const On& on)
{
    HILOG_DEBUG("Driver::FindComponent begin");
    auto component = make_unique<Component>();
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    CHECK_NULL_RETURN(uiContent, nullptr);
    uiContent->GetAllComponents(0, info);
    Rect infoRect = GetBounds(info);
    HILOG_DEBUG("GetAllComponents ok");
    vector<shared_ptr<Component>> allComponents;
    GetAllComponentInfos(info, infoRect, allComponents, nullptr);
    vector<shared_ptr<Component>> componentsInRange = GetComponentsInRange(on, allComponents);
    return GetComponentvalue(on, componentsInRange);
}

void GetComponentvalues(const On& on, vector<shared_ptr<Component>> &componentsInRange, vector<unique_ptr<Component>>& components)
{  
    HILOG_DEBUG("GetComponentvalues begin.");
    for(int index = 0; index < componentsInRange.size(); index++){
        if (on == componentsInRange[index]->GetComponentInfo() && IsWithinComponent(on, componentsInRange[index])){
            HILOG_DEBUG("Component found.");
            auto component = make_unique<Component>();
            component->SetComponentInfo(componentsInRange[index]->GetComponentInfo());
            component->SetParentComponent(componentsInRange[index]->GetParentComponent());
            components.push_back(move(component));
        }
    }
    HILOG_DEBUG("GetComponentvalues end.");
}

vector<unique_ptr<Component>> Driver::FindComponents(const On& on)
{
    HILOG_DEBUG("Driver::FindComponents");
    vector<unique_ptr<Component>> components;
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    uiContent->GetAllComponents(0, info);
    Rect infoRect = GetBounds(info);
    vector<shared_ptr<Component>> allComponents;
    GetAllComponentInfos(info, infoRect, allComponents, nullptr);
    vector<shared_ptr<Component>> componentsInRange = GetComponentsInRange(on, allComponents);
    GetComponentvalues(on, componentsInRange, components);
    HILOG_DEBUG("Driver::FindComponents end");
    return components;
}

unique_ptr<Component> Component::ScrollSearch(const On& on)
{
    HILOG_DEBUG("Component::ScrollSearch");
    OHOS::Ace::Platform::ComponentInfo ret;
    Rect infoRect = GetBounds();
    vector<shared_ptr<Component>> allComponents;
    GetAllComponentInfos(componentInfo_, infoRect, allComponents, nullptr);
    vector<shared_ptr<Component>> componentsInRange = GetComponentsInRange(on, allComponents);
    unique_ptr<Component> component = move(GetComponentvalue(on, componentsInRange));
    if (component == nullptr) {
        HILOG_ERROR("not find Component");
        return nullptr;
    }

    Driver driver;
    auto rootTop = componentInfo_.top;
    auto componentTop = component->GetComponentInfo().top;
    auto rootBottom = componentInfo_.top + componentInfo_.height;
    auto componentBottom = component->GetComponentInfo().top + component->GetComponentInfo().height;
    if ((componentBottom < rootTop || componentTop > rootBottom) && !IsScrollable().get()) {
        HILOG_ERROR("not find Component, and this component is not scrollable");
        return nullptr;
    }

    if (componentTop < rootTop && IsScrollable().get()) {
        auto distance = rootTop - componentTop;
        auto startX = componentInfo_.left + componentInfo_.width / 2;
        auto startY = componentInfo_.top + componentInfo_.height / 2;
        auto stepLen = std::min(distance / 2, componentInfo_.height / 4);
        auto steps = distance / stepLen + 1;
        for (int step = 0; step < steps; step++) {
            driver.Swipe(startX, startY, startX, startY + stepLen, 200);
        }
    }

    if (componentBottom > rootBottom && IsScrollable().get()) {
        auto distance = componentBottom - rootBottom;
        auto startX = componentInfo_.left + componentInfo_.width / 2;
        auto startY = componentInfo_.top + componentInfo_.height / 2;
        auto stepLen = std::min(distance / 2, componentInfo_.height / 4);
        auto steps = distance / stepLen + 1;
        for (int step = 0; step < steps; step++) {
            driver.Swipe(startX, startY, startX, startY - stepLen, 200);
        }
    }
    return component;
}

PointerMatrix* PointerMatrix::Create(uint32_t fingers, uint32_t steps)
{
    this->fingerPointMap_.clear();
    this->fingerNum_ = fingers;
    this->stepNum_ = steps;
    return this;
}

void PointerMatrix::SetPoint(uint32_t finger, uint32_t step, Point& point)
{
    if (this->fingerNum_ == 0 || this->stepNum_ == 0) {
        return;
    }
    if (finger < this->fingerNum_) {
        if (step < this->stepNum_) {
            vector<Point>& pointVec = fingerPointMap_[finger];
            Point pointTmp = point;
            pointVec.push_back(pointTmp);
        }
    }
}

PointerMatrix& PointerMatrix::operator=(PointerMatrix&& other)
{
    this->fingerPointMap_ = other.fingerPointMap_;
    this->fingerNum_ = other.fingerNum_;
    this->stepNum_ = other.stepNum_;
    return *this;
}

uint32_t PointerMatrix::GetSteps() const
{
    return this->stepNum_;
}

uint32_t PointerMatrix::GetFingers() const
{
    return this->fingerNum_;
}

std::map<int, std::vector<Point>> PointerMatrix::GetPointMap() const {
    return this->fingerPointMap_;
}

} // namespace OHOS::UiTest
