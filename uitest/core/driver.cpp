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
static constexpr const int32_t DELAY_TIME = 100;
constexpr size_t INDEX_ZERO = 0;
constexpr size_t INDEX_ONE = 1;
constexpr size_t INDEX_TWO = 2;
constexpr size_t INDEX_THREE = 3;
constexpr size_t INDEX_FOUR = 4;
constexpr size_t INDEX_FIVE = 5;
constexpr size_t INDEX_SIX = 6;
// CombineKey
// int32_t metaKey 参数取值: CTRL = 1,    SHIFT = 2,    ALT = 4,    META = 8,
constexpr int32_t KEY_CTRL = 1;
constexpr int32_t KEY_SHIFT = 2;
constexpr int32_t KEY_ALT = 4;
constexpr int32_t KEY_META = 8;

int32_t Findkeycode(const char ch, int32_t& metaKey, int32_t& keycode)
{
    metaKey = 0;
    if (isupper(ch)) {
        metaKey = 2; // int32_t metaKey 参数取值: CTRL = 1,    SHIFT = 2,    ALT = 4,    META = 8,
        keycode = static_cast<int32_t>(ch - UPPER_A) + static_cast<int32_t>(Ace::KeyCode::KEY_A);
        return 0;
    }

    if(islower(ch)) {
        keycode = static_cast<int32_t>(ch - LOWER_A) + static_cast<int32_t>(Ace::KeyCode::KEY_A);
        return 0;
    }

    if (isdigit(ch)) {
        keycode = static_cast<int32_t>(ch - DEF_NUMBER) + static_cast<int32_t>(Ace::KeyCode::KEY_0);
        return 0;
    }

    if (isspace(ch)) { // 空格
        keycode = static_cast<int32_t>(Ace::KeyCode::KEY_SPACE);
        return 0;
    }
    HILOG_DEBUG("Please enter lowercase letters and numbers or space.");
    return -1;
}

bool TextToKeyCodeCheck(string text)
{
    if (!text.empty()) {
        vector<char> chars(text.begin(), text.end()); // decompose to sing-char input sequence
        for (auto ch : chars) {
            int32_t metaKey, keycode;
            if (Findkeycode(ch, metaKey, keycode) == -1) {
                return false;
            }
        }
    }
    return true;
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
    UiOpArgs options;
    uiContent->ProcessKeyEvent(static_cast<int32_t>(keyCode), static_cast<int32_t>(Ace::KeyAction::DOWN),
        options.clickHoldMs_);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(keyCode), static_cast<int32_t>(Ace::KeyAction::UP), 0);
}

bool IsCombineKey(int key)
{
    bool flag = false;
    switch (key)
    {
    case static_cast<int32_t>(Ace::KeyCode::KEY_CTRL_LEFT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_CTRL_RIGHT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_SHIFT_LEFT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_SHIFT_RIGHT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_ALT_LEFT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_ALT_RIGHT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_META_LEFT):
        flag = true;
        break;
    case static_cast<int32_t>(Ace::KeyCode::KEY_META_RIGHT):
        flag = true;
        break;
    default:
        break;
    }
    return flag;
}

int GetMetaKeyValue(int key)
{
    int mataKey = -1;
    if (key == static_cast<int32_t>(Ace::KeyCode::KEY_CTRL_LEFT) ||
        key == static_cast<int32_t>(Ace::KeyCode::KEY_CTRL_RIGHT)) {
        mataKey = KEY_CTRL;
    } else if (key == static_cast<int32_t>(Ace::KeyCode::KEY_SHIFT_LEFT) ||
        key == static_cast<int32_t>(Ace::KeyCode::KEY_SHIFT_RIGHT)) {
        mataKey = KEY_SHIFT;
    } else if (key == static_cast<int32_t>(Ace::KeyCode::KEY_ALT_LEFT) ||
        key == static_cast<int32_t>(Ace::KeyCode::KEY_ALT_RIGHT)) {
        mataKey = KEY_ALT;
    } else if (key == static_cast<int32_t>(Ace::KeyCode::KEY_META_LEFT) ||
        key == static_cast<int32_t>(Ace::KeyCode::KEY_META_RIGHT)) {
        mataKey = KEY_META;
    }
    return mataKey;
}

