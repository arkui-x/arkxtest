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

#ifndef UITEST_LIBN_N_ERROR_H
#define UITEST_LIBN_N_ERROR_H

#include <functional>
#include <string>
#include <tuple>
#include <unordered_map>

#include "n_napi.h"

namespace OHOS {
namespace UiTest {
namespace LibN {

#ifdef IOS_PLATFORM
constexpr int EBADR = 53;
constexpr int EBADFD = 77;
constexpr int ERESTART = 85;
#endif
constexpr int UNKROWN_ERR = -1;
constexpr int ERRNO_NOERR = 0;
constexpr int ARKUI_TEST_TAG = 17000000;

enum ErrCodeSuffixOfArkUITest {
    E_AWAIT = 2,
    E_ASSERTFAILD,
    E_DESTROYED,
    E_NOTSUPPORT
};

enum CommonErrCode {
    E_PERMISSION = 201,
    E_PERMISSION_SYS = 202,
    E_PARAMS = 401,
    E_DEVICENOTSUPPORT = 801,
    E_OSNOTSUPPORT = 901
};

static inline std::unordered_map<int, std::pair<int32_t, std::string>> errCodeTable {
    { E_PARAMS, { E_PARAMS, "The input parameter is invalid" } },
    { ARKUI_TEST_TAG + E_AWAIT, { ARKUI_TEST_TAG + E_AWAIT, "The async function was not called with await" } },
    { ARKUI_TEST_TAG + E_ASSERTFAILD, { ARKUI_TEST_TAG + E_ASSERTFAILD, "The assertion is failed" } },
    { ARKUI_TEST_TAG + E_DESTROYED, { ARKUI_TEST_TAG + E_DESTROYED, "The window is invisible or destroyed" } },
    { ARKUI_TEST_TAG + E_NOTSUPPORT, { ARKUI_TEST_TAG + E_NOTSUPPORT, "The action is not supported on this window" } },
};

class NError {
public:
    NError();
    NError(int ePosix);
    NError(std::function<std::tuple<uint32_t, std::string>()> errGen);
    ~NError() = default;
    explicit operator bool() const;
    napi_value GetNapiErr(napi_env env);
    napi_value GetNapiErr(napi_env env, int errCode);
    napi_value GetNapiErrAddData(napi_env env, int errCode, napi_value data);
    void ThrowErr(napi_env env);
    void ThrowErr(napi_env env, int errCode);
    void ThrowErr(napi_env env, std::string errMsg);
    void ThrowErrAddData(napi_env env, int errCode, napi_value data);

private:
    int errno_ = ERRNO_NOERR;
    std::string errMsg_;
};
} // namespace LibN
} // namespace UiTest
} // namespace OHOS

#endif // UITEST_LIBN_N_ERROR_H