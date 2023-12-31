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

#ifndef UITEST_LIBN_N_VAL_H
#define UITEST_LIBN_N_VAL_H

#include <cstdint>
#include <memory>
#include <tuple>
#include <vector>

#include "n_class.h"

namespace OHOS {
namespace UiTest {
namespace LibN {
class NVal final {
public:
    NVal() = default;
    NVal(napi_env nEnv, napi_value nVal);
    NVal(const NVal &) = default;
    NVal &operator=(const NVal &) = default;
    virtual ~NVal() = default;

    // NOTE! env_ and val_ is LIKELY to be null
    napi_env env_ = nullptr;
    napi_value val_ = nullptr;

    explicit operator bool() const;
    bool TypeIs(napi_valuetype expType) const;
    bool TypeIsError(bool checkErrno = false) const;

    /* SHOULD ONLY BE USED FOR EXPECTED TYPE */
    std::tuple<bool, std::unique_ptr<char[]>, size_t> ToUTF8String() const;
    std::tuple<bool, std::unique_ptr<char[]>, size_t> ToUTF16String() const;
    std::tuple<bool, void *> ToPointer() const;
    std::tuple<bool, bool> ToBool() const;
    std::tuple<bool, int32_t> ToInt32() const;
    std::tuple<bool, int64_t> ToInt64() const;
    std::tuple<bool, void *, size_t> ToArraybuffer() const;
    std::tuple<bool, void *, size_t> ToTypedArray() const;
    std::tuple<bool, std::vector<std::string>, uint32_t> ToStringArray();
    std::tuple<bool, double> ToDouble() const;

    /* Static helpers to create js objects */
    static NVal CreateUndefined(napi_env env);
    static NVal CreateInt64(napi_env env, int64_t val);
    static NVal CreateInt32(napi_env env, int32_t val);
    static NVal CreateObject(napi_env env);
    static NVal CreateBool(napi_env env, bool val);
    static NVal CreateUTF8String(napi_env env, std::string str);
    static NVal CreateUTF8String(napi_env env, const char *str, ssize_t len);
    static NVal CreateUint8Array(napi_env env, void *buf, size_t bufLen);
    static std::tuple<NVal, void *> CreateArrayBuffer(napi_env env, size_t len);

    template <class T> static NVal CreateArray(napi_env env, std::vector<std::unique_ptr<T>> vec, std::string className)
    {
        napi_value res = nullptr;
        napi_create_array_with_length(env, vec.size(), &res);
        for (size_t i = 0; i < vec.size(); i++) {
            napi_value jsClass = NClass::InstantiateClass(env, className, {});
            NClass::SetEntityFor<T>(env, jsClass, move(vec[i]));
            napi_set_element(env, res, i, jsClass);
        }
        vec.clear();
        return {env, res};
    }

    /* SHOULD ONLY BE USED FOR OBJECT */
    bool HasProp(std::string propName) const;
    NVal GetProp(std::string propName) const;
    bool AddProp(std::vector<napi_property_descriptor> &&propVec) const;
    bool AddProp(std::string propName, napi_value nVal) const;

    /* Static helpers to create prop of js objects */
    static napi_property_descriptor DeclareNapiProperty(const char *name, napi_value val);
    static napi_property_descriptor DeclareNapiStaticProperty(const char *name, napi_value val);
    static napi_property_descriptor DeclareNapiFunction(const char *name, napi_callback func);
    static napi_property_descriptor DeclareNapiStaticFunction(const char *name, napi_callback func);
    static napi_property_descriptor DeclareNapiGetter(const char *name, napi_callback getter);
    static napi_property_descriptor DeclareNapiSetter(const char *name, napi_callback setter);
    static inline napi_property_descriptor
        DeclareNapiGetterSetter(const char *name, napi_callback getter, napi_callback setter);
};
} // namespace LibN
} // namespace UiTest
} // namespace OHOS

#endif // UITEST_LIBN_N_VAL_H