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

#include "driver_napi_libn.h"

#include "../core/driver.h"

namespace OHOS::UiTest {

using namespace std;
using namespace LibN;
static napi_ref OnRef = nullptr;

class ArgsCls {
public:
    unique_ptr<Component> component = nullptr;
    vector<unique_ptr<Component>> components;
    unique_ptr<bool> isCommonBool;
};

OnNExporter::OnNExporter(napi_env env, napi_value exports) : NExporter(env, exports) {}

OnNExporter::~OnNExporter() {}

static napi_value Instantiate(napi_env env, napi_value thisVar)
{
    napi_value OnVal = nullptr;
    napi_get_reference_value(env, OnRef, &OnVal);
    bool result;
    napi_strict_equals(env, OnVal, thisVar, &result);
    if (result) {
        HILOG_INFO("Uitest:: On addr equals.");
        thisVar = NClass::InstantiateClass(env, OnNExporter::ON_CLASS_NAME, {});
    }
    return thisVar;
}

napi_value OnNExporter::Text(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Uitest::OnNExporter::Text begin.");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE, NARG_CNT::TWO)) {
        HILOG_ERROR("Uitest::OnNExporter::Text Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [succ, txt, ignore] = NVal(env, funcArg[NARG_POS::FIRST]).ToUTF8String();
    if (!succ) {
        HILOG_ERROR("Uitest::OnNExporter::Text Get txt parameter failed!");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    napi_value thisVar = Instantiate(env, funcArg.GetThisVar());
    auto on = NClass::GetEntityOf<On>(env, thisVar);
    if (on == nullptr) {
        HILOG_ERROR("Uitest::OnNExporter::Text Cannot get entity of on");
        return nullptr;
    }
    int32_t number_ = 0;
    if (funcArg.GetArgc() == NARG_CNT::TWO) {
        auto [succGetNum, number] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
        if (!succGetNum) {
            HILOG_ERROR("Uitest::OnNExporter::Text Get number parameter failed!");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        number_ = number;
    }
    on->Text(string(txt.get()), number_);
    HILOG_INFO("Uitest::OnNExporter::Text end.");
    return thisVar;
}

napi_value OnNExporter::Id(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Uitest:: OnNExporter Id begin.");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("Id Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [succ, id, ignore] = NVal(env, funcArg[NARG_POS::FIRST]).ToUTF8String();
    if (!succ) {
        HILOG_ERROR("Get id parameter failed!");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    napi_value thisVar = Instantiate(env, funcArg.GetThisVar());
    auto on = NClass::GetEntityOf<On>(env, thisVar);
    if (on == nullptr) {
        HILOG_ERROR("Cannot get entity of on");
        return nullptr;
    }
    on->Id(string(id.get()));
    HILOG_INFO("Uitest:: OnNExporter Id end.");
    return thisVar;
}

napi_value OnNExporter::Type(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Uitest:: OnNExporter Type begin.");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("Type Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [succ, type, ignore] = NVal(env, funcArg[NARG_POS::FIRST]).ToUTF8String();
    if (!succ) {
        HILOG_ERROR("Get type parameter failed!");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    napi_value thisVar = Instantiate(env, funcArg.GetThisVar());
    auto on = NClass::GetEntityOf<On>(env, thisVar);
    if (!on) {
        HILOG_ERROR("Cannot get entity of Type");
        return nullptr;
    }
    on->Type(string(type.get()));
    HILOG_INFO("Uitest:: OnNExporter Type end.");
    return thisVar;
}

static napi_value ExecImpl(napi_env env, napi_value thisVar, int32_t type, bool b)
{
    HILOG_INFO("Uitest:: ExecImpl begin.");
    thisVar = Instantiate(env, thisVar);
    auto on = NClass::GetEntityOf<On>(env, thisVar);
    if (on) {
        HILOG_INFO("Uitest:: ExecImpl type: %{public}d", type);
        switch (type) {
            case CommonType::CLICKABLE:
                on->Clickable(b);
                break;
            case CommonType::LONGCLICKABLE:
                on->LongClickable(b);
                break;
            case CommonType::SCROLLABLE:
                on->Scrollable(b);
                break;
            case CommonType::ENABLED:
                on->Enabled(b);
                break;
            case CommonType::FOCUSED:
                on->Focused(b);
                break;
            case CommonType::SELECTED:
                on->Selected(b);
                break;
            case CommonType::CHECKED:
                on->Checked(b);
                break;
            case CommonType::CHECKABLE:
                on->Checkable(b);
                break;
            default:
                HILOG_ERROR("Cannot read type of ExecImpl");
                break;
        }
    }
    HILOG_INFO("Uitest:: ExecImpl end.");
    return thisVar;
}

static napi_value OnTemplate(napi_env env, napi_callback_info info, int32_t type)
{
    HILOG_INFO("Uitest:: OnTemplate begin.");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO, NARG_CNT::ONE)) {
        HILOG_ERROR("Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    bool b_;
    switch (type) {
        case CommonType::CLICKABLE:
        case CommonType::LONGCLICKABLE:
        case CommonType::SCROLLABLE:
        case CommonType::ENABLED:
        case CommonType::FOCUSED:
        case CommonType::SELECTED:
            b_ = true;
            break;
        case CommonType::CHECKED:
        case CommonType::CHECKABLE:
            b_ = false;
            break;
    }
    if (funcArg.GetArgc() == NARG_CNT::ONE) {
        auto [succ, b] = NVal(env, funcArg[NARG_POS::FIRST]).ToBool();
        if (!succ) {
            HILOG_ERROR("get parameter failed!");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        b_ = b;
    }
    HILOG_INFO("Uitest:: OnTemplate end.");
    return ExecImpl(env, funcArg.GetThisVar(), type, b_);
}

napi_value OnNExporter::Clickable(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::CLICKABLE);
}

napi_value OnNExporter::LongClickable(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::LONGCLICKABLE);
}

napi_value OnNExporter::Scrollable(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::SCROLLABLE);
}

napi_value OnNExporter::Enabled(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::ENABLED);
}

napi_value OnNExporter::Focused(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::FOCUSED);
}

napi_value OnNExporter::Selected(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::SELECTED);
}

napi_value OnNExporter::Checked(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::CHECKED);
}

