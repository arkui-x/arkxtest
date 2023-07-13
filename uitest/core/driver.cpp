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
#include "foundation/appframework/arkui/uicontent/ui_content.h"
#include "foundation/arkui/ace_engine/frameworks/core/accessibility/accessibility_node.h"
#include "utils/log.h"

#include "core/event/touch_event.h"

namespace OHOS::UiTest {
using namespace std;

int64_t getCurrentTimeMillis()
{
    auto now = std::chrono::system_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
}

inline Ace::TimeStamp TimeStamp(int64_t currentTimeMillis){
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

bool Driver::AssertComponentExist(On& on)
{
    HILOG_INFO("Driver::AssertComponentExist");
    auto component = make_unique<Component>();
    component = FindComponent(on);
    return component != nullptr;
}

void Driver::PressBack()
{
    HILOG_INFO("Driver::PressBack called");
    auto uicontent = GetUIContent();
    CHECK_NULL_VOID(uicontent);
    uicontent->Finish();
}

void Driver::DelayMs(int dur)
{
    HILOG_INFO("Driver::DelayMs duration=%d", dur);
    if (dur > 0) {
        this_thread::sleep_for(chrono::milliseconds(dur));
    }
}

static void PackagingEvent(Ace::TouchEvent& event, Ace::TimeStamp time, Ace::TouchType type, int x, int y)
{
    event.time = time;
    event.type = type;
    event.x = x;
    event.y = y;
    event.screenX = x;
    event.screenY = y;
    event = event.UpdatePointers();
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
    HILOG_INFO("Driver::Click x=%d, y=%d", x, y);
    std::vector<Ace::TouchEvent> clickEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, x, y);
    clickEvents.push_back(downEvent);

    Ace::TouchEvent upEvent;
    UiOpArgs options;
    PackagingEvent(upEvent,TimeStamp(currentTimeMillis + options.clickHoldMs_), Ace::TouchType::UP, x, y);
    clickEvents.push_back(upEvent);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessBasicEvent(clickEvents);
}

void Driver::DoubleClick(int x, int y)
{
    HILOG_INFO("Driver::Click x=%d, y=%d", x, y);
    std::vector<Ace::TouchEvent> clickEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    for (int i = 0; i < 2; i++) {
        Ace::TouchEvent downEvent;
        PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, x, y);
        clickEvents.push_back(downEvent);

        Ace::TouchEvent upEvent;
        UiOpArgs options;
        PackagingEvent(upEvent, TimeStamp(currentTimeMillis + options.clickHoldMs_), Ace::TouchType::DOWN, x, y);
        clickEvents.push_back(upEvent);

        currentTimeMillis += options.clickHoldMs_;
    }

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);

    uiContent->ProcessBasicEvent(clickEvents);
}

void Driver::LongClick(int x, int y)
{
    HILOG_INFO("Driver::LongClick x=%d, y=%d", x, y);
    std::vector<Ace::TouchEvent> clickEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, x, y);
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
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, startx, starty);
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
        HILOG_WARN("Driver::Swipe ignored. distance value is illegal");
        return;
    }

    const uint16_t steps = options.swipeStepsCounts_;

    for (uint16_t step = 1; step < steps; step++) {
        const float pointX = startx + (distanceX * step) / steps;
        const float pointY = starty + (distanceY * step) / steps;
        const uint32_t timeOffsetMs = (timeCostMs * step) / steps;

        Ace::TouchEvent moveEvent;
        moveEvent = moveEvent.UpdatePointers();
        PackagingEvent(moveEvent, TimeStamp(currentTimeMillis + timeOffsetMs), Ace::TouchType::MOVE, pointX, pointY);
        swipeEvents.push_back(moveEvent);
    }

    Ace::TouchEvent upEvent;
    PackagingEvent(upEvent, TimeStamp(currentTimeMillis + timeCostMs), Ace::TouchType::UP, endx, endy);
    swipeEvents.push_back(upEvent);

    auto uiContent = GetUIContent();
    CHECK_NULL_VOID(uiContent);
    uiContent->ProcessBasicEvent(swipeEvents);
}

