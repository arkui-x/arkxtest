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
#include "uitest_n_exporter.h"
#include "driver_napi_libn.h"
#include "../core/driver.h"

namespace OHOS::UiTest {

using namespace std;
using namespace LibN;

static void InitMatchPattern(napi_env env, napi_value exports)
{
    char propertyName[] = "MatchPattern";
    napi_value obj = nullptr;
    napi_create_object(env, &obj);
    static napi_property_descriptor desc[] = {
        DECLARE_NAPI_STATIC_PROPERTY("EQUALS",
                                    NVal::CreateInt32(env, (int32_t)MatchPattern::EQUALS).val_),
        DECLARE_NAPI_STATIC_PROPERTY("CONTAINS",
                                    NVal::CreateInt32(env, (int32_t)MatchPattern::CONTAINS).val_),
        DECLARE_NAPI_STATIC_PROPERTY("STARTS_WITH",
                                    NVal::CreateInt32(env, (int32_t)MatchPattern::STARTS_WITH).val_),
        DECLARE_NAPI_STATIC_PROPERTY("ENDS_WITH",
                                    NVal::CreateInt32(env, (int32_t)MatchPattern::ENDS_WITH).val_),
    };
    napi_define_properties(env, obj, sizeof(desc) / sizeof(desc[0]), desc);
    napi_set_named_property(env, exports, propertyName, obj);
}

/***********************************************
 * Module export and register
 ***********************************************/
napi_value UiTestExport(napi_env env, napi_value exports)
{
    InitMatchPattern(env, exports);
    std::vector<std::unique_ptr<NExporter>> products;
    products.emplace_back(std::make_unique<OnNExporter>(env, exports));
    products.emplace_back(std::make_unique<ComponentNExporter>(env, exports));
    products.emplace_back(std::make_unique<DriverNExporter>(env, exports));
    for (auto &&product : products) {
        if (!product->Export()) {
            HILOG_ERROR("INNER BUG. Failed to export class %s for module UiTest ", product->GetClassName().c_str());
            return nullptr;
        } else {
            HILOG_ERROR("Class %s for module UiTest has been exported", product->GetClassName().c_str());
        }
    }
    return exports;
}

static napi_module _module = {
    .nm_version = 1,
    .nm_flags = 0,
    .nm_filename = nullptr,
    .nm_register_func = UiTestExport,
    .nm_modname = "UiTest",
    .nm_priv = ((void *)0),
    .reserved = {0}
};

extern "C" __attribute__((constructor)) void RegisterModule(void)
{
    napi_module_register(&_module);
}
} // namespace OHOS::UiTest
