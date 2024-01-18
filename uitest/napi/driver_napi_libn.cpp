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
static napi_ref PmRef = nullptr;
static constexpr const int32_t MAX_FINGERS = 10;
static constexpr const int32_t MAX_STEPS = 1000;

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
        HILOG_DEBUG("Uitest:: On addr equals.");
        thisVar = NClass::InstantiateClass(env, OnNExporter::ON_CLASS_NAME, {});
    }
    return thisVar;
}

napi_value OnNExporter::Text(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Uitest::OnNExporter::Text begin.");
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
    MatchPattern pattern = MatchPattern::EQUALS;
    if (funcArg.GetArgc() == NARG_CNT::TWO) {
        auto [succGetNum, number] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
        if (!succGetNum) {
            HILOG_ERROR("Uitest::OnNExporter::Text Get number parameter failed!");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        pattern = static_cast<MatchPattern>(number);
    }
    on->Text(string(txt.get()), pattern);
    HILOG_DEBUG("Uitest::OnNExporter::Text end.");
    return thisVar;
}

napi_value OnNExporter::Id(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Uitest:: OnNExporter Id begin.");
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
    HILOG_DEBUG("Uitest:: OnNExporter Id end.");
    return thisVar;
}

napi_value OnNExporter::Type(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Uitest:: OnNExporter Type begin.");
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
    HILOG_DEBUG("Uitest:: OnNExporter Type end.");
    return thisVar;
}

static napi_value ExecImpl(napi_env env, napi_value thisVar, int32_t type, bool b)
{
    HILOG_DEBUG("Uitest:: ExecImpl begin.");
    thisVar = Instantiate(env, thisVar);
    auto on = NClass::GetEntityOf<On>(env, thisVar);
    if (on) {
        HILOG_DEBUG("Uitest:: ExecImpl type: %{public}d", type);
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
    HILOG_DEBUG("Uitest:: ExecImpl end.");
    return thisVar;
}

static napi_value OnTemplate(napi_env env, napi_callback_info info, int32_t type)
{
    HILOG_DEBUG("Uitest:: OnTemplate begin.");
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
    HILOG_DEBUG("Uitest:: OnTemplate end.");
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

static napi_value RelativeOnTemplate(napi_env env, napi_callback_info info, int32_t type)
{
    HILOG_DEBUG("Uitest:: RelativeOnTemplate begin.");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("WithIn Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto relativeOn = NClass::GetEntityOf<On>(env, NVal(env, funcArg[NARG_POS::FIRST]).val_);
    if (!relativeOn) {
        HILOG_ERROR("Cannot get entity of parameterOn");
        return nullptr;
    }

    napi_value thisVar = Instantiate(env, funcArg.GetThisVar());
    auto on = NClass::GetEntityOf<On>(env, thisVar);
    if (on == nullptr) {
        HILOG_ERROR("Cannot get entity of on");
        return nullptr;
    }
    switch (type)
    {
    case CommonType::ISBEFORE:
        if (!on->IsBefore(relativeOn)) {
            HILOG_ERROR("Cannot put attributions to on");
            return nullptr;
        }
        break;
    case CommonType::ISAFTER:
        if (!on->IsAfter(relativeOn)) {
            HILOG_ERROR("Cannot put attributions to on");
            return nullptr;
        }
        break;
    case CommonType::WITHIN:
        if (!on->WithIn(relativeOn)) {
            HILOG_ERROR("Cannot put attributions to on");
            return nullptr;
        }
        break;
    default:
        HILOG_ERROR("Cannot read type of RelativeOn");
        break;
    }
    HILOG_DEBUG("Uitest:: RelativeOnTemplate end.");
    return thisVar;
}

napi_value OnNExporter::IsBefore(napi_env env, napi_callback_info info)
{
    return RelativeOnTemplate(env, info, CommonType::ISBEFORE);
}

napi_value OnNExporter::IsAfter(napi_env env, napi_callback_info info)
{
    return RelativeOnTemplate(env, info, CommonType::ISAFTER);
}

napi_value OnNExporter::WithIn(napi_env env, napi_callback_info info)
{
    return RelativeOnTemplate(env, info, CommonType::WITHIN);
}

static napi_value OnInitializer(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("OnInitializer begin");
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
    HILOG_DEBUG("OnInitializer end");
    return funcArg.GetThisVar();
}

bool OnNExporter::Export()
{
    HILOG_DEBUG("Uitest::OnNExporter Export begin");
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
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_ISBEFORE, OnNExporter::IsBefore),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_ISAFTER, OnNExporter::IsAfter),
        NVal::DeclareNapiFunction(OnNExporter::FUNCTION_WITHIN, OnNExporter::WithIn),
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
    HILOG_DEBUG("Uitest::OnNExporter Export end");
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
    HILOG_DEBUG("Component Initializer begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("Component Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    HILOG_DEBUG("Component Initializer end");
    return funcArg.GetThisVar();
}

napi_value ComponentNExporter::Click(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Click begin");
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
    HILOG_DEBUG("DoubleClick begin");
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
    HILOG_DEBUG("LongClick begin");
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
    HILOG_DEBUG("GetId begin");
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
    HILOG_DEBUG("GetText begin");
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

    static string text = "";
    auto cbExec = [component]() -> NError {
        text = component->GetText();
        HILOG_DEBUG("ComponentNExporter::GetText 1 %{public}s", text.c_str());
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_DEBUG("ComponentNExporter::GetText 2 %{public}s", text.c_str());
        NVal obj = NVal::CreateUTF8String(env, text);
        return { obj };
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "GetText";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::GetType(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("GetType begin");
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
    HILOG_DEBUG("ProcedureName begin");
    switch (type) {
        HILOG_DEBUG("ProcedureName type: %{public}d", type);
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
    HILOG_DEBUG("ProcedureName end");
}

static void ComponentImpl(shared_ptr<ArgsCls> args, Component* component, int32_t type)
{
    HILOG_DEBUG("ComponentImpl begin");
    switch (type) {
        HILOG_DEBUG("ComponentImpl type: %{public}d", type);
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
    HILOG_DEBUG("ComponentImpl end");
}

static napi_value ComponentTemplate(napi_env env, napi_callback_info info, int32_t type)
{
    HILOG_DEBUG("ComponentTemplate begin");
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
    HILOG_DEBUG("ComponentTemplate end");
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
    HILOG_DEBUG("InputText begin");
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
    HILOG_DEBUG("ClearText begin");
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
    HILOG_DEBUG("ScrollToTop begin");
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
    HILOG_DEBUG("ScrollToBottom begin");
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
    HILOG_DEBUG("ScrollSearch begin");
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
        if (!arg->component) {
            HILOG_ERROR("Failed to component is nullptr.");
            return NVal::CreateUndefined(env);
        }
        napi_value jsComponent_ = nullptr;
        napi_get_reference_value(env, ref, &jsComponent_);
        if (!NClass::SetEntityFor<Component>(env, jsComponent_, move(arg->component))) {
            HILOG_ERROR("Failed to set Component entity");
            return { env, NError(E_PARAMS).GetNapiErr(env) };
        }
        HILOG_DEBUG("ScrollSearch Success!");
        return NVal(env, jsComponent_);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "ScrollSearch";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::GetBoundsCenter(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("GetBoundsCenter begin");
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

napi_value ComponentNExporter::GetBounds(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("GetBounds begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("GetBounds Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }

    static Rect rect;
    auto cbExec = [component]() -> NError {
        rect = component->GetBounds();
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        NVal obj = NVal::CreateObject(env);
        obj.AddProp("left", NVal::CreateInt32(env, rect.left).val_);
        obj.AddProp("top", NVal::CreateInt32(env, rect.top).val_);
        obj.AddProp("right", NVal::CreateInt32(env, rect.right).val_);
        obj.AddProp("bottom", NVal::CreateInt32(env, rect.bottom).val_);
        HILOG_DEBUG("ComponentNExporter::GetBounds %{public}d, %{public}d, %{public}d, %{public}d",
            rect.left, rect.top, rect.right, rect.bottom);
        return { obj };
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "GetBounds";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::PinchOut(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("GetBounds PinchOut");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("GetBounds Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [succ, scale] = NVal(env, funcArg[NARG_POS::FIRST]).ToDouble();
    if (!succ) {
        HILOG_ERROR("Get PinchOut parameter failed!");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }
    float scale_ = scale;
    auto cbExec = [component, scale_]() -> NError {
        component->PinchOut(scale_);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "PinchOut";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value ComponentNExporter::PinchIn(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("GetBounds PinchIn");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("GetBounds Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [succ, scale] = NVal(env, funcArg[NARG_POS::FIRST]).ToDouble();
    if (!succ) {
        HILOG_ERROR("Get PinchIn parameter failed!");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto component = NClass::GetEntityOf<Component>(env, funcArg.GetThisVar());
    if (!component) {
        HILOG_ERROR("Cannot get entity of component");
        NError(E_DESTROYED).ThrowErr(env);
        return nullptr;
    }
    float scale_ = scale;
    auto cbExec = [component, scale_]() -> NError {
        component->PinchIn(scale_);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "PinchIn";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

bool ComponentNExporter::Export()
{
    HILOG_DEBUG("Uitest::ComponentNExporter Export begin");
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
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_GET_BOUNDS, ComponentNExporter::GetBounds),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_PINCH_OUT, ComponentNExporter::PinchOut),
        NVal::DeclareNapiFunction(ComponentNExporter::FUNCTION_PINCH_IN, ComponentNExporter::PinchIn),
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

    HILOG_DEBUG("Uitest::ComponentNExporter Export end");
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
    HILOG_DEBUG("Uitest::CreateDriver begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("CreateDriver Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    napi_value thisVar = NClass::InstantiateClass(env, DriverNExporter::DRIVER_CLASS_NAME, {});
    if (thisVar == nullptr) {
        HILOG_ERROR("CreateDriver failed to initialize.");
        NError(E_INITIALIZE).ThrowErr(env);
        return nullptr;
    }

    HILOG_DEBUG("Uitest::CreateDriver end");
    return thisVar;
}

napi_value DriverNExporter::DelayMs(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("DelayMs begin");
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
        HILOG_DEBUG("DelayMs Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "DelayMs";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::PressBack(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("PressBack begin");
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
        HILOG_DEBUG("PressBack Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "PressBack";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::AssertComponentExist(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("AssertComponentExist begin");
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
        bool ret = driver->AssertComponentExist(*on);
        if (!ret) {
            return NError(E_ASSERTFAILD);
        }
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_DEBUG("AssertComponentExist Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "AssertComponentExist";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

static bool GetArg(napi_env env, napi_value thisValue, int number, shared_ptr<ArgsInfo> argsInfo)
{
    auto [success, number_] = NVal(env, thisValue).ToInt32();
    if(!success){
        return false;
    }
    switch (number) {
        case NARG_POS::FIRST:
            argsInfo->startx = number_;
            break;
        case NARG_POS::SECOND:
            argsInfo->starty = number_;
            break;
        case NARG_POS::THIRD:
            argsInfo->endx = number_;
            break;
        case NARG_POS::FOURTH:
            argsInfo->endy = number_;
            break;
        case NARG_POS::FIFTH:
            argsInfo->speed = number_;
            break;
    }
    return true;
}

static bool GetArgs(napi_env env, NFuncArg &funcArg, shared_ptr<ArgsInfo> argsInfo)
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

napi_value DriverNExporter::InjectMultiPointerAction(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("DriverNExporter::InjectMultiPointerAction begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE, NARG_CNT::TWO)) {
        HILOG_ERROR("DriverNExporter::InjectMultiPointerAction Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }
    auto poMatrix = NClass::GetEntityOf<PointerMatrix>(env, NVal(env, funcArg[NARG_POS::FIRST]).val_);
    if (!poMatrix) {
        HILOG_ERROR("Cannot get entity of pointerMatrix");
        return nullptr;
    }

    int speed = -1;
    if (funcArg.GetArgc() == NARG_CNT::TWO) {
        auto [resGetSecondArg, number] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
        if (!resGetSecondArg) {
            HILOG_ERROR("Invalid speed");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        speed = number;
    }
    static bool ret = false;
    auto cbExec = [driver, poMatrix, sp = speed]() -> NError {
        ret = driver->InjectMultiPointerAction(*poMatrix, sp);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateBool(env, ret);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "InjectMultiPointerAction";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::TriggerCombineKeys(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("DriverNExporter::TriggerCombineKeys begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO, NARG_CNT::THREE)) {
        HILOG_ERROR("DriverNExporter::TriggerCombineKeys Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, key1] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid key1");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, key2] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("Invalid key2");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    int key3 = -1;
    if (funcArg.GetArgc() == NARG_CNT::THREE) {
        auto [resGetThirdArg, number] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
        if (!resGetThirdArg) {
            HILOG_ERROR("Invalid key3");
            NError(E_PARAMS).ThrowErr(env);
            return nullptr;
        }
        key3 = number;
    }

    auto cbExec = [driver, k1 = key1, k2 = key2, k3 = key3]() -> NError {
        driver->TriggerCombineKeys(k1, k2, k3);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "TriggerCombineKeys";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::TriggerKey(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("DriverNExporter::TriggerKey begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ONE)) {
        HILOG_ERROR("DriverNExporter::TriggerKey Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, keyCode] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid keyCode");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [driver, key = keyCode]() -> NError {
        driver->TriggerKey(key);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_DEBUG("TriggerKey Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "TriggerKey";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::Swipe(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Swipe begin");
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

    auto argsInfo = make_shared<ArgsInfo>();
    if (!GetArgs(env, funcArg, argsInfo)) {
        HILOG_ERROR("Swipe Invalid arguments");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [env = env, driver, argsInfo]() -> NError {
        driver->Swipe(argsInfo->startx, argsInfo->starty, argsInfo->endx, argsInfo->endy, argsInfo->speed);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_DEBUG("Swipe Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Swipe";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

static napi_value DirectFling(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Uitest:: DirectFling begin.");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    auto [resGetFirstArg, direct] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("Invalid duration");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, speed] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("Invalid speed");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto cbExec = [env = env, driver, dir = direct, sp = speed]() -> NError {
        UiDirection uiDir = static_cast<UiDirection>(dir);
        driver->Fling(uiDir, sp);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_DEBUG("Fling Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Fling";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::Fling(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Fling begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::FOUR) && !funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("Fling Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    if (funcArg.GetArgc() == NARG_CNT::TWO) {
        return DirectFling(env, info);
    }

    auto driver = NClass::GetEntityOf<Driver>(env, funcArg.GetThisVar());
    if (!driver) {
        HILOG_ERROR("Cannot get entity of driver");
        return nullptr;
    }

    NVal objFrom(env, funcArg[NARG_POS::FIRST]);
    if (!objFrom.TypeIs(napi_object)) {
        HILOG_ERROR("Invalid objFrom");
        return nullptr;
    }
    Point ptFrom = { std::get<1>(objFrom.GetProp("x").ToInt32()), std::get<1>(objFrom.GetProp("y").ToInt32()) };

    NVal objTo(env, funcArg[NARG_POS::SECOND]);
    if (!objTo.TypeIs(napi_object)) {
        HILOG_ERROR("Invalid objTo");
        return nullptr;
    }
    Point ptTo = { std::get<1>(objTo.GetProp("x").ToInt32()), std::get<1>(objTo.GetProp("y").ToInt32()) };

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
        driver->Fling(ptFrom, ptTo, stepLen, speed);
        return NError(ERRNO_NOERR);
    };

    auto cbCompl = [](napi_env env, NError err) -> NVal {
        if (err) {
            return { env, err.GetNapiErr(env) };
        }
        HILOG_DEBUG("Fling Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "Fling";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::Click(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("Click begin");
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
        HILOG_DEBUG("Click Success!");
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
        HILOG_DEBUG("DoubleClick Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "DoubleClick";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::LongClick(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("LongClick begin");
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
        HILOG_DEBUG("LongClick Success!");
        return NVal::CreateUndefined(env);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "LongClick";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::FindComponent(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("FindComponent begin");
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
        if (!arg->component) {
            HILOG_ERROR("Failed to component is nullptr.");
            return NVal::CreateUndefined(env);
        }
        napi_value jsComponent_ = nullptr;
        napi_get_reference_value(env, ref, &jsComponent_);
        if (!NClass::SetEntityFor<Component>(env, jsComponent_, move(arg->component))) {
            HILOG_ERROR("Failed to set Component entity");
            return { env, NError(E_PARAMS).GetNapiErr(env) };
        }
        HILOG_DEBUG("FindComponent Success!");
        return NVal(env, jsComponent_);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "FindComponent";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

napi_value DriverNExporter::FindComponents(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("FindComponents begin");
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
        if (args->components.size() == 0) {
            HILOG_DEBUG("FindComponents end,but null !");
            return NVal::CreateUndefined(env);
        }
        HILOG_DEBUG("FindComponents Success!");
        return NVal::CreateArray(env, move(args->components), ComponentNExporter::COMPONENT_CLASS_NAME);
    };

    NVal thisVar(env, funcArg.GetThisVar());
    string procedureName = "FindComponents";
    return NAsyncWorkPromise(env, thisVar).Schedule(procedureName, cbExec, cbCompl).val_;
}

static napi_value DriverInitializer(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("DriverInitializer begin");
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
    HILOG_DEBUG("DriverInitializer end");
    return funcArg.GetThisVar();
}

bool DriverNExporter::Export()
{
    HILOG_DEBUG("Uitest::DriverNExporter Export begin");
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
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_TRIGGER_KEY, DriverNExporter::TriggerKey),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_TRIGGER_COMBINE_KEYS, DriverNExporter::TriggerCombineKeys),
        NVal::DeclareNapiFunction(DriverNExporter::FUNCTION_INJECT_MULTI_POINTER_ACTION, DriverNExporter::InjectMultiPointerAction),
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

    HILOG_DEBUG("Uitest::DriverNExporter Export end");
    return exports_.AddProp(DriverNExporter::DRIVER_CLASS_NAME, classValue);
}

string DriverNExporter::GetClassName()
{
    return DriverNExporter::DRIVER_CLASS_NAME;
}

PointerMatrixNExporter::PointerMatrixNExporter(napi_env env, napi_value exports) : NExporter(env, exports) {}

PointerMatrixNExporter::~PointerMatrixNExporter() {}

napi_value PointerMatrixNExporter::Create(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("PointerMatrixNExporter::Create begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::TWO)) {
        HILOG_ERROR("PointerMatrixNExporter::Create Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetFirstArg, fingers] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid fingers");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, steps] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid steps");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    // fingers  number  是  多指操作中注入的手指数，取值范围：[1,10].
    // steps    number  是  每根手指操作的步骤数，取值范围：[1,1000].
    if (fingers < 1 || fingers > MAX_FINGERS) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid value. fingers[%d]", fingers);
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    if (steps < 1 || steps > MAX_STEPS) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid value. steps[%d]", steps);
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto pMatrix = NClass::GetEntityOf<PointerMatrix>(env, funcArg.GetThisVar());
    if (pMatrix == nullptr) {
        HILOG_ERROR("Cannot get entity of pMatrix");
        return nullptr;
    }

    napi_value jsMatrix = NClass::InstantiateClass(env, PointerMatrixNExporter::POINTER_MATRIX_CLASS_NAME, {});
    if (!jsMatrix) {
        HILOG_ERROR("Failed to instantiate jsMatrix class");
        return nullptr;
    }
    napi_ref ref = nullptr;
    napi_create_reference(env, jsMatrix, 1, &ref);

    pMatrix->Create(fingers, steps);
    if (pMatrix == nullptr) {
        HILOG_ERROR("Cannot get entity of pMatrix");
        return nullptr;
    }
    unique_ptr<PointerMatrix> pmPtr(pMatrix);
    napi_value jsMatrix_ = nullptr;
    napi_get_reference_value(env, ref, &jsMatrix_);
    if (!NClass::SetEntityFor<PointerMatrix>(env, jsMatrix_, move(pmPtr))) {
        HILOG_ERROR("Failed to set PointerMatrix entity");
        return nullptr;
    }
    HILOG_DEBUG("PointerMatrixNExporter::Create Success!");
    return jsMatrix_;
}

napi_value PointerMatrixNExporter::SetPoint(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("PointerMatrixNExporter::SetPoint begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::THREE)) {
        HILOG_ERROR("PointerMatrixNExporter::SetPoint Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto pointerMatrix = NClass::GetEntityOf<PointerMatrix>(env, funcArg.GetThisVar());
    if (!pointerMatrix) {
        HILOG_ERROR("Cannot get entity of pointerMatrix");
        return nullptr;
    }

    auto [resGetFirstArg, finger] = NVal(env, funcArg[NARG_POS::FIRST]).ToInt32();
    if (!resGetFirstArg) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid finger");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    auto [resGetSecondArg, step] = NVal(env, funcArg[NARG_POS::SECOND]).ToInt32();
    if (!resGetSecondArg) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid step");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }

    NVal obj(env, funcArg[NARG_POS::THIRD]);
    if (!obj.TypeIs(napi_object)) {
        HILOG_ERROR("PointerMatrixNExporter::Create Invalid point obj");
        return nullptr;
    }
    Point point = { std::get<1>(obj.GetProp("x").ToInt32()), std::get<1>(obj.GetProp("y").ToInt32()) };

    pointerMatrix->SetPoint(finger, step, point);
    return nullptr;
}

static napi_value PointerMatrixInitializer(napi_env env, napi_callback_info info)
{
    HILOG_DEBUG("PointerMatrixInitializer begin");
    NFuncArg funcArg(env, info);
    if (!funcArg.InitArgs(NARG_CNT::ZERO)) {
        HILOG_ERROR("pointerMatrix Number of arguments unmatched");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    auto pointerMatrix = make_unique<PointerMatrix>();
    if (!NClass::SetEntityFor<PointerMatrix>(env, funcArg.GetThisVar(), move(pointerMatrix))) {
        HILOG_ERROR("Failed to set pointerMatrix entity");
        NError(E_PARAMS).ThrowErr(env);
        return nullptr;
    }
    HILOG_DEBUG("PointerMatrix Initializer end");
    return funcArg.GetThisVar();
}

bool PointerMatrixNExporter::Export()
{
    HILOG_DEBUG("Uitest::PointerMatrixNExporter Export begin");
    vector<napi_property_descriptor> props = {
        NVal::DeclareNapiStaticFunction(PointerMatrixNExporter::FUNCTION_CREATE, PointerMatrixNExporter::Create),
        NVal::DeclareNapiFunction(PointerMatrixNExporter::FUNCTION_CREATE, PointerMatrixNExporter::Create),
        NVal::DeclareNapiFunction(PointerMatrixNExporter::FUNCTION_SET_POINT, PointerMatrixNExporter::SetPoint),
    };
    auto [succ, classValue] = NClass::DefineClass(exports_.env_, PointerMatrixNExporter::POINTER_MATRIX_CLASS_NAME,
        PointerMatrixInitializer, std::move(props));
    if (!succ) {
        HILOG_ERROR("Failed to define PointerMatrixNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }
    succ = NClass::SaveClass(exports_.env_, PointerMatrixNExporter::POINTER_MATRIX_CLASS_NAME, classValue);
    if (!succ) {
        HILOG_ERROR("Failed to save PointerMatrixNExporter class");
        NError(EIO).ThrowErr(exports_.env_);
        return false;
    }

    napi_value pMtr = NClass::InstantiateClass(exports_.env_, PointerMatrixNExporter::POINTER_MATRIX_CLASS_NAME, {});
    if (!pMtr) {
        HILOG_ERROR("Failed to instantiate ON class");
        return false;
    }
    napi_create_reference(exports_.env_, pMtr, 1, &PmRef);
    HILOG_DEBUG("Uitest::PointerMatrixNExporter Export end");
    return exports_.AddProp(PointerMatrixNExporter::POINTER_MATRIX_CLASS_NAME, pMtr);
}

string PointerMatrixNExporter::GetClassName()
{
    return PointerMatrixNExporter::POINTER_MATRIX_CLASS_NAME;
}

} // namespace OHOS::UiTest
