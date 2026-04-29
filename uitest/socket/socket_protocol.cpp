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

#include "socket_protocol.h"

#include <arpa/inet.h>
#include <cerrno>
#include <limits>
#include <sys/socket.h>
#include <unistd.h>

#include "securec.h"
#include "utils/log.h"

namespace OHOS::UiTest {
namespace {
constexpr int SOCKET_SUCCESS_CODE = 0;
constexpr int SOCKET_ERROR_CODE = -1;
constexpr char SOCKET_SUCCESS_RESULT[] = "success";
const std::string COLLECTCOMMENTS = "collectComments";
const std::string INDENTATION = "indentation";
std::string JsonToCompactString(const Json::Value& value)
{
    Json::StreamWriterBuilder writerBuilder;
    writerBuilder[INDENTATION] = "";
    std::string jsonText = Json::writeString(writerBuilder, value);
    if (!jsonText.empty() && jsonText.back() == '\n') {
        jsonText.pop_back();
    }
    return jsonText;
}

bool BuildMessageBuffer(const std::string& payload, MessageBuffer& output)
{
    if (payload.size() > std::numeric_limits<uint32_t>::max()) {
        return false;
    }
    if (payload.size() + SOCKET_HEAD_SIZE > SOCKET_TOTAL_SIZE) {
        return false;
    }

    output.resize(SOCKET_HEAD_SIZE + payload.size());
    uint32_t totalSize = htonl(static_cast<uint32_t>(SOCKET_HEAD_SIZE + payload.size()));
    if (memcpy_s(output.data(), output.size(), &totalSize, SOCKET_HEAD_SIZE) != EOK) {
        return false;
    }
    if (!payload.empty()) {
        if (memcpy_s(output.data() + SOCKET_HEAD_SIZE, output.size() - SOCKET_HEAD_SIZE,
            payload.data(), payload.size()) != EOK) {
            return false;
        }
    }
    return true;
}
} // namespace

bool SetSocketTimeout(int socketFd, int optionName, int timeoutSec)
{
    struct timeval timeout = {timeoutSec, 0};
    return setsockopt(socketFd, SOL_SOCKET, optionName, &timeout, sizeof(timeout)) == 0;
}

void CloseSocket(int& socketFd)
{
    if (socketFd == SOCKET_INVALID_FD) {
        return;
    }
    shutdown(socketFd, SHUT_RDWR);
    close(socketFd);
    socketFd = SOCKET_INVALID_FD;
}

bool SendAll(int socketFd, const char* buffer, size_t len)
{
    size_t sentSize = 0;
    while (sentSize < len) {
        const ssize_t sendBytes = send(socketFd, buffer + sentSize, len - sentSize, 0);
        if (sendBytes > 0) {
            sentSize += static_cast<size_t>(sendBytes);
            continue;
        }
        if (sendBytes == 0) {
            HILOG_WARN("send returned zero, client fd %d", socketFd);
            return false;
        }
        if (sendBytes < 0 && errno == EINTR) {
            continue;
        }
        if (sendBytes < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            HILOG_WARN("send message timeout, client fd %d", socketFd);
        } else {
            HILOG_ERROR("send message failed, client fd %d, errno=%d", socketFd, errno);
        }
        return false;
    }
    return true;
}

bool EncodeJsonPayload(SocketCommand command, const Json::Value& value, MessageBuffer& output)
{
    Json::Value root(Json::objectValue);
    root[JSON_KEY_COMMAND] = ToCommandValue(command);
    root[JSON_KEY_ERR_CODE] = SOCKET_SUCCESS_CODE;
    root[JSON_KEY_ERR_MES] = "";
    root[JSON_KEY_RESULT] = value;

    std::string jsonText = JsonToCompactString(root);
    return BuildMessageBuffer(jsonText, output);
}

bool EncodeErrorPayload(SocketCommand command, const std::string& errorMessage, MessageBuffer& output)
{
    Json::Value root(Json::objectValue);
    root[JSON_KEY_COMMAND] = ToCommandValue(command);
    root[JSON_KEY_ERR_CODE] = SOCKET_ERROR_CODE;
    root[JSON_KEY_ERR_MES] = errorMessage;

    std::string jsonText = JsonToCompactString(root);
    return BuildMessageBuffer(jsonText, output);
}

bool EncodeStringPayload(SocketCommand command, const std::string& value, MessageBuffer& output)
{
    return EncodeJsonPayload(command, Json::Value(value), output);
}

bool EncodeBoolPayload(SocketCommand command, bool value, MessageBuffer& output)
{
    return EncodeJsonPayload(command, Json::Value(value), output);
}

bool ReadJsonString(const Json::Value& object, const char* key, size_t maxSize, std::string& value)
{
    if (key == nullptr || !object.isObject() || !object.isMember(key)) {
        return false;
    }

    const Json::Value& item = object[key];
    if (!item.isString()) {
        return false;
    }

    std::string result = item.asString();
    if (result.size() > maxSize) {
        return false;
    }
    value = std::move(result);
    return true;
}

bool ReadJsonInt(const Json::Value& object, const char* key, int& value)
{
    if (key == nullptr || !object.isObject() || !object.isMember(key)) {
        return false;
    }

    const Json::Value& item = object[key];
    if (item.isInt()) {
        value = item.asInt();
        return true;
    }
    if (item.isUInt() && item.asUInt() <= static_cast<Json::UInt>(std::numeric_limits<int>::max())) {
        value = static_cast<int>(item.asUInt());
        return true;
    }
    return false;
}

bool ReadJsonDouble(const Json::Value& object, const char* key, double& value)
{
    if (key == nullptr || !object.isObject() || !object.isMember(key)) {
        return false;
    }

    const Json::Value& item = object[key];
    if (!item.isNumeric()) {
        return false;
    }
    value = item.asDouble();
    return true;
}

bool ReadJsonBool(const Json::Value& object, const char* key, bool& value)
{
    if (key == nullptr || !object.isObject() || !object.isMember(key)) {
        return false;
    }

    const Json::Value& item = object[key];
    if (!item.isBool()) {
        return false;
    }
    value = item.asBool();
    return true;
}

bool ReadComponentId(const Json::Value& root, const Json::Value& params, std::string& componentId)
{
    return ReadJsonString(root, JSON_KEY_COMPONENT_ID, MAX_COMPONENT_ID_LENGTH, componentId) ||
        ReadJsonString(params, JSON_KEY_COMPONENT_ID, MAX_COMPONENT_ID_LENGTH, componentId);
}

bool DecodeSocketRequest(const MessageBuffer& input, FindHandlerFunc findHandler, SocketRequestPtr& request)
{
    return DecodeSocketRequest(input, findHandler, request, nullptr);
}

bool DecodeSocketRequest(const MessageBuffer& input, FindHandlerFunc findHandler,
    SocketRequestPtr& request, SocketCommand* parsedCommand)
{
    if (findHandler == nullptr) {
        return false;
    }

    Json::Value root;
    JSONCPP_STRING errors;
    Json::CharReaderBuilder builder;
    Json::CharReaderBuilder::strictMode(&builder.settings_);
    builder[COLLECTCOMMENTS] = false;
    std::unique_ptr<Json::CharReader> jsonReader(builder.newCharReader());
    if (!jsonReader) {
        return false;
    }

    const char* begin = input.data();
    const char* end = input.data() + input.size();
    if (!jsonReader->parse(begin, end, &root, &errors)) {
        return false;
    }

    int commandValue = 0;
    if (!ReadJsonInt(root, JSON_KEY_COMMAND, commandValue) || commandValue < 0) {
        return false;
    }
    SocketCommand command = static_cast<SocketCommand>(commandValue);
    if (parsedCommand != nullptr) {
        *parsedCommand = command;
    }

    Json::Value params(Json::objectValue);
    if (root.isMember(JSON_KEY_PARAMS)) {
        params = root[JSON_KEY_PARAMS];
        if (!params.isObject()) {
            return false;
        }
    }

    const auto* handler = findHandler(command);
    if (handler == nullptr || handler->decode == nullptr) {
        return false;
    }

    request = handler->decode(command, root, params);
    return request != nullptr;
}

void SendJsonMessage(int clientFd, SocketCommand command, const Json::Value& value)
{
    MessageBuffer buffer;
    if (!EncodeJsonPayload(command, value, buffer)) {
        HILOG_ERROR("encode json message failed!");
        return;
    }

    if (!SendAll(clientFd, buffer.data(), buffer.size())) {
        HILOG_ERROR("send json message failed!");
    }
}

void SendStrMessage(int clientFd, SocketCommand command, const std::string& value)
{
    MessageBuffer buffer;
    if (!EncodeStringPayload(command, value, buffer)) {
        HILOG_ERROR("encode message failed!");
        return;
    }

    if (!SendAll(clientFd, buffer.data(), buffer.size())) {
        HILOG_ERROR("send message failed!");
    }
}

void SendBoolMessage(int clientFd, SocketCommand command, bool value)
{
    MessageBuffer buffer;
    if (!EncodeBoolPayload(command, value, buffer)) {
        HILOG_ERROR("encode bool message failed!");
        return;
    }

    if (!SendAll(clientFd, buffer.data(), buffer.size())) {
        HILOG_ERROR("send bool message failed!");
    }
}

void SendSuccessMessage(int clientFd, SocketCommand command)
{
    SendStrMessage(clientFd, command, SOCKET_SUCCESS_RESULT);
}

void SendErrorMessage(int clientFd, SocketCommand command, const std::string& errorMessage)
{
    MessageBuffer buffer;
    if (!EncodeErrorPayload(command, errorMessage, buffer)) {
        HILOG_ERROR("encode error message failed!");
        return;
    }

    if (!SendAll(clientFd, buffer.data(), buffer.size())) {
        HILOG_ERROR("send error message failed!");
    }
}
} // namespace OHOS::UiTest