void Driver::Fling(Point& from, Point& to, int stepLen, int speed)
{
    HILOG_DEBUG(
        "Driver::Fling from (%d, %d) to (%d, %d), stepLen:%d, speed:%d", from.x, from.y, to.x, to.y, stepLen, speed);
    std::vector<Ace::TouchEvent> flingEvents;
    int64_t currentTimeMillis = getCurrentTimeMillis();

    Ace::TouchEvent downEvent;
    PackagingEvent(downEvent, TimeStamp(currentTimeMillis), Ace::TouchType::DOWN, from.x, from.y);
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
        HILOG_WARN("Driver::Fling ignored. stepLen is illegal");
        return;
    }
    const uint16_t steps = distance / stepLen;

    for (uint16_t step = 1; step < steps; step++) {
        const float pointX = from.x + (distanceX * step) / steps;
        const float pointY = from.y + (distanceY * step) / steps;
        const uint32_t timeOffsetMs = (timeCostMs * step) / steps;
        Ace::TouchEvent moveEvent;
        PackagingEvent(downEvent, TimeStamp(currentTimeMillis + timeOffsetMs), Ace::TouchType::MOVE, pointX, pointY);
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
    HILOG_INFO("Component::Click");
    Point point = GetBoundsCenter();
    Driver driver;
    driver.Click(point.x, point.y);
}

void Component::DoubleClick()
{
    HILOG_INFO("Component::DoubleClick");
    Point point = GetBoundsCenter();
    Driver driver;
    driver.DoubleClick(point.x, point.y);
}

void Component::LongClick()
{
    HILOG_INFO("Component::LongClick");
    Point point = GetBoundsCenter();
    Driver driver;
    driver.LongClick(point.x, point.y);
}

string Component::GetId()
{
    HILOG_INFO("Component::GetId");
    return componentInfo_.compid;
}

string Component::GetText()
{
    HILOG_INFO("Component::GetText");
    return componentInfo_.text;
}

string Component::GetType()
{
    HILOG_INFO("Component::GetType");
    return componentInfo_.type;
}

unique_ptr<bool> Component::IsClickable()
{
    auto clickable = make_unique<bool>();
    *clickable = componentInfo_.clickable;
    HILOG_INFO("Component::Clickable: %{public}d", *clickable);
    return clickable;
}

unique_ptr<bool> Component::IsLongClickable()
{
    auto longClickable = make_unique<bool>();
    *longClickable = componentInfo_.longClickable;
    HILOG_INFO("Component::LongClickable: %{public}d", *longClickable);
    return longClickable;
}

unique_ptr<bool> Component::IsScrollable()
{
    auto scrollable = make_unique<bool>();
    *scrollable = componentInfo_.scrollable;
    HILOG_INFO("Component::scrollable: %{public}d", *scrollable);
    return scrollable;
}

unique_ptr<bool> Component::IsEnabled()
{
    auto enabled = make_unique<bool>();
    *enabled = componentInfo_.enabled;
    HILOG_INFO("Component::enabled: %{public}d", *enabled);
    return enabled;
}

unique_ptr<bool> Component::IsFocused()
{
    auto focused = make_unique<bool>();
    *focused = componentInfo_.focused;
    HILOG_INFO("Component::focused: %{public}d", *focused);
    return focused;
}

unique_ptr<bool> Component::IsSelected()
{
    auto selected = make_unique<bool>();
    *selected = componentInfo_.selected;
    HILOG_INFO("Component::selected: %{public}d", *selected);
    return selected;
}

unique_ptr<bool> Component::IsChecked()
{
    auto checked = make_unique<bool>();
    *checked = componentInfo_.checked;
    HILOG_INFO("Component::checked: %{public}d", *checked);
    return checked;
}

unique_ptr<bool> Component::IsCheckable()
{
    auto checkable = make_unique<bool>();
    *checkable = componentInfo_.checkable;
    HILOG_INFO("Component::checkable: %{public}d", *checkable);
    return checkable;
}

void Component::InputText(const string &text)
{
    HILOG_INFO("Component::InputText");
    componentInfo_.text = text;
}

void Component::ClearText()
{
    HILOG_INFO("Component::ClearText");
    componentInfo_.text = "";
}

