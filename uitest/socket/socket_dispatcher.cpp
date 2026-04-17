/*
 * Copyright (c) 2026 Huawei Device Co., Ltd.
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

#include "socket_dispatcher.h"

#include <functional>
#include <unordered_map>

#include "../core/driver.h"
#include "json/json.h"
#include "socket_protocol.h"
#include "utils/log.h"

namespace OHOS::UiTest {
namespace {
namespace Json = ::Json;
using ComponentAction = std::function<void(Component&)>;
using DriverAction = std::function<void(Driver&)>;
using StringGetter = std::function<std::string(Component&)>;
using BoolGetter = std::function<bool(Component&)>;
using JsonGetter = std::function<Json::Value(Component&)>;
using DriverJsonGetter = std::function<Json::Value(Driver&)>;
using OnBoolSetter = On* (On::*)(bool);
using OnRelationSetter = On* (On::*)(On*);

Json::Value MakeRectJson(const Rect& rect)
{
    Json::Value value(Json::objectValue);
    value[JSON_KEY_LEFT] = rect.left;
    value[JSON_KEY_TOP] = rect.top;
    value[JSON_KEY_RIGHT] = rect.right;
    value[JSON_KEY_BOTTOM] = rect.bottom;
    return value;
}

Json::Value MakePointJson(const Point& point)
{
    Json::Value value(Json::objectValue);
    value[JSON_KEY_X] = point.x;
    value[JSON_KEY_Y] = point.y;
    return value;
}

Json::Value MakeComponentInfoJson(const OHOS::Ace::Platform::ComponentInfo& info)
{
    Json::Value value(Json::objectValue);
    value[JSON_KEY_COMPONENT_ID] = info.compid;
    value[JSON_KEY_TEXT] = info.text;
    value[JSON_KEY_TYPE] = info.type;
    value[JSON_KEY_LEFT] = info.left;
    value[JSON_KEY_TOP] = info.top;
    value[JSON_KEY_WIDTH] = info.width;
    value[JSON_KEY_HEIGHT] = info.height;
    value[JSON_KEY_CLICKABLE] = info.clickable;
    value[JSON_KEY_CHECKABLE] = info.checkable;
    value[JSON_KEY_CHECKED] = info.checked;
    value[JSON_KEY_SELECTED] = info.selected;
    value[JSON_KEY_SCROLLABLE] = info.scrollable;
    value[JSON_KEY_ENABLED] = info.enabled;
    value[JSON_KEY_FOCUSED] = info.focused;
    value[JSON_KEY_LONG_CLICKABLE] = info.longClickable;
    value[JSON_KEY_CHILDREN_COUNT] = static_cast<Json::UInt>(info.children.size());
    return value;
}

Json::Value MakeComponentsJson(const std::vector<std::unique_ptr<Component>>& components)
{
    Json::Value value(Json::arrayValue);
    for (const auto& component : components) {
        if (component == nullptr) {
            continue;
        }
        value.append(MakeComponentInfoJson(component->GetComponentInfo()));
    }
    return value;
}

bool ReadPointValue(const Json::Value& object, Point& point)
{
    return ReadJsonInt(object, JSON_KEY_X, point.x) && ReadJsonInt(object, JSON_KEY_Y, point.y);
}

bool ReadJsonPoint(const Json::Value& object, const char* key, Point& point)
{
    if (key == nullptr || !object.isObject() || !object.isMember(key)) {
        return false;
    }

    const Json::Value& item = object[key];
    if (!item.isObject()) {
        return false;
    }
    return ReadPointValue(item, point);
}

bool ReadOnStringConditions(const Json::Value& object, On& on, bool& hasCondition)
{
    std::string componentId;
    if (ReadJsonString(object, JSON_KEY_COMPONENT_ID, MAX_COMPONENT_ID_LENGTH, componentId)) {
        on.Id(componentId);
        hasCondition = true;
    }

    int matchPatternValue = static_cast<int>(MatchPattern::EQUALS);
    const bool hasMatchPattern = ReadJsonInt(object, JSON_KEY_MATCH_PATTERN, matchPatternValue);
    if (hasMatchPattern && (matchPatternValue < static_cast<int>(MatchPattern::EQUALS) ||
        matchPatternValue > static_cast<int>(MatchPattern::ENDS_WITH))) {
        return false;
    }

    std::string text;
    if (ReadJsonString(object, JSON_KEY_TEXT, SOCKET_TOTAL_SIZE, text)) {
        on.Text(text, static_cast<MatchPattern>(matchPatternValue));
        hasCondition = true;
    } else if (hasMatchPattern) {
        return false;
    }

    std::string type;
    if (ReadJsonString(object, JSON_KEY_TYPE, SOCKET_TOTAL_SIZE, type)) {
        on.Type(type);
        hasCondition = true;
    }

    return true;
}

bool ApplyOnBoolCondition(
    const Json::Value& object, const char* key, On& on, OnBoolSetter setter, bool& hasCondition)
{
    bool value = false;
    if (!object.isMember(key)) {
        return true;
    }
    if (!ReadJsonBool(object, key, value)) {
        return false;
    }
    (on.*setter)(value);
    hasCondition = true;
    return true;
}

bool ReadOnBoolConditions(const Json::Value& object, On& on, bool& hasCondition)
{
    return ApplyOnBoolCondition(object, JSON_KEY_CLICKABLE, on, &On::Clickable, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_LONG_CLICKABLE, on, &On::LongClickable, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_SCROLLABLE, on, &On::Scrollable, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_ENABLED, on, &On::Enabled, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_FOCUSED, on, &On::Focused, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_SELECTED, on, &On::Selected, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_CHECKED, on, &On::Checked, hasCondition) &&
        ApplyOnBoolCondition(object, JSON_KEY_CHECKABLE, on, &On::Checkable, hasCondition);
}

bool ReadOnObject(const Json::Value& object, On& on)
{
    if (!object.isObject()) {
        return false;
    }

    bool hasCondition = false;
    if (!ReadOnStringConditions(object, on, hasCondition)) {
        return false;
    }
    if (!ReadOnBoolConditions(object, on, hasCondition)) {
        return false;
    }
    const auto readNestedCondition = [&object, &on, &hasCondition](const char* key, OnRelationSetter setter) {
        if (!object.isMember(key)) {
            return true;
        }

        On nested;
        if (!ReadOnObject(object[key], nested)) {
            return false;
        }
        (on.*setter)(&nested);
        hasCondition = true;
        return true;
    };
    if (!readNestedCondition(JSON_KEY_IS_BEFORE, &On::IsBefore)) {
        return false;
    }
    if (!readNestedCondition(JSON_KEY_IS_AFTER, &On::IsAfter)) {
        return false;
    }
    if (!readNestedCondition(JSON_KEY_WITHIN, &On::WithIn)) {
        return false;
    }
    return hasCondition;
}

bool ReadOnParams(const Json::Value& params, On& on)
{
    if (!params.isObject()) {
        return false;
    }
    if (params.isMember(JSON_KEY_ON)) {
        return ReadOnObject(params[JSON_KEY_ON], on);
    }
    return ReadOnObject(params, on);
}

bool ReadPointerMatrixObject(const Json::Value& object, PointerMatrix& pointers)
{
    if (!object.isObject()) {
        return false;
    }

    int fingers = 0;
    int steps = 0;
    if (!ReadJsonInt(object, JSON_KEY_FINGERS, fingers) || fingers <= 0) {
        return false;
    }
    if (!ReadJsonInt(object, JSON_KEY_STEPS, steps) || steps <= 1) {
        return false;
    }
    if (!object.isMember(JSON_KEY_POINTS) || !object[JSON_KEY_POINTS].isArray()) {
        return false;
    }

    pointers.Create(static_cast<uint32_t>(fingers), static_cast<uint32_t>(steps));
    const Json::Value& points = object[JSON_KEY_POINTS];
    for (Json::ArrayIndex index = 0; index < points.size(); index++) {
        const Json::Value& item = points[index];
        if (!item.isObject()) {
            return false;
        }

        int finger = 0;
        int step = 0;
        Point point;
        if (!ReadJsonInt(item, JSON_KEY_FINGER, finger) || !ReadJsonInt(item, JSON_KEY_STEP, step) ||
            finger < 0 || finger >= fingers || step < 0 || step >= steps || !ReadPointValue(item, point)) {
            return false;
        }
        pointers.SetPoint(static_cast<uint32_t>(finger), static_cast<uint32_t>(step), point);
    }
    return true;
}

bool ReadPointerMatrixParams(const Json::Value& params, PointerMatrix& pointers)
{
    if (!params.isObject()) {
        return false;
    }
    if (params.isMember(JSON_KEY_POINTER_MATRIX)) {
        return ReadPointerMatrixObject(params[JSON_KEY_POINTER_MATRIX], pointers);
    }
    return ReadPointerMatrixObject(params, pointers);
}

SocketRequestPtr DecodeEmptyRequest(SocketCommand command, const Json::Value&, const Json::Value&)
{
    auto request = std::make_unique<SocketRequestBase>(command, SocketRequestType::NONE);
    return request;
}

SocketRequestPtr DecodeComponentRequest(SocketCommand command, const Json::Value& root, const Json::Value& params)
{
    auto request = std::make_unique<ComponentRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadComponentId(root, params, request->componentId)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeInputTextRequest(SocketCommand command, const Json::Value& root, const Json::Value& params)
{
    auto request = std::make_unique<TextComponentRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadComponentId(root, params, request->componentId)) {
        return nullptr;
    }
    if (!ReadJsonString(params, JSON_KEY_TEXT, SOCKET_TOTAL_SIZE, request->text)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeScaleRequest(SocketCommand command, const Json::Value& root, const Json::Value& params)
{
    auto request = std::make_unique<ScaleComponentRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadComponentId(root, params, request->componentId)) {
        return nullptr;
    }
    if (!ReadJsonDouble(params, JSON_KEY_SCALE, request->scale)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeTargetComponentRequest(
    SocketCommand command, const Json::Value& root, const Json::Value& params)
{
    auto request = std::make_unique<TargetComponentRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadComponentId(root, params, request->componentId)) {
        return nullptr;
    }
    if (!params.isObject() || !params.isMember(JSON_KEY_TARGET_ON)) {
        return nullptr;
    }
    if (!ReadOnObject(params[JSON_KEY_TARGET_ON], request->targetOn)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeDelayRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverDelayRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonInt(params, JSON_KEY_DURATION, request->duration)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeKeyRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverKeyRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonInt(params, JSON_KEY_KEY_CODE, request->keyCode)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeCombineKeyRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverCombineKeyRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonInt(params, JSON_KEY_KEY0, request->key0) || !ReadJsonInt(params, JSON_KEY_KEY1, request->key1)) {
        return nullptr;
    }
    ReadJsonInt(params, JSON_KEY_KEY2, request->key2);
    return request;
}

SocketRequestPtr DecodePointRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverPointRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonInt(params, JSON_KEY_X, request->x) || !ReadJsonInt(params, JSON_KEY_Y, request->y)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeSwipeRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverSwipeRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonInt(params, JSON_KEY_START_X, request->startX) ||
        !ReadJsonInt(params, JSON_KEY_START_Y, request->startY) ||
        !ReadJsonInt(params, JSON_KEY_END_X, request->endX) ||
        !ReadJsonInt(params, JSON_KEY_END_Y, request->endY)) {
        return nullptr;
    }
    ReadJsonInt(params, JSON_KEY_SPEED, request->speed);
    return request;
}

SocketRequestPtr DecodeDirectionFlingRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverDirectionFlingRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    int direction = 0;
    if (!ReadJsonInt(params, JSON_KEY_DIRECTION, direction)) {
        return nullptr;
    }
    if (direction < static_cast<int>(UiDirection::LEFT) || direction > static_cast<int>(UiDirection::DOWN)) {
        return nullptr;
    }
    request->direction = static_cast<UiDirection>(direction);
    ReadJsonInt(params, JSON_KEY_SPEED, request->speed);
    return request;
}

SocketRequestPtr DecodePointFlingRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverPointFlingRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonPoint(params, JSON_KEY_FROM, request->from) ||
        !ReadJsonPoint(params, JSON_KEY_TO, request->to) ||
        !ReadJsonInt(params, JSON_KEY_STEP_LEN, request->stepLen)) {
        return nullptr;
    }
    ReadJsonInt(params, JSON_KEY_SPEED, request->speed);
    return request;
}

SocketRequestPtr DecodeDragRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverDragRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadJsonInt(params, JSON_KEY_START_X, request->startX) ||
        !ReadJsonInt(params, JSON_KEY_START_Y, request->startY) ||
        !ReadJsonInt(params, JSON_KEY_END_X, request->endX) ||
        !ReadJsonInt(params, JSON_KEY_END_Y, request->endY)) {
        return nullptr;
    }
    ReadJsonInt(params, JSON_KEY_SPEED, request->speed);
    return request;
}

SocketRequestPtr DecodeDisplaySizeRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverDisplaySizeRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!params.isObject()) {
        return request;
    }
    if (!params.isMember(JSON_KEY_DISPLAY_ID)) {
        return request;
    }
    if (!ReadJsonInt(params, JSON_KEY_DISPLAY_ID, request->displayId)) {
        return nullptr;
    }
    if (request->displayId != -1 && request->displayId != 0) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodeDisplayRotationRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverDisplayRotationRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    int rotation = 0;
    if (!ReadJsonInt(params, JSON_KEY_ROTATION, rotation)) {
        return nullptr;
    }
    if (rotation < static_cast<int>(DisplayRotation::ROTATION_0) ||
        rotation > static_cast<int>(DisplayRotation::ROTATION_270)) {
        return nullptr;
    }
    request->rotation = static_cast<DisplayRotation>(rotation);
    return request;
}

SocketRequestPtr DecodeOnRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverOnRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadOnParams(params, request->on)) {
        return nullptr;
    }
    return request;
}

SocketRequestPtr DecodePointerMatrixRequest(SocketCommand command, const Json::Value&, const Json::Value& params)
{
    auto request = std::make_unique<DriverPointerMatrixRequest>(command);
    if (request == nullptr) {
        return nullptr;
    }
    if (!ReadPointerMatrixParams(params, *request->pointers)) {
        return nullptr;
    }
    ReadJsonInt(params, JSON_KEY_SPEED, request->speed);
    return request;
}

template<typename T>
const T* ExpectRequest(int clientFd, const SocketRequestBase& request, SocketRequestType expectedType)
{
    const auto* typedRequest = CastSocketRequest<T>(request, expectedType);
    if (typedRequest == nullptr) {
        SendErrorMessage(clientFd, request.command, "invalid params");
    }
    return typedRequest;
}

bool GetTargetComponent(int clientFd, const ComponentRequest& request, std::unique_ptr<Component>& component)
{
    if (request.componentId.empty()) {
        SendErrorMessage(clientFd, request.command, "invalid params");
        return false;
    }

    Driver driver;
    On on;
    component = driver.FindComponent(*on.Id(request.componentId));
    if (component == nullptr) {
        HILOG_ERROR("not find component, componentId is %s!", request.componentId.c_str());
        SendErrorMessage(clientFd, request.command, "component not found");
        return false;
    }
    return true;
}

bool HandleComponentAction(int clientFd, const ComponentRequest& request, const ComponentAction& action)
{
    std::unique_ptr<Component> component;
    if (!GetTargetComponent(clientFd, request, component)) {
        return false;
    }
    action(*component);
    SendSuccessMessage(clientFd, request.command);
    return true;
}

bool HandleComponentStringQuery(int clientFd, const ComponentRequest& request, const StringGetter& getter)
{
    std::unique_ptr<Component> component;
    if (!GetTargetComponent(clientFd, request, component)) {
        return false;
    }
    SendStrMessage(clientFd, request.command, getter(*component));
    return true;
}

bool HandleComponentBoolQuery(int clientFd, const ComponentRequest& request, const BoolGetter& getter)
{
    std::unique_ptr<Component> component;
    if (!GetTargetComponent(clientFd, request, component)) {
        return false;
    }
    SendBoolMessage(clientFd, request.command, getter(*component));
    return true;
}

bool HandleComponentJsonQuery(int clientFd, const ComponentRequest& request, const JsonGetter& getter)
{
    std::unique_ptr<Component> component;
    if (!GetTargetComponent(clientFd, request, component)) {
        return false;
    }
    SendJsonMessage(clientFd, request.command, getter(*component));
    return true;
}

bool HandleDriverAction(int clientFd, SocketCommand command, const DriverAction& action)
{
    Driver driver;
    action(driver);
    SendSuccessMessage(clientFd, command);
    return true;
}

bool HandleDriverJsonQuery(int clientFd, SocketCommand command, const DriverJsonGetter& getter)
{
    Driver driver;
    SendJsonMessage(clientFd, command, getter(driver));
    return true;
}

bool HandleClick(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentAction(clientFd, *componentRequest, [](Component& component) { component.Click(); });
}

bool HandleDoubleClick(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentAction(
        clientFd, *componentRequest, [](Component& component) { component.DoubleClick(); });
}

bool HandleLongClick(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentAction(clientFd, *componentRequest, [](Component& component) { component.LongClick(); });
}

bool HandleGetText(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentStringQuery(
        clientFd, *componentRequest, [](Component& component) { return component.GetText(); });
}

bool HandleGetType(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentStringQuery(
        clientFd, *componentRequest, [](Component& component) { return component.GetType(); });
}

bool HandleGetId(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentStringQuery(
        clientFd, *componentRequest, [](Component& component) { return component.GetId(); });
}

bool HandleIsClickable(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsClickable();
            return result != nullptr && *result;
        });
}

bool HandleIsLongClickable(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsLongClickable();
            return result != nullptr && *result;
        });
}

bool HandleIsScrollable(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsScrollable();
            return result != nullptr && *result;
        });
}

bool HandleIsEnabled(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsEnabled();
            return result != nullptr && *result;
        });
}

bool HandleIsFocused(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsFocused();
            return result != nullptr && *result;
        });
}

bool HandleIsSelected(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsSelected();
            return result != nullptr && *result;
        });
}

bool HandleIsChecked(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsChecked();
            return result != nullptr && *result;
        });
}

bool HandleIsCheckable(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentBoolQuery(clientFd, *componentRequest,
        [](Component& component) {
            auto result = component.IsCheckable();
            return result != nullptr && *result;
        });
}

bool HandleInputText(int clientFd, const SocketRequestBase& request)
{
    const auto* textRequest = ExpectRequest<TextComponentRequest>(clientFd, request, SocketRequestType::COMPONENT_TEXT);
    if (textRequest == nullptr) {
        return false;
    }
    const std::string text = textRequest->text;
    return HandleComponentAction(clientFd, *textRequest, [text](Component& component) { component.InputText(text); });
}

bool HandleGetBounds(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentJsonQuery(clientFd, *componentRequest,
        [](Component& component) { return MakeRectJson(component.GetBounds()); });
}

bool HandleGetBoundsCenter(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentJsonQuery(clientFd, *componentRequest,
        [](Component& component) { return MakePointJson(component.GetBoundsCenter()); });
}

bool HandlePinchOut(int clientFd, const SocketRequestBase& request)
{
    const auto* scaleRequest = ExpectRequest<ScaleComponentRequest>(
        clientFd, request, SocketRequestType::COMPONENT_SCALE);
    if (scaleRequest == nullptr) {
        return false;
    }
    const float scale = static_cast<float>(scaleRequest->scale);
    return HandleComponentAction(clientFd, *scaleRequest, [scale](Component& component) { component.PinchOut(scale); });
}

bool HandlePinchIn(int clientFd, const SocketRequestBase& request)
{
    const auto* scaleRequest = ExpectRequest<ScaleComponentRequest>(
        clientFd, request, SocketRequestType::COMPONENT_SCALE);
    if (scaleRequest == nullptr) {
        return false;
    }
    const float scale = static_cast<float>(scaleRequest->scale);
    return HandleComponentAction(clientFd, *scaleRequest, [scale](Component& component) { component.PinchIn(scale); });
}

bool HandleGetComponentInfo(int clientFd, const SocketRequestBase& request)
{
    const auto* componentRequest = ExpectRequest<ComponentRequest>(clientFd, request, SocketRequestType::COMPONENT);
    if (componentRequest == nullptr) {
        return false;
    }
    return HandleComponentJsonQuery(clientFd, *componentRequest,
        [](Component& component) { return MakeComponentInfoJson(component.GetComponentInfo()); });
}

bool HandleScrollSearch(int clientFd, const SocketRequestBase& request)
{
    const auto* targetRequest = ExpectRequest<TargetComponentRequest>(
        clientFd, request, SocketRequestType::COMPONENT_TARGET);
    if (targetRequest == nullptr) {
        return false;
    }

    std::unique_ptr<Component> component;
    if (!GetTargetComponent(clientFd, *targetRequest, component)) {
        return false;
    }

    auto targetComponent = component->ScrollSearch(targetRequest->targetOn);
    if (targetComponent == nullptr) {
        SendErrorMessage(clientFd, targetRequest->command, "component not found");
        return false;
    }

    SendJsonMessage(clientFd, targetRequest->command, MakeComponentInfoJson(targetComponent->GetComponentInfo()));
    return true;
}

bool HandleDriverDelayMs(int clientFd, const SocketRequestBase& request)
{
    const auto* delayRequest = ExpectRequest<DriverDelayRequest>(clientFd, request, SocketRequestType::DRIVER_DELAY);
    if (delayRequest == nullptr) {
        return false;
    }
    const int duration = delayRequest->duration;
    return HandleDriverAction(clientFd, request.command, [duration](Driver& driver) { driver.DelayMs(duration); });
}

bool HandleDriverPressBack(int clientFd, const SocketRequestBase& request)
{
    return HandleDriverAction(clientFd, request.command, [](Driver& driver) { driver.PressBack(); });
}

bool HandleDriverTriggerKey(int clientFd, const SocketRequestBase& request)
{
    const auto* keyRequest = ExpectRequest<DriverKeyRequest>(clientFd, request, SocketRequestType::DRIVER_KEY);
    if (keyRequest == nullptr) {
        return false;
    }
    const int keyCode = keyRequest->keyCode;
    return HandleDriverAction(clientFd, request.command, [keyCode](Driver& driver) { driver.TriggerKey(keyCode); });
}

bool HandleDriverTriggerCombineKeys(int clientFd, const SocketRequestBase& request)
{
    const auto* keyRequest = ExpectRequest<DriverCombineKeyRequest>(
        clientFd, request, SocketRequestType::DRIVER_COMBINE_KEY);
    if (keyRequest == nullptr) {
        return false;
    }
    const int key0 = keyRequest->key0;
    const int key1 = keyRequest->key1;
    const int key2 = keyRequest->key2;
    return HandleDriverAction(clientFd, request.command,
        [key0, key1, key2](Driver& driver) { driver.TriggerCombineKeys(key0, key1, key2); });
}

bool HandleDriverInjectMultiPointerAction(int clientFd, const SocketRequestBase& request)
{
    const auto* pointerRequest = ExpectRequest<DriverPointerMatrixRequest>(
        clientFd, request, SocketRequestType::DRIVER_POINTER_MATRIX);
    if (pointerRequest == nullptr) {
        return false;
    }

    Driver driver;
    const bool result = driver.InjectMultiPointerAction(*pointerRequest->pointers,
        static_cast<uint32_t>(pointerRequest->speed));
    SendBoolMessage(clientFd, request.command, result);
    return true;
}

bool HandleDriverClick(int clientFd, const SocketRequestBase& request)
{
    const auto* pointRequest = ExpectRequest<DriverPointRequest>(clientFd, request, SocketRequestType::DRIVER_POINT);
    if (pointRequest == nullptr) {
        return false;
    }
    const int x = pointRequest->x;
    const int y = pointRequest->y;
    return HandleDriverAction(clientFd, request.command, [x, y](Driver& driver) { driver.Click(x, y); });
}

bool HandleDriverDoubleClick(int clientFd, const SocketRequestBase& request)
{
    const auto* pointRequest = ExpectRequest<DriverPointRequest>(clientFd, request, SocketRequestType::DRIVER_POINT);
    if (pointRequest == nullptr) {
        return false;
    }
    const int x = pointRequest->x;
    const int y = pointRequest->y;
    return HandleDriverAction(
        clientFd, request.command, [x, y](Driver& driver) { driver.DoubleClick(x, y); });
}

bool HandleDriverLongClick(int clientFd, const SocketRequestBase& request)
{
    const auto* pointRequest = ExpectRequest<DriverPointRequest>(clientFd, request, SocketRequestType::DRIVER_POINT);
    if (pointRequest == nullptr) {
        return false;
    }
    const int x = pointRequest->x;
    const int y = pointRequest->y;
    return HandleDriverAction(clientFd, request.command, [x, y](Driver& driver) { driver.LongClick(x, y); });
}

bool HandleDriverSwipe(int clientFd, const SocketRequestBase& request)
{
    const auto* swipeRequest = ExpectRequest<DriverSwipeRequest>(clientFd, request, SocketRequestType::DRIVER_SWIPE);
    if (swipeRequest == nullptr) {
        return false;
    }
    const int startX = swipeRequest->startX;
    const int startY = swipeRequest->startY;
    const int endX = swipeRequest->endX;
    const int endY = swipeRequest->endY;
    const int speed = swipeRequest->speed;
    return HandleDriverAction(clientFd, request.command, [startX, startY, endX, endY, speed](Driver& driver) {
        driver.Swipe(startX, startY, endX, endY, static_cast<uint32_t>(speed));
    });
}

bool HandleDriverDrag(int clientFd, const SocketRequestBase& request)
{
    const auto* dragRequest = ExpectRequest<DriverDragRequest>(clientFd, request, SocketRequestType::DRIVER_DRAG);
    if (dragRequest == nullptr) {
        return false;
    }
    const int startX = dragRequest->startX;
    const int startY = dragRequest->startY;
    const int endX = dragRequest->endX;
    const int endY = dragRequest->endY;
    const int speed = dragRequest->speed;
    return HandleDriverAction(clientFd, request.command, [startX, startY, endX, endY, speed](Driver& driver) {
        driver.Drag(startX, startY, endX, endY, static_cast<uint32_t>(speed));
    });
}

bool HandleDriverDirectionFling(int clientFd, const SocketRequestBase& request)
{
    const auto* flingRequest = ExpectRequest<DriverDirectionFlingRequest>(
        clientFd, request, SocketRequestType::DRIVER_FLING_DIRECTION);
    if (flingRequest == nullptr) {
        return false;
    }

    const UiDirection direction = flingRequest->direction;
    const int speed = flingRequest->speed;
    return HandleDriverAction(clientFd, request.command, [direction, speed](Driver& driver) {
        driver.Fling(direction, static_cast<uint32_t>(speed));
    });
}

bool HandleDriverPointFling(int clientFd, const SocketRequestBase& request)
{
    const auto* flingRequest = ExpectRequest<DriverPointFlingRequest>(
        clientFd, request, SocketRequestType::DRIVER_FLING_POINT);
    if (flingRequest == nullptr) {
        return false;
    }

    const Point from = flingRequest->from;
    const Point to = flingRequest->to;
    const int stepLen = flingRequest->stepLen;
    const int speed = flingRequest->speed;
    return HandleDriverAction(clientFd, request.command, [from, to, stepLen, speed](Driver& driver) {
        driver.Fling(from, to, stepLen, static_cast<uint32_t>(speed));
    });
}

bool HandleDriverFindComponent(int clientFd, const SocketRequestBase& request)
{
    const auto* onRequest = ExpectRequest<DriverOnRequest>(clientFd, request, SocketRequestType::DRIVER_ON);
    if (onRequest == nullptr) {
        return false;
    }
    const On on = onRequest->on;
    return HandleDriverJsonQuery(clientFd, request.command, [on](Driver& driver) {
        auto component = driver.FindComponent(on);
        return component == nullptr ? Json::Value() : MakeComponentInfoJson(component->GetComponentInfo());
    });
}

bool HandleDriverFindComponents(int clientFd, const SocketRequestBase& request)
{
    const auto* onRequest = ExpectRequest<DriverOnRequest>(clientFd, request, SocketRequestType::DRIVER_ON);
    if (onRequest == nullptr) {
        return false;
    }
    const On on = onRequest->on;
    return HandleDriverJsonQuery(clientFd, request.command, [on](Driver& driver) {
        auto components = driver.FindComponents(on);
        return MakeComponentsJson(components);
    });
}

bool HandleDriverGetDisplaySize(int clientFd, const SocketRequestBase& request)
{
    const auto* displaySizeRequest = ExpectRequest<DriverDisplaySizeRequest>(
        clientFd, request, SocketRequestType::DRIVER_DISPLAY_SIZE);
    if (displaySizeRequest == nullptr) {
        return false;
    }

    Driver driver;
    const Point point = driver.GetDisplaySize(displaySizeRequest->displayId);
    if (point.x <= 0 || point.y <= 0) {
        SendErrorMessage(clientFd, request.command, "get display size failed");
        return false;
    }
    SendJsonMessage(clientFd, request.command, MakePointJson(point));
    return true;
}

bool HandleDriverSetDisplayRotation(int clientFd, const SocketRequestBase& request)
{
    const auto* rotationRequest = ExpectRequest<DriverDisplayRotationRequest>(
        clientFd, request, SocketRequestType::DRIVER_DISPLAY_ROTATION);
    if (rotationRequest == nullptr) {
        return false;
    }
    const DisplayRotation rotation = rotationRequest->rotation;
    return HandleDriverAction(clientFd, request.command, [rotation](Driver& driver) {
        driver.SetDisplayRotation(rotation);
    });
}
} // namespace

const SocketHandlerEntry* FindSocketHandler(SocketCommand command)
{
    static const std::unordered_map<int32_t, SocketHandlerEntry> handlerMap = {
        {ToCommandValue(SocketCommand::COMPONENT_CLICK), {&DecodeComponentRequest, &HandleClick}},
        {ToCommandValue(SocketCommand::COMPONENT_DOUBLE_CLICK), {&DecodeComponentRequest, &HandleDoubleClick}},
        {ToCommandValue(SocketCommand::COMPONENT_LONG_CLICK), {&DecodeComponentRequest, &HandleLongClick}},
        {ToCommandValue(SocketCommand::COMPONENT_GET_ID), {&DecodeComponentRequest, &HandleGetId}},
        {ToCommandValue(SocketCommand::COMPONENT_GET_TEXT), {&DecodeComponentRequest, &HandleGetText}},
        {ToCommandValue(SocketCommand::COMPONENT_GET_TYPE), {&DecodeComponentRequest, &HandleGetType}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_CLICKABLE), {&DecodeComponentRequest, &HandleIsClickable}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_LONG_CLICKABLE),
            {&DecodeComponentRequest, &HandleIsLongClickable}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_SCROLLABLE), {&DecodeComponentRequest, &HandleIsScrollable}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_ENABLED), {&DecodeComponentRequest, &HandleIsEnabled}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_FOCUSED), {&DecodeComponentRequest, &HandleIsFocused}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_SELECTED), {&DecodeComponentRequest, &HandleIsSelected}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_CHECKED), {&DecodeComponentRequest, &HandleIsChecked}},
        {ToCommandValue(SocketCommand::COMPONENT_IS_CHECKABLE), {&DecodeComponentRequest, &HandleIsCheckable}},
        {ToCommandValue(SocketCommand::COMPONENT_INPUT_TEXT), {&DecodeInputTextRequest, &HandleInputText}},
        {ToCommandValue(SocketCommand::COMPONENT_GET_BOUNDS), {&DecodeComponentRequest, &HandleGetBounds}},
        {ToCommandValue(SocketCommand::COMPONENT_GET_BOUNDS_CENTER), {&DecodeComponentRequest, &HandleGetBoundsCenter}},
        {ToCommandValue(SocketCommand::COMPONENT_PINCH_OUT), {&DecodeScaleRequest, &HandlePinchOut}},
        {ToCommandValue(SocketCommand::COMPONENT_PINCH_IN), {&DecodeScaleRequest, &HandlePinchIn}},
        {ToCommandValue(SocketCommand::COMPONENT_GET_COMPONENT_INFO),
            {&DecodeComponentRequest, &HandleGetComponentInfo}},
        {ToCommandValue(SocketCommand::COMPONENT_SCROLL_SEARCH), {&DecodeTargetComponentRequest, &HandleScrollSearch}},
        {ToCommandValue(SocketCommand::DRIVER_DELAY_MS), {&DecodeDelayRequest, &HandleDriverDelayMs}},
        {ToCommandValue(SocketCommand::DRIVER_PRESS_BACK), {&DecodeEmptyRequest, &HandleDriverPressBack}},
        {ToCommandValue(SocketCommand::DRIVER_TRIGGER_KEY), {&DecodeKeyRequest, &HandleDriverTriggerKey}},
        {ToCommandValue(SocketCommand::DRIVER_TRIGGER_COMBINE_KEYS),
            {&DecodeCombineKeyRequest, &HandleDriverTriggerCombineKeys}},
        {ToCommandValue(SocketCommand::DRIVER_INJECT_MULTI_POINTER_ACTION),
            {&DecodePointerMatrixRequest, &HandleDriverInjectMultiPointerAction}},
        {ToCommandValue(SocketCommand::DRIVER_CLICK), {&DecodePointRequest, &HandleDriverClick}},
        {ToCommandValue(SocketCommand::DRIVER_DOUBLE_CLICK), {&DecodePointRequest, &HandleDriverDoubleClick}},
        {ToCommandValue(SocketCommand::DRIVER_LONG_CLICK), {&DecodePointRequest, &HandleDriverLongClick}},
        {ToCommandValue(SocketCommand::DRIVER_SWIPE), {&DecodeSwipeRequest, &HandleDriverSwipe}},
        {ToCommandValue(SocketCommand::DRIVER_DRAG), {&DecodeDragRequest, &HandleDriverDrag}},
        {ToCommandValue(SocketCommand::DRIVER_FLING_DIRECTION),
            {&DecodeDirectionFlingRequest, &HandleDriverDirectionFling}},
        {ToCommandValue(SocketCommand::DRIVER_FIND_COMPONENT), {&DecodeOnRequest, &HandleDriverFindComponent}},
        {ToCommandValue(SocketCommand::DRIVER_FIND_COMPONENTS), {&DecodeOnRequest, &HandleDriverFindComponents}},
        {ToCommandValue(SocketCommand::DRIVER_GET_DISPLAY_SIZE),
            {&DecodeDisplaySizeRequest, &HandleDriverGetDisplaySize}},
        {ToCommandValue(SocketCommand::DRIVER_FLING_POINT),
            {&DecodePointFlingRequest, &HandleDriverPointFling}},
        {ToCommandValue(SocketCommand::DRIVER_SET_DISPLAY_ROTATION),
            {&DecodeDisplayRotationRequest, &HandleDriverSetDisplayRotation}},
    };
    auto it = handlerMap.find(ToCommandValue(command));
    return it == handlerMap.end() ? nullptr : &it->second;
}

bool DispatchSocketRequest(int clientFd, const SocketRequestBase& request)
{
    const auto* handler = FindSocketHandler(request.command);
    if (handler == nullptr || handler->handle == nullptr) {
        HILOG_ERROR("unsupported command is %d", ToCommandValue(request.command));
        SendErrorMessage(clientFd, request.command, "unsupported function");
        return false;
    }
    if (!handler->handle(clientFd, request)) {
        HILOG_ERROR("handle function failed, command is %d", ToCommandValue(request.command));
    }
    return true;
}
} // namespace OHOS::UiTest
