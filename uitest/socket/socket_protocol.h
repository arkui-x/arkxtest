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

#ifndef UITEST_SOCKET_PROTOCOL_H
#define UITEST_SOCKET_PROTOCOL_H

#include <netinet/in.h>
#include <string>
#include <vector>

#include "json/json.h"
#include "socket_request.h"

namespace OHOS::UiTest {
constexpr size_t SOCKET_HEAD_SIZE = sizeof(uint32_t);
constexpr size_t SOCKET_TOTAL_SIZE = 1024 * 1024;
constexpr int SOCKET_TIMEOUT_S = 60;
constexpr int SOCKET_INVALID_FD = -1;
using MessageBuffer = std::vector<char>;
using FindHandlerFunc = const SocketHandlerEntry* (*)(SocketCommand);

bool SetSocketTimeout(int socketFd, int optionName, int timeoutSec);
void CloseSocket(int& socketFd);
bool SendAll(int socketFd, const char* buffer, size_t len);

bool EncodeJsonPayload(SocketCommand command, const Json::Value& value, MessageBuffer& output);
bool EncodeStringPayload(SocketCommand command, const std::string& value, MessageBuffer& output);
bool EncodeBoolPayload(SocketCommand command, bool value, MessageBuffer& output);

bool ReadJsonString(const Json::Value& object, const char* key, size_t maxSize, std::string& value);
bool ReadJsonInt(const Json::Value& object, const char* key, int& value);
bool ReadJsonDouble(const Json::Value& object, const char* key, double& value);
bool ReadJsonBool(const Json::Value& object, const char* key, bool& value);
bool ReadComponentId(const Json::Value& root, const Json::Value& params, std::string& componentId);

bool DecodeSocketRequest(const MessageBuffer& input, FindHandlerFunc findHandler, SocketRequestPtr& request);
bool DecodeSocketRequest(const MessageBuffer& input, FindHandlerFunc findHandler,
    SocketRequestPtr& request, SocketCommand* parsedCommand);

void SendJsonMessage(int clientFd, SocketCommand command, const Json::Value& value);
void SendStrMessage(int clientFd, SocketCommand command, const std::string& value);
void SendBoolMessage(int clientFd, SocketCommand command, bool value);
void SendSuccessMessage(int clientFd, SocketCommand command);
void SendErrorMessage(int clientFd, SocketCommand command, const std::string& errorMessage);
} // namespace OHOS::UiTest
#endif // UITEST_SOCKET_PROTOCOL_H