void Component::ScrollToTop(int speed)
{
    HILOG_DEBUG("Component::ScrollToTop speed:%d", speed);
    if (!IsScrollable()) {
        HILOG_WARN("Component::ScrollToTop current component is not scrollable");
        return;
    }

    HILOG_DEBUG("Component::ScrollToTop child.size:%d", componentInfo_.children.size());
    if (componentInfo_.children.size() < 1) {
        HILOG_WARN("Component::ScrollToTop current scollable component has no child");
        return;
    }

    OHOS::Ace::Platform::ComponentInfo flex = componentInfo_.children.front();
    HILOG_DEBUG("Component::ScrollToTop flex.size:%d", flex.children.size());
    if (flex.children.size() < 1) {
        HILOG_WARN("Component::ScrollToTop flex has no child");
        return;
    }

    if (flex.children.front().top >= (componentInfo_.top)) {
        HILOG_WARN("Component::ScrollToTop component is already in the top");
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
        HILOG_WARN("Component::ScrollToBottom current component is not scrollable");
        return;
    }

    HILOG_DEBUG("Component::scrollToBottom child.size:%d", componentInfo_.children.size());
    if (componentInfo_.children.size() < 1) {
        HILOG_WARN("Component::ScrollToBottom current scollable component has no child");
        return;
    }

    OHOS::Ace::Platform::ComponentInfo flex = componentInfo_.children.front();
    HILOG_DEBUG("Component::scrollToBottom flex.size:%d", flex.children.size());
    if (flex.children.size() < 1) {
        HILOG_WARN("Component::ScrollToBottom flex has no child");
        return;
    }

    if (flex.children.back().top <= (componentInfo_.top + componentInfo_.height)) {
        HILOG_WARN("Component::ScrollToBottom component is already in the bottom");
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

void Component::SetComponentInfo(OHOS::Ace::Platform::ComponentInfo& com)
{
    componentInfo_ = com;
}

unique_ptr<Component> Component::ScrollSearch(On on)
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
    HILOG_INFO("Component::GetBoundsCenter");
    Point point;
    point.x = componentInfo_.left + componentInfo_.width / 2;
    point.y = componentInfo_.top + componentInfo_.height / 2;
    HILOG_INFO("Component::GetBoundsCenter left:%f  top:%f width:%f height:%f  x:%d  y:%d", componentInfo_.left,
        componentInfo_.top, componentInfo_.width, componentInfo_.height, point.x, point.y);
    return point;
}

On* On::Text(const string &text, MatchPattern pattern)
{
    HILOG_INFO("On::Text");
    if (pattern >= MatchPattern::EQUALS && pattern <= MatchPattern::ENDS_WITH) {
        this->text = text;
        this->pattern_ = pattern;
        this->commonType.push_back(CommonType::TEXT);
        HILOG_INFO("On::Text success");
    }
    return this;
}

On* On::Id(const string &id)
{
    HILOG_INFO("On::Onid");
    this->id = id;
    this->commonType.push_back(CommonType::ID);
    return this;
}

On* On::Type(const string &type)
{
    HILOG_INFO("On::Ontype");
    this->type = type;
    this->commonType.push_back(CommonType::TYPE);
    return this;
}

On* On::Enabled(bool enabled)
{
    HILOG_INFO("On::Onenabled");
    this->enabled = enabled;
    this->commonType.push_back(CommonType::ENABLED);
    return this;
}

On* On::Focused(bool focused)
{
    HILOG_INFO("Ons::Onfocused");
    this->focused = focused;
    this->commonType.push_back(CommonType::FOCUSED);
    return this;
}

On* On::Selected(bool selected)
{
    HILOG_INFO("Driver::Onselected");
    this->selected = selected;
    this->commonType.push_back(CommonType::SELECTED);
    return this;
}

On* On::Clickable(bool clickable)
{
    HILOG_INFO("Driver::Onclickable");
    this->clickable = clickable;
    this->commonType.push_back(CommonType::CLICKABLE);
    return this;
}

On* On::LongClickable(bool longClickable)
{
    HILOG_INFO("Driver::OnlongClickable");
    this->longClickable = longClickable;
    this->commonType.push_back(CommonType::LONGCLICKABLE);
    return this;
}

On* On::Scrollable(bool scrollable)
{
    HILOG_INFO("Driver::Onscrollable");
    this->scrollable = scrollable;
    this->commonType.push_back(CommonType::SCROLLABLE);
    return this;
}

On* On::Checkable(bool checkable)
{
    HILOG_INFO("Driver::Oncheckable");
    this->checkable = checkable;
    this->commonType.push_back(CommonType::CHECKABLE);
    return this;
}

On* On::Checked(bool checked)
{
    HILOG_INFO("Driver::Onchecked");
    this->checked = checked;
    this->commonType.push_back(CommonType::CHECKED);
    return this;
}

bool IsEqual(OHOS::Ace::Platform::ComponentInfo& component, On& on)
{
    if (on.commonType.empty()) {
        HILOG_INFO("on is empty");
        return false;
    }
    for (auto iter = on.commonType.begin(); iter != on.commonType.end(); ++iter) {
        switch (*iter) {
            case CommonType::ID:
                if (on.id != component.compid)
                    return false;
                break;
            case CommonType::TEXT:
                switch(on.pattern_) {
                    case MatchPattern::EQUALS:
                        return component.text == on.text;
                    case MatchPattern::CONTAINS:
                        return component.text.find(on.text) != string::npos;
                    case MatchPattern::STARTS_WITH:
                        return component.text.find(on.text) == 0;
                    case MatchPattern::ENDS_WITH:
                        return (component.text.find(on.text) == (component.text.length() - on.text.length()));
                    default:
                        break;
                }
                break;
            case CommonType::TYPE:
                if (on.type != component.type)
                    return false;
                break;
            case CommonType::ENABLED:
                if (on.enabled != component.enabled)
                    return false;
                break;
            case CommonType::FOCUSED:
                if (on.focused != component.focused)
                    return false;
                break;
            case CommonType::SELECTED:
                if (on.selected != component.selected)
                    return false;
                break;
            case CommonType::CLICKABLE:
                if (on.clickable != component.clickable)
                    return false;
                break;
            case CommonType::LONGCLICKABLE:
                if (on.longClickable != component.longClickable)
                    return false;
                break;
            case CommonType::SCROLLABLE:
                if (on.scrollable != component.scrollable)
                    return false;
                break;
            case CommonType::CHECKED:
                if (on.checked != component.checked)
                    return false;
                break;
            case CommonType::CHECKABLE:
                if (on.checkable != component.checkable)
                    return false;
                break;
            default:
                HILOG_INFO("is not find");
                break;
        }
    }
    HILOG_INFO("IsEqual::IsEqual end");
    return false;
}

void GetComponentvalue(OHOS::Ace::Platform::ComponentInfo& component, On& on, OHOS::Ace::Platform::ComponentInfo& ret)
{
    if (IsEqual(component, on)) {
        ret = component;
        HILOG_INFO("GetComponentvalue return");
        return;
    }

    for (auto& child : component.children) {
        GetComponentvalue(child, on, ret);
    }
}

unique_ptr<Component> Driver::FindComponent(On on)
{
    HILOG_INFO("Driver::FindComponent begin");
    auto component = make_unique<Component>();
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    CHECK_NULL_RETURN(uiContent, component);
    uiContent->GetAllComponents(0, info);
    HILOG_INFO("GetAllComponents ok");
    OHOS::Ace::Platform::ComponentInfo ret;
    GetComponentvalue(info, on, ret);
    if (ret.left < 1 && ret.top < 1 && ret.width < 1 && ret.height < 1) {
        HILOG_INFO("not  find Component");
        return nullptr;
    }
    component->SetComponentInfo(ret);
    return component;
}

void GetComponentvalues(OHOS::Ace::Platform::ComponentInfo& info, On& on, vector<unique_ptr<Component>>& components)
{
    if (IsEqual(info, on)) {
        auto component = make_unique<Component>();
        component->SetComponentInfo(info);
        components.push_back(move(component));
    }
    for (auto& child : info.children) {
        GetComponentvalues(child, on, components);
    }
}

vector<unique_ptr<Component>> Driver::FindComponents(On on)
{
    HILOG_INFO("Driver::FindComponents");
    vector<unique_ptr<Component>> components;
    OHOS::Ace::Platform::ComponentInfo info;
    auto uiContent = GetUIContent();
    uiContent->GetAllComponents(0, info);
    GetComponentvalues(info, on, components);
    HILOG_INFO("Driver::FindComponents");
    return components;
}

} // namespace OHOS::UiTest