napi_value OnNExporter::Checkable(napi_env env, napi_callback_info info)
{
    return OnTemplate(env, info, CommonType::CHECKABLE);
}

static napi_value OnInitializer(napi_env env, napi_callback_info info)
{
    HILOG_INFO("OnInitializer begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("On Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto on_ = make_unique<On>();
    if (!NClass::SetEntityFor<On>(env, funcArg.GetThisVar(), move(on_))) {
        HILOG_ERROR("Failed to set On entity");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    HILOG_INFO("OnInitializer end");
    return funcArg.GetThisVar();
}

bool OnNExporter::Export()
{
    HILOG_INFO("Uitest::OnNExporter Export begin");
    vector<napi_property_descriptor> props = {
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_TEXT, OnNExporter::Text),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_ID, OnNExporter::Id),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_TYPE, OnNExporter::Type),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_CLICKABLE, OnNExporter::Clickable),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_LONG_CLICKABLE, OnNExporter::LongClickable),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_SCROLLABLE, OnNExporter::Scrollable),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_ENABLED, OnNExporter::Enabled),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_FOCUSED, OnNExporter::Focused),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_SELECTED, OnNExporter::Selected),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_CHECKED, OnNExporter::Checked),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_CHECKABLE, OnNExporter::Checkable),
    };
    auto [succ, classValue] = NClass::DefineClass(exports_.env_, OnNExporter::ON_CLASS_NAME, OnInitializer,
        std::move(props));
    if (!succ) {
        HILOG_ERROR("Failed to define OnNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }
    succ = NClass::SaveClass(exports_.env_, OnNExporter::ON_CLASS_NAME, classValue);
    if (!succ) {
        HILOG_ERROR("Failed to save OnNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }
    exports_.AddProp(OnNExporter::ON_CLASS_NAME, classValue);
    napi_value On = NClass::InstantiateClass(exports_.env_, OnNExporter::ON_CLASS_NAME, {});
    if (!On) {
        HILOG_ERROR("Failed to instantiate ON class");
        return false;
    }
    napi_create_reference(exports_.env_, On, 1, &OnRef);
    HILOG_INFO("Uitest::OnNExporter Export end");
    return exports_.AddProp(OnNExporter::ON_CLASS_NAME_, On);
}

string OnNExporter::GetClassName()
{
    return OnNExporter::ON_CLASS_NAME;
}

ComponentNExporter::ComponentNExporter(napi_env env, napi_value exports) : NExporter(env, exports) {}

ComponentNExporter::~ComponentNExporter() {}

static napi_value ComponentInitializer(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Component Initializer begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("Component Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    HILOG_INFO("Component Initializer end");
    return funcArg.GetThisVar();
}

napi_value ComponentNExporter::Click(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Click begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("Click Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component]() -> NError {
        component->Click();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Click";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::DoubleClick(napi_env env, napi_callback_info info)
{
    HILOG_INFO("DoubleClick begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("DoubleClick Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component]() -> NError {
        component->DoubleClick();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "DoubleClick";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::LongClick(napi_env env, napi_callback_info info)
{
    HILOG_INFO("LongClick begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("LongClick Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component]() -> NError {
        component->LongClick();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "LongClick";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::GetId(napi_env env, napi_callback_info info)
{
    HILOG_INFO("GetId begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("GetId Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    string id = "";
    auto cbExec = [&id, component]() -> NError {
        id = component->GetId();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [&id](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUTF8String(env, id);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "GetId";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::GetText(napi_env env, napi_callback_info info)
{
    HILOG_INFO("GetText begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("GetText Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    string text = "";
    auto cbExec = [&text, component]() -> NError {
        text = component->GetText();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [&text](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUTF8String(env, text);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "GetText";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::GetType(napi_env env, napi_callback_info info)
{
    HILOG_INFO("GetType begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("GetType Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    string type;
    auto cbExec = [&type, component]() -> NError {
        type = component->GetType();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [&type](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUTF8String(env, type);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "GetType";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

static string ProcedureName(int32_t type)
{
    HILOG_INFO("ProcedureName begin");
    switch (type) {
        HILOG_INFO("ProcedureName type: %{public}d", type);
        case CommonType::CLICKABLE:
            return "IsClickable";
        case CommonType::LONGCLICKABLE:
            return "IsLongClickable";
        case CommonType::SCROLLABLE:
            return "IsScrollable";
        case CommonType::ENABLED:
            return "IsEnabled";
        case CommonType::FOCUSED:
            return "IsFocused";
        case CommonType::SELECTED:
            return "IsSelected";
        case CommonType::CHECKED:
            return "IsChecked";
        case CommonType::CHECKABLE:
            return "IsCheckable";
    }
    HILOG_INFO("ProcedureName end");
}

static void ComponentImpl(shared_ptr<ArgsCls> args, Component* component, int32_t type)
{
    HILOG_INFO("ComponentImpl begin");
    switch (type) {
        HILOG_INFO("ComponentImpl type: %{public}d", type);
        case CommonType::CLICKABLE:
            args->isCommonBool = move(component->IsClickable());
            break;
        case CommonType::LONGCLICKABLE:
            args->isCommonBool = move(component->IsLongClickable());
            break;
        case CommonType::SCROLLABLE:
            args->isCommonBool = move(component->IsScrollable());
            break;
        case CommonType::ENABLED:
            args->isCommonBool = move(component->IsEnabled());
            break;
        case CommonType::FOCUSED:
            args->isCommonBool = move(component->IsFocused());
            break;
        case CommonType::SELECTED:
            args->isCommonBool = move(component->IsSelected());
            break;
        case CommonType::CHECKED:
            args->isCommonBool = move(component->IsChecked());
            break;
        case CommonType::CHECKABLE:
            args->isCommonBool = move(component->IsCheckable());
            break;
        default:
            HILOG_ERROR("Cannot read type of ComponentImpl");
            break;
    }
    HILOG_INFO("ComponentImpl end");
}

static napi_value ComponentTemplate(napi_env env, napi_callback_info info, int32_t type)
{
    HILOG_INFO("ComponentTemplate begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("ComponentTemplate Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto args = std::make_shared<ArgsCls>();
    auto cbExec = [args, component, tp = type]() -> NError {
        ComponentImpl(args, component, tp);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [args](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateBool(env, *(args->isCommonBool));
    };

    NVal thisVar(env, funcArg.GetThisVar());
    HILOG_INFO("ComponentTemplate end");
    return NAsyncWorkPromise(env, thisVar).Schedule(ProcedureName(type), cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::IsClickable(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::CLICKABLE);
}

napi_value ComponentNExporter::IsLongClickable(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::LONGCLICKABLE);
}

napi_value ComponentNExporter::IsScrollable(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::SCROLLABLE);
}

napi_value ComponentNExporter::IsEnabled(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::ENABLED);
}

napi_value ComponentNExporter::IsFocused(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::FOCUSED);
}

napi_value ComponentNExporter::IsSelected(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::SELECTED);
}

napi_value ComponentNExporter::IsChecked(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::CHECKED);
}

napi_value ComponentNExporter::IsCheckable(napi_env env, napi_callback_info info)
{
    return ComponentTemplate(env, info, CommonType::CHECKABLE);
}

napi_value ComponentNExporter::InputText(napi_env env, napi_callback_info info)
{
    HILOG_INFO("InputText begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("InputText Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto [succ, text, ignore] = NVal(env, funcArg[NARG_POS::FIRST]).ToUTF8String();
    if (!succ) {
        HILOG_ERROR("InputText get text parameter failed!");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component, text = string(text.get())]() -> NError {
        component->InputText(text);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "InputText";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::ClearText(napi_env env, napi_callback_info info)
{
    HILOG_INFO("ClearText begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("ClearText Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component]() -> NError {
        component->ClearText();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "ClearText";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::ScrollToTop(napi_env env, napi_callback_info info)
{
    HILOG_INFO("ScrollToTop begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO, NARG_CNT::ONE)) {
        HILOG_ERROR("ScrollToTop Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    int32_t speed_ = 0;
    if (funcArg.GetArgc() == NARG_CNT::ONE) {
        auto [succ, speed] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
        if (!succ) {
            HILOG_ERROR("Get scrollToBottom parameter failed!");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        speed_ = speed;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component, speed_]() -> NError {
        component->ScrollToTop(speed_);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "ScrollToTop";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::ScrollToBottom(napi_env env, napi_callback_info info)
{
    HILOG_INFO("ScrollToBottom begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO, NARG_CNT::ONE)) {
        HILOG_ERROR("ScrollToBottom Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    int32_t speed_ = 0;
    if (funcArg.GetArgc() == NARG_CNT::ONE) {
        auto [succ, speed] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
        if (!succ) {
            HILOG_ERROR("Get scrollToBottom parameter failed!");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        speed_ = speed;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [component, speed_]() -> NError {
        component->ScrollToBottom(speed_);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "ScrollToBottom";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::ScrollSearch(napi_env env, napi_callback_info info)
{
    HILOG_INFO("ScrollSearch begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("ScrollSearch Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    auto on = NClass::GetEntityOf<On>(env, NVal(env, funcArg[NARG_POS::FIRST]).val_);
    if (!on) {
        HILOG_ERROR("Cannot get entity of on");
        return nullptr;
    }

    napi_value jsComponent = NClass::InstantiateClass(env, ComponentNExporter::COMPONENT_CLASS_NAME, {});
    if (!jsComponent) {
        HILOG_ERROR("Failed to instantiate jsComponent class");
        return nullptr;
    }
    napi_ref ref = nullptr;
    napi_create_reference(env, jsComponent, 1, &ref);

    auto arg = make_shared<ArgsCls>();
    auto cbExec = [component, on, arg]() -> NError {
        arg->component = move(component->ScrollSearch(*on));
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [ref, arg](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        napi_value jsComponent_ = nullptr;
        napi_get_reference_value(env, ref, &jsComponent_);
        if (!arg->component) {
            HILOG_ERROR("Failed to component is nullptr.");
            NError(E_AWAIT).ThrowErr(env);
            return NVal::CreateUndefined(env);
        }
        if (!NClass::SetEntityFor<Component>(env, jsComponent_, move(arg->component))) {
            NError(E_ASSERTFAILD).ThrowErr(env);
        }
        HILOG_INFO("ScrollSearch Success!");
        return NVal(env, jsComponent_);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "ScrollSearch";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::GetBoundsCenter(napi_env env, napi_callback_info info)
{
    HILOG_INFO("GetBoundsCenter begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("GetBoundsCenter Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    Point point;
    auto cbExec = [&point, component]() -> NError {
        point = component->GetBoundsCenter();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [&point](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        NVal obj = NVal::CreateObject(env);
        obj.AddProp("x", NVal::CreateInt32(env, point.x).val_);
        obj.AddProp("y", NVal::CreateInt32(env, point.y).val_);
        return { obj };
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "GetBoundsCenter";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

bool ComponentNExporter::Export()
{
    HILOG_INFO("Uitest::ComponentNExporter Export begin");
    vector<napi_property_descriptor> props = {
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_CLICK, ComponentNExporter::Click),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_DOUBLE_CLICK, ComponentNExporter::DoubleClick),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_LONG_CLICK, ComponentNExporter::LongClick),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_GET_ID, ComponentNExporter::GetId),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_GET_TEXT, ComponentNExporter::GetText),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_GET_TYPE, ComponentNExporter::GetType),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_CLICKABLE, ComponentNExporter::IsClickable),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_LONG_CLICKABLE, ComponentNExporter::IsLongClickable),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_SCROLLABLE, ComponentNExporter::IsScrollable),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_ENABLED, ComponentNExporter::IsEnabled),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_FOCUSED, ComponentNExporter::IsFocused),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_SELECTED, ComponentNExporter::IsSelected),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_CHECKED, ComponentNExporter::IsChecked),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_IS_CHECKABLE, ComponentNExporter::IsCheckable),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_INPUT_TEXT, ComponentNExporter::InputText),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_CLEAR_TEXT, ComponentNExporter::ClearText),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_SCROLL_TO_TOP, ComponentNExporter::ScrollToTop),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_SCROLL_TO_BOTTOM, ComponentNExporter::ScrollToBottom),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_SCROLL_SEARCH, ComponentNExporter::ScrollSearch),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_GET_BOUNDS_CENTER, ComponentNExporter::GetBoundsCenter),
    };
    auto [succ, classValue] = NClass::DefineClass(exports_.env_, ComponentNExporter::COMPONENT_CLASS_NAME,
        ComponentInitializer, std::move(props));
    if (!succ) {
        HILOG_ERROR("Failed to define ComponentNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }
    succ = NClass::SaveClass(exports_.env_, ComponentNExporter::COMPONENT_CLASS_NAME, classValue);
    if (!succ) {
        HILOG_ERROR("Failed to save ComponentNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }

    HILOG_INFO("Uitest::ComponentNExporter Export end");
    return exports_.AddProp(ComponentNExporter::COMPONENT_CLASS_NAME, classValue);
}

string ComponentNExporter::GetClassName()
{
    return ComponentNExporter::COMPONENT_CLASS_NAME;
}

DriverNExporter::DriverNExporter(napi_env env, napi_value exports) : NExporter(env, exports) {}

DriverNExporter::~DriverNExporter() {}

napi_value DriverNExporter::CreateDriver(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Uitest::CreateDriver begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("Start Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    napi_value thisVar = NClass::InstantiateClass(env, DriverNExporter::DRIVER_CLASS_NAME, {});
    if (thisVar == nullptr) {
        return NVal::CreateUndefined(env).val_;
    }

    HILOG_INFO("Uitest::CreateDriver end");
    return thisVar;
}

napi_value DriverNExporter::DelayMs(napi_env env, napi_callback_info info)
{
    HILOG_INFO("DelayMs begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("DelayMs Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, duration] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid duration");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [env = env, driver, dur = duration]() -> NError {
        driver->DelayMs(dur);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_ERROR("DelayMs Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "DelayMs";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::PressBack(napi_env env, napi_callback_info info)
{
    HILOG_INFO("PressBack begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("PressBack Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto cbExec = [env = env, driver]() -> NError {
        driver->PressBack();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_ERROR("PressBack Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "PressBack";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::AssertComponentExist(napi_env env, napi_callback_info info)
{
    HILOG_INFO("AssertComponentExist begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("AssertComponentExist Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    NVal valOn(env, funcArg[NARG_POS::FIRST]);
    if (!valOn.TypeIs(napi_object)) {
        HILOG_ERROR("Invalid valOn");
    }
    auto on = NClass::GetEntityOf<On>(env, valOn.val_);

    auto cbExec = [env = env, driver, on]() -> NError {
        driver->AssertComponentExist(*on);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_ERROR("AssertComponentExist Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "AssertComponentExist";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

static bool GetArg(napi_env env, napi_value thisValue, int number, ArgsInfo &argsInfo)
{
    auto [success, number_] = NVal(env, thisValue).ToInt32();
    if(!success){
        return false;
    }
    switch (number) {
        case NARG_POS::FIRST:
            argsInfo.startx = number_;
            break;
        case NARG_POS::SECOND:
            argsInfo.starty = number_;
            break;
        case NARG_POS::THIRD:
            argsInfo.endx = number_;
            break;
        case NARG_POS::FOURTH:
            argsInfo.endy = number_;
            break;
        case NARG_POS::FIFTH:
            argsInfo.speed = number_;
            break;
    }
    return true;
}

static bool GetArgs(napi_env env, NFuncArg &funcArg, ArgsInfo &argsInfo)
{
    bool retFirst, retSecond, retThird, retFourth;
    bool retFifth = true;
    retFirst = GetArg(env, funcArg[NARG_POS::FIRST], NARG_POS::FIRST, argsInfo);
    retSecond = GetArg(env, funcArg[NARG_POS::SECOND], NARG_POS::SECOND, argsInfo);
    retThird = GetArg(env, funcArg[NARG_POS::THIRD], NARG_POS::THIRD, argsInfo);
    retFourth = GetArg(env, funcArg[NARG_POS::FOURTH], NARG_POS::FOURTH, argsInfo);

    if (funcArg.GetArgc() == NARG_CNT::FIVE) {
        retFifth = GetArg(env, funcArg[NARG_POS::FIFTH], NARG_POS::FIFTH, argsInfo);
    }
    return retFirst && retSecond && retThird && retFourth && retFifth;
}

napi_value DriverNExporter::Swipe(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Swipe begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::FOUR, NARG_CNT::FIVE)) {
        HILOG_ERROR("Swipe Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    ArgsInfo argsInfo;
    if (!GetArgs(env, funcArg, argsInfo)) {
        HILOG_ERROR("Swipe Invalid arguments");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [env = env, driver, &argsInfo]() -> NError {
        driver->Swipe(argsInfo.startx, argsInfo.starty, argsInfo.endx, argsInfo.endy, argsInfo.speed);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_INFO("Swipe Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Swipe";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::Fling(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Fling begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("Fling Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    NVal objFrom(env, funcArg[NARG_POS::FIRST]);
    if (!objFrom.TypeIs(napi_object)) {
        HILOG_ERROR("Invalid objFrom");
    }
    auto ptFrom = NClass::GetEntityOf<Point>(env, objFrom.val_);

    NVal objTo(env, funcArg[NARG_POS::SECOND]);
    if (!objTo.TypeIs(napi_object)) {
        HILOG_ERROR("Invalid objTo");
    }
    auto ptTo = NClass::GetEntityOf<Point>(env, objTo.val_);

    auto [resGetFirstArg, stepLen] = NVal(env, funcArg[NARG_POS::THIRD]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid x");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, speed] = NVal(env, funcArg[NARG_POS::FOURTH]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("Invalid y");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [env = env, driver, ptFrom = ptFrom, ptTo = ptTo, stepLen = stepLen, speed = speed]() -> NError {
        driver->Fling(*ptFrom, *ptTo, stepLen, speed);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_ERROR("Fling Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Fling";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::Click(napi_env env, napi_callback_info info)
{
    HILOG_INFO("Click begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("Click Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, x] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid x");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, y] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("Invalid y");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [driver, x = x, y = y]() -> NError {
        driver->Click(x, y);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_INFO("Click Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Click";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::DoubleClick(napi_env env, napi_callback_info info)
{
    HILOG_ERROR("DoubleClick begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("DoubleClick Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, x] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid x");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, y] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("Invalid y");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [driver, x = x, y = y]() -> NError {
        driver->DoubleClick(x, y);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_INFO("DoubleClick Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "DoubleClick";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::LongClick(napi_env env, napi_callback_info info)
{
    HILOG_INFO("LongClick begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("LongClick Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, x] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid x");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, y] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("Invalid y");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [driver, x = x, y = y]() -> NError {
        driver->LongClick(x, y);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_INFO("LongClick Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "LongClick";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::FindComponent(napi_env env, napi_callback_info info)
{
    HILOG_INFO("FindComponent begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("FindComponent Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto on = NClass::GetEntityOf<On>(env, NVal(env, funcArg[NARG_POS::FIRST]).val_);
    if (!on) {
        HILOG_ERROR("Cannot get entity of on");
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    napi_value jsComponent = NClass::InstantiateClass(env, ComponentNExporter::COMPONENT_CLASS_NAME, {});
    if (!jsComponent) {
        HILOG_ERROR("Failed to instantiate jsComponent class");
        return nullptr;
    }

    napi_ref ref = nullptr;
    napi_create_reference(env, jsComponent, 1, &ref);
    auto arg = make_shared<ArgsCls>();
    auto cbExec = [driver, on, arg]() -> NError {
        arg->component = move(driver->FindComponent(*on));
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [ref, arg](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        napi_value jsComponent_ = nullptr;
        napi_get_reference_value(env, ref, &jsComponent_);
        if (!arg->component) {
            HILOG_ERROR("Failed to component is nullptr.");
            NError(E_AWAIT).ThrowErr(env);
            return NVal::CreateUndefined(env);
        }
        if (!NClass::SetEntityFor<Component>(env, jsComponent_, move(arg->component))) {
            NError(E_ASSERTFAILD).ThrowErr(env);
        }
        HILOG_INFO("FindComponent Success!");
        return NVal(env, jsComponent_);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "FindComponent";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::FindComponents(napi_env env, napi_callback_info info)
{
    HILOG_INFO("FindComponents begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("FindComponents Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto on = NClass::GetEntityOf<On>(env, NVal(env, funcArg[NARG_POS::FIRST]).val_);
    if (!on) {
        HILOG_ERROR("Cannot get entity of on");
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }
    auto args = make_shared<ArgsCls>();
    if (!args) {
        HILOG_ERROR("Failed to request heap memory.");
        NError(ENOMEM).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [driver, on, args, env]() -> NError {
        args->components = move(driver->FindComponents(*on));
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [args](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_INFO("FindComponents Success!");
        return NVal::CreateArray(env, move(args->components), ComponentNExporter::COMPONENT_CLASS_NAME);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "FindComponents";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

static napi_value DriverInitializer(napi_env env, napi_callback_info info)
{
    HILOG_INFO("DriverInitializer begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("driver Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    auto driver = make_unique<Driver>();
    if (!NClass::SetEntityFor<Driver>(env, funcArg.GetThisVar(), move(driver))) {
        HILOG_ERROR("Failed to set driver entity");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    HILOG_INFO("DriverInitializer end");
    return funcArg.GetThisVar();
}

bool DriverNExporter::Export()
{
    HILOG_INFO("Uitest::DriverNExporter Export begin");
    vector<napi_property_descriptor> props = {
        NVal::DeclareNapiStaticFunction(DriverNExporter::FUNCTION_CREATE, DriverNExporter::CreateDriver),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_CREATE, DriverNExporter::CreateDriver),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_DELAY_MS, DriverNExporter::DelayMs),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_PRESS_BACK, DriverNExporter::PressBack),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_ASSERT_COMPONENT, DriverNExporter::AssertComponentExist),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_FIND_COMPONENT, DriverNExporter::FindComponent),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_FIND_COMPONENTS, DriverNExporter::FindComponents),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_CLICK, DriverNExporter::Click),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_DOUBLE_CLICK, DriverNExporter::DoubleClick),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_LONG_CLICK, DriverNExporter::LongClick),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_SWIPE, DriverNExporter::Swipe),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_FLING, DriverNExporter::Fling),
    };
    auto [succ, classValue] = NClass::DefineClass(exports_.env_, DriverNExporter::DRIVER_CLASS_NAME, DriverInitializer,
        std::move(props));
    if (!succ) {
        HILOG_ERROR("Failed to define DriverNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }
    succ = NClass::SaveClass(exports_.env_, DriverNExporter::DRIVER_CLASS_NAME, classValue);
    if (!succ) {
        HILOG_ERROR("Failed to save DriverNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }

    HILOG_INFO("Uitest::DriverNExporter Export end");
    return exports_.AddProp(DriverNExporter::DRIVER_CLASS_NAME, classValue);
}

string DriverNExporter::GetClassName()
{
    return DriverNExporter::DRIVER_CLASS_NAME;
}
} // namespace OHOS::UiTest
