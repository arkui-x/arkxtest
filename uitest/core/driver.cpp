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
    uicontent->Finish();
}

void Driver::DelayMs(int dur)
{
    HILOG_DEBUG("Driver::DelayMs duration=%d", dur);
    if (dur > 0) {
        this_thread::sleep_for(chrono::milliseconds(dur));
    }
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

void Driver::Swipe(int startx, int starty, int endx, int endy, int speed)
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

void Driver::Fling(const Point& from, const Point& to, int stepLen, int speed)
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
    Driver driver;
    for (int i = 0; i < text.length(); i++) {
        int32_t keycode = Findkeycode(text[i]);
        if (keycode == -1) {
            continue;
        }
        HILOG_DEBUG("Component::checkable: %{public}d", keycode);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(keycode), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(keycode), static_cast<int32_t>(Ace::KeyAction::UP), 0);
        driver.DelayMs(DELAY_TIME);
    }
   
}

void Component::ClearText()
{
    HILOG_DEBUG("Component::ClearText length:%d", componentInfo_.text.length());
    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    Driver driver;
    for (int i = 0; i < componentInfo_.text.length(); i++) {
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DPAD_RIGHT), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DPAD_RIGHT), static_cast<int32_t>(Ace::KeyAction::UP), 0);
        driver.DelayMs(DELAY_TIME);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DEL), static_cast<int32_t>(Ace::KeyAction::DOWN), 0);
        uiContent->ProcessKeyEvent(static_cast<int32_t>(Ace::KeyCode::KEY_DEL), static_cast<int32_t>(Ace::KeyAction::UP), 0);
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

void Component::SetComponentInfo(const OHOS::Ace::Platform::ComponentInfo& com)
{
    componentInfo_ = com;
}

unique_ptr<Component> Component::ScrollSearch(const On& on)
{
    HILOG_DEBUG("Component::ScrollSearch");
    auto component = make_unique<Component>();

    auto uiContent = GetUIContent();
    CHECK_NULL_RETURN(uiContent, component);

    OHOS::Ace::Platform::ComponentInfo info;
    uiContent->GetAllComponents(0, info);

    Driver driver;
    component = driver.FindComponent(on);

    if (component == nullptr) {
        HILOG_DEBUG("Component::ScrollSearch component is not find");
        return component;
    }

    if (!IsScrollable().get()) {
        HILOG_DEBUG("Component::ScrollSearch component is visible");
        return component;
    }

    auto rootTop = info.top;
    auto rootBottom = info.top + info.height;
    auto componentTop = component->componentInfo_.top;
    auto componentBottom = component->componentInfo_.top + component->componentInfo_.height;

    if (componentTop < rootTop) {
        auto distance = rootTop - componentTop;
        auto startX = info.left + info.width / 2;
        auto startY = info.top + info.height / 2;
        auto stepLen = std::min(distance / 2, info.height / 4);
        auto steps = distance / stepLen + 1;
        for (int step = 0; step < steps; step++) {
            driver.Swipe(startX, startY, startX, startY + stepLen, 200);
        }
    }

    if (componentBottom > rootBottom) {
        auto distance = componentBottom - rootBottom;
        auto startX = info.left + info.width / 2;
        auto startY = info.top + info.height / 2;
        auto stepLen = std::min(distance / 2, info.height / 4);
        auto steps = distance / stepLen + 1;
        for (int step = 0; step < steps; step++) {
            driver.Swipe(startX, startY, startX, startY - stepLen, 200);
        }
    }
    return component;
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
        HILOG_DEBUG("On::Text success");
    }
    return this;
}

On* On::Id(const string& id)
{
    HILOG_DEBUG("On::Onid");
    this->id = std::make_shared<string>(id);
    return this;
}

On* On::Type(const string& type)
{
    HILOG_DEBUG("On::Ontype");
    this->type = std::make_shared<string>(type);
    return this;
}

On* On::Enabled(bool enabled)
{
    HILOG_DEBUG("On::Onenabled");
    this->enabled = std::make_shared<bool>(enabled);
    return this;
}

On* On::Focused(bool focused)
{
    HILOG_DEBUG("Ons::Onfocused");
    this->focused = std::make_shared<bool>(focused);
    return this;
}

On* On::Selected(bool selected)
{
    HILOG_DEBUG("Driver::Onselected");
    this->selected = std::make_shared<bool>(selected);
    return this;
}

On* On::Clickable(bool clickable)
{
    HILOG_DEBUG("Driver::Onclickable");
    this->clickable = std::make_shared<bool>(clickable);
    return this;
}

On* On::LongClickable(bool longClickable)
{
    HILOG_DEBUG("Driver::OnlongClickable");
    this->longClickable = std::make_shared<bool>(longClickable);
    return this;
}

On* On::Scrollable(bool scrollable)
{
    HILOG_DEBUG("Driver::Onscrollable");
    this->scrollable = std::make_shared<bool>(scrollable);
    return this;
}

On* On::Checkable(bool checkable)
{
    HILOG_DEBUG("Driver::Oncheckable");
    this->checkable = std::make_shared<bool>(checkable);
    return this;
}

On* On::Checked(bool checked)
{
    HILOG_DEBUG("Driver::Onchecked");
    this->checked = std::make_shared<bool>(checked);
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
        return (text.find(*this->text) == (text.length() - this->text->length()));
    }
    return false;
}

bool operator == (const On& on, const OHOS::Ace::Platform::ComponentInfo& info)
{
    if (!on.id && !on.text && !on.type && !on.clickable && !on.longClickable && !on.scrollable && !on.enabled &&
        !on.focused && !on.selected && !on.checked && !on.checkable) {
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

void GetComponentvalue(OHOS::Ace::Platform::ComponentInfo& component,
    const On& on, OHOS::Ace::Platform::ComponentInfo& ret)
{
    if (on == component) {
        ret = component;
        HILOG_DEBUG("GetComponentvalue return");
        return;
    }

    for (auto& child : component.children) {
        GetComponentvalue(child, on, ret);
    }
}

unique_ptr<Component> Driver::FindComponent(const On& on)
{
    HILOG_DEBUG("Driver::FindComponent begin");
    auto component = make_unique<Component>();
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    CHECK_NULL_RETURN(uiContent, nullptr);
    uiContent->GetAllComponents(0, info);
    HILOG_DEBUG("GetAllComponents ok");
    OHOS::Ace::Platform::ComponentInfo ret;
    GetComponentvalue(info, on, ret);
    if (ret.left < 1 && ret.top < 1 && ret.width < 1 && ret.height < 1) {
        HILOG_DEBUG("not  find Component");
        return nullptr;
    }
    component->SetComponentInfo(ret);
    return component;
}

void GetComponentvalues(OHOS::Ace::Platform::ComponentInfo& info, const On& on,
    vector<unique_ptr<Component>>& components)
{
    if (on == info) {
        auto component = make_unique<Component>();
        component->SetComponentInfo(info);
        components.push_back(move(component));
    }
    for (auto& child : info.children) {
        GetComponentvalues(child, on, components);
    }
}

vector<unique_ptr<Component>> Driver::FindComponents(const On& on)
{
    HILOG_DEBUG("Driver::FindComponents");
    vector<unique_ptr<Component>> components;
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    uiContent->GetAllComponents(0, info);
    GetComponentvalues(info, on, components);
    HILOG_DEBUG("Driver::FindComponents");
    return components;
}

} // namespace OHOS::UiTest