void Driver::TriggerCombineKeys(int key0, int key1, int key2)
{
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    if (key0 == -1 || key1 == -1) {
        return;
    }
    Driver driver;
    HILOG_DEBUG("Driver::TriggerCombineKeys: %{public}d %{public}d %{public}d", key0, key1, key2);
    if (IsCombineKey(key0) && IsCombineKey(key1) && key2 != -1) {
        int metaKey0 = GetMetaKeyValue(key0);
        int metaKey1 = GetMetaKeyValue(key1);
        uiContent->ProcessKeyEvent(key2, static_cast<int32_t>(Ace::KeyAction::DOWN), 0, 0, 0, metaKey0 | metaKey1);
        uiContent->ProcessKeyEvent(key2, static_cast<int32_t>(Ace::KeyAction::UP), 0, 0, 0, metaKey0 | metaKey1);
    } else if (IsCombineKey(key0)) {
        int metaKey0 = GetMetaKeyValue(key0);
        uiContent->ProcessKeyEvent(key1, static_cast<int32_t>(Ace::KeyAction::DOWN), 0, 0, 0, metaKey0);
        uiContent->ProcessKeyEvent(key1, static_cast<int32_t>(Ace::KeyAction::UP), 0, 0, 0, metaKey0);
    } else {
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key0), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key1), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key2), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        driver.DelayMs(DELAY_TIME);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key0), static_cast<int32_t>(Ace::KeyAction::UP), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key1), static_cast<int32_t>(Ace::KeyAction::UP), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(key2), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    }
    driver.DelayMs(DELAY_TIME);
}

bool Driver::InjectMultiPointerAction(PointerMatrix& pointers, uint32_t speed)
{
    uint32_t steps = pointers.GetSteps();
    if (steps <= 1) {
        HILOG_ERROR("Driver::InjectMultiPointerAction no move.");
        return false;
    }
    // speed will add later
    std::vector<Ace::TouchEvent> injectEvents;
    int64_t curTimeMillis = getCurrentTimeMillis();
    for (auto it : pointers.fingerPointMap_) {
        Ace::TouchEvent downEvent;
        downEvent.id = it.first;
        if (it.second.size() == 0) {
            return false;
        }
        PackagingEvent(downEvent, TimeStamp(curTimeMillis), Ace::TouchType::DOWN, it.second[0]);
        injectEvents.push_back(downEvent);
    }
    auto it2 = pointers.fingerPointMap_.begin();
    int size2 = it2->second.size();
    if (size2 <= 1) {
        return false;
    }
    for (int i = 1; i < size2; i++) {
        for (auto it : pointers.fingerPointMap_) {
            Ace::TouchEvent moveEvent;
            moveEvent.id = it.first;
            PackagingEvent(moveEvent, TimeStamp(curTimeMillis + DELAY_TIME * i), Ace::TouchType::MOVE, it.second[i]);
            injectEvents.push_back(moveEvent);
        }
    }
    for (auto it : pointers.fingerPointMap_) {
        Ace::TouchEvent upEvent;
        upEvent.id = it.first;
        int size = it.second.size();
        PackagingEvent(upEvent, TimeStamp(curTimeMillis + DELAY_TIME * steps), Ace::TouchType::UP, it.second[size - 1]);
        injectEvents.push_back(upEvent);
    }

    auto uiContent = GetUIContent();
    CHECK_NULL_RETURN(uiContent, false);
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

/* 默认左上角原点
componentInfo:
left  x  number    矩形区域的左边界，单位为px，该参数为整数。
top   y  number    矩形区域的上边界，单位为px，该参数应为整数。
width   number    矩形区域的宽度，单位为px，该参数应为整数。
height  number    矩形区域的高度，单位为px，该参数应为整数。
*/
void Driver::CalculateDirection(const OHOS::Ace::Platform::ComponentInfo& info,
    const UiDirection& direction, Point& from, Point& to)
{
    // 滑动距离要大于1/2才能更有效的滑动屏幕，尤其在左右滑动时
    switch (direction) {
        case UiDirection::LEFT : // 从左滑到右
            from.x = info.left + info.width / INDEX_SIX;
            from.y = info.top + info.height / INDEX_TWO; // 横向居中
            to.x = from.x - info.width * INDEX_TWO / INDEX_THREE;
            to.y = from.y;
            break;
        case UiDirection::RIGHT : // 从右滑到左
            from.x = info.left + info.width * INDEX_FIVE / INDEX_SIX;
            from.y = info.top + info.height / INDEX_TWO; // 横向居中
            to.x = from.x + info.width * INDEX_TWO / INDEX_THREE;
            to.y = from.y;
            break;
        case UiDirection::UP : // 从上滑到下
            from.x = info.left + info.width / INDEX_TWO; // 纵向居中
            from.y = info.top + info.height / INDEX_SIX;
            to.x = from.x;
            to.y = from.y - info.height * INDEX_TWO / INDEX_THREE;
            break;
        case UiDirection::DOWN : // 从下滑到上
            from.x = info.left + info.width / INDEX_TWO; // 纵向居中
            from.y = info.top + info.height * INDEX_FIVE / INDEX_SIX;
            to.x = from.x;
            to.y = from.y + info.height * INDEX_TWO / INDEX_THREE;
            break;
        default:
            from.x = info.left + info.width / INDEX_TWO; // 纵向居中
            from.y = info.top + info.height * INDEX_FIVE / INDEX_SIX;
            to.x = from.x;
            to.y = from.y + info.height * INDEX_TWO / INDEX_THREE;
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
    ClearText();
    if (text.empty()) {
        return;
    }
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    Driver driver;
    if (TextToKeyCodeCheck(text)) {
        for (uint32_t i = 0; i < text.length(); i++) {
            int32_t metaKey, keycode;
            Findkeycode(text[i], metaKey, keycode);
            uiContent->ProcessKeyEvent(keycode, static_cast<int32_t>(Ace::KeyAction::DOWN), 0, 0, 0, metaKey);
            uiContent->ProcessKeyEvent(keycode, static_cast<int32_t>(Ace::KeyAction::UP), 0, 0, 0, metaKey);
            driver.DelayMs(DELAY_TIME);
        }
    } else {
        // ProcessKeyEvent 接口参数: int32_t keyCode, int32_t keyAction, int32_t repeatTime, int64_t timeStamp = 0,
        // int64_t timeStampStart = 0, int32_t metaKey = 0, int32_t sourceDevice = 0, int32_t deviceId = 0
        // int32_t metaKey 参数取值: CTRL = 1,    SHIFT = 2,    ALT = 4,    META = 8,
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_V), static_cast<int32_t>(Ace::KeyAction::DOWN), 0, 0, 0, KEY_CTRL);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_V), static_cast<int32_t>(Ace::KeyAction::UP), 0, 0, 0, KEY_CTRL);
        driver.DelayMs(DELAY_TIME);
    }
    componentInfo_.text = text;
}

