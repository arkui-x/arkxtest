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

#ifndef UITEST_SOCKET_REQUEST_H
#define UITEST_SOCKET_REQUEST_H

#include <cstdint>
#include <memory>
#include <string>

#include "common_type.h"
#include "../core/driver.h"
#include "json/json.h"

namespace OHOS::UiTest {
constexpr size_t MAX_COMPONENT_ID_LENGTH = 256;

enum class SocketCommand : int32_t {
    COMPONENT_CLICK = 1,
    COMPONENT_DOUBLE_CLICK = 2,
    COMPONENT_LONG_CLICK = 3,
    COMPONENT_GET_ID = 4,
    COMPONENT_GET_TEXT = 5,
    COMPONENT_GET_TYPE = 6,
    COMPONENT_IS_CLICKABLE = 7,
    COMPONENT_IS_LONG_CLICKABLE = 8,
    COMPONENT_IS_SCROLLABLE = 9,
    COMPONENT_IS_ENABLED = 10,
    COMPONENT_IS_FOCUSED = 11,
    COMPONENT_IS_SELECTED = 12,
    COMPONENT_IS_CHECKED = 13,
    COMPONENT_IS_CHECKABLE = 14,
    COMPONENT_INPUT_TEXT = 15,
    COMPONENT_GET_BOUNDS = 19,
    COMPONENT_GET_BOUNDS_CENTER = 20,
    COMPONENT_PINCH_OUT = 21,
    COMPONENT_PINCH_IN = 22,
    COMPONENT_GET_COMPONENT_INFO = 23,
    COMPONENT_SCROLL_SEARCH = 24,
    DRIVER_DELAY_MS = 100,
    DRIVER_PRESS_BACK = 101,
    DRIVER_TRIGGER_KEY = 103,
    DRIVER_TRIGGER_COMBINE_KEYS = 104,
    DRIVER_INJECT_MULTI_POINTER_ACTION = 105,
    DRIVER_CLICK = 106,
    DRIVER_DOUBLE_CLICK = 107,
    DRIVER_LONG_CLICK = 108,
    DRIVER_SWIPE = 109,
    DRIVER_FLING_DIRECTION = 110,
    DRIVER_FIND_COMPONENT = 111,
    DRIVER_FIND_COMPONENTS = 112,
    DRIVER_GET_DISPLAY_SIZE = 113,
    DRIVER_FLING_POINT = 114,
    DRIVER_DRAG = 115,
    DRIVER_SET_DISPLAY_ROTATION = 116,
};

inline int32_t ToCommandValue(SocketCommand command)
{
    return static_cast<int32_t>(command);
}

constexpr char JSON_KEY_COMMAND[] = "command";
constexpr char JSON_KEY_RESULT[] = "result";
constexpr char JSON_KEY_ERR_CODE[] = "err_code";
constexpr char JSON_KEY_ERR_MES[] = "err_mes";
constexpr char JSON_KEY_PARAMS[] = "params";
constexpr char JSON_KEY_COMPONENT_ID[] = "componentId";
constexpr char JSON_KEY_TARGET_ON[] = "targetOn";
constexpr char JSON_KEY_TEXT[] = "text";
constexpr char JSON_KEY_MATCH_PATTERN[] = "matchPattern";
constexpr char JSON_KEY_SPEED[] = "speed";
constexpr char JSON_KEY_SCALE[] = "scale";
constexpr char JSON_KEY_DURATION[] = "duration";
constexpr char JSON_KEY_KEY_CODE[] = "keyCode";
constexpr char JSON_KEY_KEY0[] = "key0";
constexpr char JSON_KEY_KEY1[] = "key1";
constexpr char JSON_KEY_KEY2[] = "key2";
constexpr char JSON_KEY_X[] = "x";
constexpr char JSON_KEY_Y[] = "y";
constexpr char JSON_KEY_START_X[] = "startX";
constexpr char JSON_KEY_START_Y[] = "startY";
constexpr char JSON_KEY_END_X[] = "endX";
constexpr char JSON_KEY_END_Y[] = "endY";
constexpr char JSON_KEY_FROM[] = "from";
constexpr char JSON_KEY_TO[] = "to";
constexpr char JSON_KEY_STEP_LEN[] = "stepLen";
constexpr char JSON_KEY_DIRECTION[] = "direction";
constexpr char JSON_KEY_DISPLAY_ID[] = "displayId";
constexpr char JSON_KEY_ROTATION[] = "rotation";
constexpr char JSON_KEY_ON[] = "on";
constexpr char JSON_KEY_IS_BEFORE[] = "isBefore";
constexpr char JSON_KEY_IS_AFTER[] = "isAfter";
constexpr char JSON_KEY_WITHIN[] = "within";
constexpr char JSON_KEY_POINTER_MATRIX[] = "pointerMatrix";
constexpr char JSON_KEY_FINGERS[] = "fingers";
constexpr char JSON_KEY_STEPS[] = "steps";
constexpr char JSON_KEY_POINTS[] = "points";
constexpr char JSON_KEY_FINGER[] = "finger";
constexpr char JSON_KEY_STEP[] = "step";
constexpr char JSON_KEY_LEFT[] = "left";
constexpr char JSON_KEY_TOP[] = "top";
constexpr char JSON_KEY_RIGHT[] = "right";
constexpr char JSON_KEY_BOTTOM[] = "bottom";
constexpr char JSON_KEY_WIDTH[] = "width";
constexpr char JSON_KEY_HEIGHT[] = "height";
constexpr char JSON_KEY_TYPE[] = "type";
constexpr char JSON_KEY_CLICKABLE[] = "clickable";
constexpr char JSON_KEY_CHECKABLE[] = "checkable";
constexpr char JSON_KEY_CHECKED[] = "checked";
constexpr char JSON_KEY_SELECTED[] = "selected";
constexpr char JSON_KEY_SCROLLABLE[] = "scrollable";
constexpr char JSON_KEY_ENABLED[] = "enabled";
constexpr char JSON_KEY_FOCUSED[] = "focused";
constexpr char JSON_KEY_LONG_CLICKABLE[] = "longClickable";
constexpr char JSON_KEY_CHILDREN_COUNT[] = "childrenCount";

enum class SocketRequestType {
    NONE = 0,
    COMPONENT,
    COMPONENT_TEXT,
    COMPONENT_SCALE,
    COMPONENT_TARGET,
    DRIVER_DELAY,
    DRIVER_KEY,
    DRIVER_COMBINE_KEY,
    DRIVER_POINT,
    DRIVER_SWIPE,
    DRIVER_FLING_DIRECTION,
    DRIVER_FLING_POINT,
    DRIVER_DRAG,
    DRIVER_DISPLAY_SIZE,
    DRIVER_DISPLAY_ROTATION,
    DRIVER_ON,
    DRIVER_POINTER_MATRIX,
};

struct SocketRequestBase {
    SocketRequestBase(SocketCommand cmd, SocketRequestType type) : command(cmd), requestType(type) {}
    virtual ~SocketRequestBase() = default;

