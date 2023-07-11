/*
 * Copyright (c) 2023 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef DRIVER_NAPI_LIBN_H
#define DRIVER_NAPI_LIBN_H

#include <string>
#include "napi_libn_fwk.h"
#include "utils/log.h"

namespace OHOS::UiTest {

enum OnType : int32_t {
    CLICKABLE = 1,
    LONGCLICKABLE,
    SCROLLABLE,
    ENABLED,
    FOCUSED,
    SELECTED,
    CHECKED,
    CHECKABLE
};

class OnNExporter : public LibN::NExporter {
public:
    OnNExporter(napi_env env, napi_value exports);
    ~OnNExporter() override;

    bool Export() override;
    std::string GetClassName() override;
    static napi_value Text(napi_env env, napi_callback_info info);
    static napi_value Id(napi_env env, napi_callback_info info);
    static napi_value Type(napi_env env, napi_callback_info info);
    static napi_value Clickable(napi_env env, napi_callback_info info);
    static napi_value LongClickable(napi_env env, napi_callback_info info);
    static napi_value Scrollable(napi_env env, napi_callback_info info);
    static napi_value Enabled(napi_env env, napi_callback_info info);
    static napi_value Focused(napi_env env, napi_callback_info info);
    static napi_value Selected(napi_env env, napi_callback_info info);
    static napi_value Checked(napi_env env, napi_callback_info info);
    static napi_value Checkable(napi_env env, napi_callback_info info);

    static constexpr const char *ON_CLASS_NAME_ = "ON";
    static constexpr const char *ON_CLASS_NAME = "On";
    static constexpr const char *FUNCTION_TEXT = "text";
    static constexpr const char *FUNCTION_ID = "id";
    static constexpr const char *FUNCTION_TYPE = "type";
    static constexpr const char *FUNCTION_CLICKABLE = "clickable";
    static constexpr const char *FUNCTION_LONG_CLICKABLE = "longClickable";
    static constexpr const char *FUNCTION_SCROLLABLE = "scrollable";
    static constexpr const char *FUNCTION_ENABLED = "enabled";
    static constexpr const char *FUNCTION_FOCUSED = "focused";
    static constexpr const char *FUNCTION_SELECTED = "selected";
    static constexpr const char *FUNCTION_CHECKED = "checked";
    static constexpr const char *FUNCTION_CHECKABLE = "checkable";
    static constexpr const char *FUNCTION_IS_BEFORE = "isBefore";
    static constexpr const char *FUNCTION_IS_AFTER = "isAfter";
};

class ComponentNExporter : public LibN::NExporter {
public:
    ComponentNExporter(napi_env env, napi_value exports);
    ~ComponentNExporter() override;

    bool Export() override;
    std::string GetClassName() override;
    static napi_value Click(napi_env env, napi_callback_info info);
    static napi_value DoubleClick(napi_env env, napi_callback_info info);
    static napi_value LongClick(napi_env env, napi_callback_info info);
    static napi_value GetId(napi_env env, napi_callback_info info);
    static napi_value GetText(napi_env env, napi_callback_info info);
    static napi_value GetType(napi_env env, napi_callback_info info);
    static napi_value IsClickable(napi_env env, napi_callback_info info);
    static napi_value IsLongClickable(napi_env env, napi_callback_info info);
    static napi_value IsScrollable(napi_env env, napi_callback_info info);
    static napi_value IsEnabled(napi_env env, napi_callback_info info);
    static napi_value IsFocused(napi_env env, napi_callback_info info);
    static napi_value IsSelected(napi_env env, napi_callback_info info);
    static napi_value IsChecked(napi_env env, napi_callback_info info);
    static napi_value IsCheckable(napi_env env, napi_callback_info info);
    static napi_value InputText(napi_env env, napi_callback_info info);
    static napi_value ClearText(napi_env env, napi_callback_info info);
    static napi_value ScrollToTop(napi_env env, napi_callback_info info);
    static napi_value ScrollToBottom(napi_env env, napi_callback_info info);
    static napi_value ScrollSearch(napi_env env, napi_callback_info info);
    static napi_value GetBoundsCenter(napi_env env, napi_callback_info info);

    static constexpr const char *COMPONENT_CLASS_NAME = "Component";
    static constexpr const char *FUNCTION_CLICK = "click";
    static constexpr const char *FUNCTION_DOUBLE_CLICK = "doubleClick";
    static constexpr const char *FUNCTION_LONG_CLICK = "longClick";
    static constexpr const char *FUNCTION_GET_ID = "getId";
    static constexpr const char *FUNCTION_GET_TEXT = "getText";
    static constexpr const char *FUNCTION_GET_TYPE = "getType";
    static constexpr const char *FUNCTION_IS_CLICKABLE = "isClickable";
    static constexpr const char *FUNCTION_IS_LONG_CLICKABLE = "isLongClickable";
    static constexpr const char *FUNCTION_IS_SCROLLABLE = "isScrollable";
    static constexpr const char *FUNCTION_IS_ENABLED = "isEnabled";
    static constexpr const char *FUNCTION_IS_FOCUSED = "isFocused";
    static constexpr const char *FUNCTION_IS_SELECTED = "isSelected";
    static constexpr const char *FUNCTION_IS_CHECKED = "isChecked";
    static constexpr const char *FUNCTION_IS_CHECKABLE = "isCheckable";
    static constexpr const char *FUNCTION_INPUT_TEXT = "inputText";
    static constexpr const char *FUNCTION_CLEAR_TEXT = "clearText";
    static constexpr const char *FUNCTION_SCROLL_TO_TOP = "scrollToTop";
    static constexpr const char *FUNCTION_SCROLL_TO_BOTTOM = "scrollToBottom";
    static constexpr const char *FUNCTION_SCROLL_SEARCH = "scrollSearch";
    static constexpr const char *FUNCTION_GET_BOUNDS = "getBounds";
    static constexpr const char *FUNCTION_GET_BOUNDS_CENTER = "getBoundsCenter";
    static constexpr const char *FUNCTION_DRAG_TO = "dragTo";
    static constexpr const char *FUNCTION_PINCH_OUT = "pinchOut";
    static constexpr const char *FUNCTION_PINCH_IN = "pinchIn";
};

class DriverNExporter final : public LibN::NExporter {
public:
    DriverNExporter(napi_env env, napi_value exports);
    ~DriverNExporter() override;

    bool Export() override;
    std::string GetClassName() override;

    static napi_value CreateDriver(napi_env env, napi_callback_info info);
    static napi_value DelayMs(napi_env env, napi_callback_info info);
    static napi_value PressBack(napi_env env, napi_callback_info info);
    static napi_value AssertComponentExist(napi_env env, napi_callback_info info);
    static napi_value FindComponent(napi_env env, napi_callback_info info);
    static napi_value FindComponents(napi_env env, napi_callback_info info);
    static napi_value Click(napi_env env, napi_callback_info info);
    static napi_value DoubleClick(napi_env env, napi_callback_info info);
    static napi_value LongClick(napi_env env, napi_callback_info info);
    static napi_value Swipe(napi_env env, napi_callback_info info);
    static napi_value Fling(napi_env env, napi_callback_info info);

    static constexpr const char *DRIVER_CLASS_NAME = "Driver";
    static constexpr const char *FUNCTION_CREATE = "create";
    static constexpr const char *FUNCTION_DELAY_MS = "delayMs";
    static constexpr const char *FUNCTION_PRESS_BACK = "pressBack";
    static constexpr const char *FUNCTION_ASSERT_COMPONENT = "assertComponentExist";
    static constexpr const char *FUNCTION_FIND_COMPONENT = "findComponent";
    static constexpr const char *FUNCTION_FIND_COMPONENTS = "findComponents";
    static constexpr const char *FUNCTION_CLICK = "click";
    static constexpr const char *FUNCTION_DOUBLE_CLICK = "doubleClick";
    static constexpr const char *FUNCTION_LONG_CLICK = "longClick";
    static constexpr const char *FUNCTION_SWIPE = "swipe";
    static constexpr const char *FUNCTION_FLING = "fling";
};

} // namespace OHOS::UiTest
#endif // DRIVER_NAPI_LIBN_H