void Component::ClearText()
{
    HILOG_DEBUG("Component::ClearText length:%d", componentInfo_.text.length());
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_MOVE_END), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
    uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_MOVE_END), static_cast<int32_t>(Ace::KeyAction::UP), 0);
    Driver driver;
    for (uint32_t i = 0; i < componentInfo_.text.length(); i++) {
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DEL), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DEL), static_cast<int32_t>(Ace::KeyAction::UP), 0);
        driver.DelayMs(DELAY_TIME);
    }
    componentInfo_.text.clear();
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
    HILOG_DEBUG("Component::GetBounds left:%d right%d top:%d bottom:%d", rect.left,
        rect.right, rect.top, rect.bottom);
    return rect;
}

void Component::PinchOut(float scale)
{
    HILOG_DEBUG("Component::PinchOut");
    if (scale <= 1.0f) {
        HILOG_DEBUG("Component::PinchOut scale[%f] <= 1.0f", scale);
        return;
    }
    float scaleOpt = scale - 1.0;
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
    PointerMatrix pointers;
    pointers.Create(2, 2);
    pointers.SetPoint(0, 0, fromUp);
    pointers.SetPoint(0, 1, toUp);
    pointers.SetPoint(1, 0, fromDown);
    pointers.SetPoint(1, 1, toDown);

    Driver driver;
    driver.InjectMultiPointerAction(pointers);
    driver.DelayMs(DELAY_TIME);

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
    float disH = componentInfo_.height * scale / INDEX_TWO;
    fromUp.x = center.x;
    fromUp.y = rect.top;
    fromDown.x = center.x;
    fromDown.y = rect.bottom;
    toUp.x = fromUp.x;
    toUp.y = fromUp.y + disH;
    toDown.x = fromDown.x;
    toDown.y = fromDown.y - disH;

    PointerMatrix pointers;
    pointers.Create(2, 2);
    pointers.SetPoint(0, 0, fromUp);
    pointers.SetPoint(0, 1, toUp);
    pointers.SetPoint(1, 0, fromDown);
    pointers.SetPoint(1, 1, toDown);

    Driver driver;
    driver.InjectMultiPointerAction(pointers);
    driver.DelayMs(DELAY_TIME);

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

On* On::IsBefore(On* on)
{
    HILOG_INFO("Driver::IsBefore")
    this->isBefore = make_shared<On>(*on);
    this->isEnter = true;
    return this;
}

On* On::IsAfter(On* on)
{
    HILOG_INFO("Driver::IsAfter")
    this->isAfter = make_shared<On>(*on);
    this->isEnter = true;
    return this;
}

On* On::WithIn(On* on)
{
    HILOG_INFO("Driver::WithIn")
    this->withIn = make_shared<On>(*on);
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
    if (IsRectOverlap(rect1, rect)) {
        allComponents.emplace_back(component);
    }
    for (auto &child : componentInfo.children) {
        GetAllComponentInfos(child, rect1, allComponents, component);
    }
    HILOG_DEBUG("GetAllComponentInfos end. allComponents.size()=%d", allComponents.size());
}

static void FindChildComponents(OHOS::Ace::Platform::ComponentInfo& componentInfo,
    const On& on, vector<shared_ptr<Component>>& childComponents)
{
    HILOG_DEBUG("FindChildComponents. childComponents.size()=%d", childComponents.size());
    if (on == componentInfo) {
        Rect rect = GetBounds(componentInfo);
        for (auto &child : componentInfo.children) {
            GetAllComponentInfos(child, rect, childComponents, nullptr);
        }
        return;
    }

    for (auto &child : componentInfo.children) {
        FindChildComponents(child, on, childComponents);
    }
}

static vector<shared_ptr<Component>> GetComponentsInRange(const On& on,
    vector<shared_ptr<Component>>& allComponents)
{
    HILOG_DEBUG("GetComponentsInRange begin.");
    vector<shared_ptr<Component>> componentsInRange;
    if (allComponents.size() == 0) {
        HILOG_DEBUG("allComponents size = 0.");
        return componentsInRange;
    }
    uint32_t firstIndex = 0;
    uint32_t lastIndex = allComponents.size() - 1;
    if (on.isBefore) {
        for (uint32_t index = 0; index < allComponents.size(); index++) {
            if (*(on.isBefore.get()) == allComponents[index]->GetComponentInfo()) {
                if (index == 0) {
                    return componentsInRange;
                }
                lastIndex = index;
                break;
            }
        }
    }

    if (on.isAfter) {
        for (int index = allComponents.size() - 1; index >= 0; index--) {
            if (*(on.isAfter.get()) == allComponents[index]->GetComponentInfo()) {
                firstIndex = index + 1;
                break;
            }
        }
    }

    for (uint32_t index = firstIndex; index <= lastIndex; index++) {
        componentsInRange.push_back(allComponents[index]);
    }
    HILOG_DEBUG("GetComponentsInRange end. firstIndex = %d, lastIndex = %d", firstIndex, lastIndex);
    HILOG_DEBUG("GetComponentsInRange end. allComponents size = %d, componentsInRange size = %d",
        allComponents.size(), componentsInRange.size());
    return componentsInRange;
}

unique_ptr<Component> GetComponentvalue(const On& on,
    vector<shared_ptr<Component>>& componentsInRange)
{
    HILOG_DEBUG("GetComponentvalue begin.");
    if (componentsInRange.size() == 0) {
        HILOG_DEBUG("componentsInRange size = 0.");
        return nullptr;
    }
    for (int index = 0; index < componentsInRange.size(); index++) {
        if (on == componentsInRange[index]->GetComponentInfo()) {
            HILOG_DEBUG("Component found.");
            auto component = make_unique<Component>();
            component->SetComponentInfo(componentsInRange[index]->GetComponentInfo());
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
    vector<shared_ptr<Component>> allComponents;
    Rect infoRect = GetBounds(info);
    if (on.withIn) {
        On onWithIn = *(on.withIn.get());
        FindChildComponents(info, onWithIn, allComponents);
    } else {
        GetAllComponentInfos(info, infoRect, allComponents, nullptr);
    }
    HILOG_DEBUG("GetAllComponents ok, size = %d", allComponents.size());
    vector<shared_ptr<Component>> componentsInRange = GetComponentsInRange(on, allComponents);
    return GetComponentvalue(on, componentsInRange);
}

void GetComponentvalues(const On& on, vector<shared_ptr<Component>> &componentsInRange,
    vector<unique_ptr<Component>>& components)
{
    HILOG_DEBUG("GetComponentvalues begin.");
    for(int index = 0; index < componentsInRange.size(); index++){
        if (on == componentsInRange[index]->GetComponentInfo()) {
            HILOG_DEBUG("Component found.");
            auto component = make_unique<Component>();
            component->SetComponentInfo(componentsInRange[index]->GetComponentInfo());
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
    if (on.withIn) {
        On onWithIn = *(on.withIn.get());
        FindChildComponents(info, onWithIn, allComponents);
    } else {
        GetAllComponentInfos(info, infoRect, allComponents, nullptr);
    }
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
    if (finger < this->fingerNum_) {
        if (step < this->stepNum_) {
            vector<Point>& pointVec = this->fingerPointMap_[finger];
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

} // namespace OHOS::UiTest