    SocketCommand command;
    SocketRequestType requestType;
};

struct ComponentRequest : SocketRequestBase {
    explicit ComponentRequest(SocketCommand command, SocketRequestType type = SocketRequestType::COMPONENT)
        : SocketRequestBase(command, type) {}

    std::string componentId;
};

struct TextComponentRequest : ComponentRequest {
    explicit TextComponentRequest(SocketCommand command)
        : ComponentRequest(command, SocketRequestType::COMPONENT_TEXT) {}

    std::string text;
};

struct ScaleComponentRequest : ComponentRequest {
    explicit ScaleComponentRequest(SocketCommand command)
        : ComponentRequest(command, SocketRequestType::COMPONENT_SCALE) {}

    double scale = 0.0;
};

struct TargetComponentRequest : ComponentRequest {
    explicit TargetComponentRequest(SocketCommand command)
        : ComponentRequest(command, SocketRequestType::COMPONENT_TARGET) {}

        On targetOn;
};

struct DriverDelayRequest : SocketRequestBase {
    explicit DriverDelayRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_DELAY) {}

    int duration = 0;
};

struct DriverKeyRequest : SocketRequestBase {
    explicit DriverKeyRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_KEY) {}

    int keyCode = -1;
};

struct DriverCombineKeyRequest : SocketRequestBase {
    explicit DriverCombineKeyRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_COMBINE_KEY) {}

    int key0 = -1;
    int key1 = -1;
    int key2 = -1;
};

struct DriverPointRequest : SocketRequestBase {
    explicit DriverPointRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_POINT) {}

    int x = 0;
    int y = 0;
};

struct DriverSwipeRequest : SocketRequestBase {
    explicit DriverSwipeRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_SWIPE) {}

    int startX = 0;
    int startY = 0;
    int endX = 0;
    int endY = 0;
    int speed = 0;
};

struct DriverDirectionFlingRequest : SocketRequestBase {
    explicit DriverDirectionFlingRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_FLING_DIRECTION) {}

    UiDirection direction = UiDirection::DOWN;
    int speed = 0;
};

struct DriverPointFlingRequest : SocketRequestBase {
    explicit DriverPointFlingRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_FLING_POINT) {}

    Point from;
    Point to;
    int stepLen = 0;
    int speed = 0;
};

struct DriverDragRequest : SocketRequestBase {
    explicit DriverDragRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_DRAG) {}

    int startX = 0;
    int startY = 0;
    int endX = 0;
    int endY = 0;
    int speed = 0;
};

struct DriverDisplaySizeRequest : SocketRequestBase {
    explicit DriverDisplaySizeRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_DISPLAY_SIZE) {}

    int displayId = -1;
};

struct DriverDisplayRotationRequest : SocketRequestBase {
    explicit DriverDisplayRotationRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_DISPLAY_ROTATION) {}

    DisplayRotation rotation = DisplayRotation::ROTATION_0;
};

struct DriverOnRequest : SocketRequestBase {
    explicit DriverOnRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_ON) {}

    On on;
};

struct DriverPointerMatrixRequest : SocketRequestBase {
    explicit DriverPointerMatrixRequest(SocketCommand command)
        : SocketRequestBase(command, SocketRequestType::DRIVER_POINTER_MATRIX) {}

    std::shared_ptr<PointerMatrix> pointers = std::make_shared<PointerMatrix>();
    int speed = 0;
};

using SocketRequestPtr = std::unique_ptr<SocketRequestBase>;
using DecodeFunc = SocketRequestPtr (*)(SocketCommand, const Json::Value&, const Json::Value&);
using HandleFunc = bool (*)(int, const SocketRequestBase&);

struct SocketHandlerEntry {
    DecodeFunc decode = nullptr;
    HandleFunc handle = nullptr;
};

template<typename T>
const T* CastSocketRequest(const SocketRequestBase& request, SocketRequestType expectedType)
{
    if (request.requestType != expectedType) {
        return nullptr;
    }
    return static_cast<const T*>(&request);
}
} // namespace OHOS::UiTest
#endif // UITEST_SOCKET_REQUEST_H
