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

#include "test_socket_server.h"

#include <algorithm>
#include <arpa/inet.h>
#include <array>
#include <cerrno>
#include <sys/socket.h>
#include <unistd.h>

#include "securec.h"
#include "socket_dispatcher.h"
#include "socket_protocol.h"
#include "utils/log.h"

namespace OHOS::UiTest {
namespace {
constexpr int LISTEN_QUEUE_SIZE = 1;
} // namespace

TestSocket::TestSocket(int port) : running_(false), serverFd_(SOCKET_INVALID_FD), port_(port),
    clientFd_(SOCKET_INVALID_FD) {}

TestSocket::~TestSocket()
{
    Stop();
}

bool TestSocket::Start()
{
    if (running_.load()) {
        HILOG_INFO("[SOCKET] Test Socket already running, port: %d!", port_);
        return true;
    }
    if (port_ <= 0) {
        HILOG_ERROR("[SOCKET] invalid test socket port: %d", port_);
        return false;
    }
    if (!SetUpServer()) {
        HILOG_ERROR("[SOCKET] Test Socket start failed!");
        return false;
    }

    HILOG_INFO("[SOCKET] Test Socket start successed, port: %d!", port_);
    acceptThread_ = std::thread(&TestSocket::AcceptConnections, this);
    return true;
}

void TestSocket::Stop()
{
    running_.store(false);

    CloseSocket(serverFd_);
    int clientFd = SOCKET_INVALID_FD;
    {
        std::lock_guard<std::mutex> lock(clientMutex_);
        clientFd = clientFd_;
        clientFd_ = SOCKET_INVALID_FD;
    }
    CloseSocket(clientFd);

    if (acceptThread_.joinable()) {
        acceptThread_.join();
    }

    if (clientThread_.joinable()) {
        clientThread_.join();
    }
}

void TestSocket::CloseClientSocket(int clientFd)
{
    bool shouldClose = false;
    {
        std::lock_guard<std::mutex> lock(clientMutex_);
        if (clientFd_ == clientFd) {
            clientFd_ = SOCKET_INVALID_FD;
            shouldClose = true;
        }
    }
    if (!shouldClose) {
        return;
    }
    CloseSocket(clientFd);
}

bool TestSocket::SetUpServer()
{
    if (running_.load()) {
        HILOG_INFO("[SOCKET] Test Socket is running");
        return false;
    }

    serverFd_ = socket(AF_INET, SOCK_STREAM, 0);
    if (serverFd_ < 0) {
        HILOG_ERROR("[SOCKET] create socket failed!");
        return false;
    }

    int opt = 1;
    if (setsockopt(serverFd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        HILOG_ERROR("[SOCKET] set socket option failed!");
        CloseSocket(serverFd_);
        return false;
    }

    if (setsockopt(serverFd_, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt)) < 0) {
        HILOG_WARN("[SOCKET] set SO_REUSEPORT failed, errno=%d", errno);
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(port_);

    if (::bind(serverFd_, static_cast<const sockaddr*>(static_cast<const void*>(&serverAddr)),
        sizeof(serverAddr)) < 0) {
        HILOG_ERROR("[SOCKET] bind port failed!");
        CloseSocket(serverFd_);
        return false;
    }

    if (listen(serverFd_, LISTEN_QUEUE_SIZE) < 0) {
        HILOG_ERROR("[SOCKET] listen failed!");
        CloseSocket(serverFd_);
        return false;
    }
    running_.store(true);
    return true;
}

void TestSocket::AcceptConnections()
{
    while (running_.load()) {
        sockaddr_in clientAddr{};
        socklen_t clientLength = sizeof(clientAddr);
        int clientFd = accept(serverFd_, static_cast<sockaddr*>(static_cast<void*>(&clientAddr)), &clientLength);
        if (clientFd < 0) {
            if (!running_.load() || errno == EBADF || errno == EINVAL) {
                HILOG_WARN("[SOCKET] accept loop exit");
                break;
            }
            if (errno == EINTR) {
                HILOG_INFO("[SOCKET] accept signal interruption!");
                continue;
            }
            HILOG_ERROR("[SOCKET] accept connect failed, errno=%d!", errno);
            break;
        }

        if (!running_.load()) {
            CloseSocket(clientFd);
            break;
        }

        {
            std::lock_guard<std::mutex> lock(clientMutex_);
            if (clientFd_ != SOCKET_INVALID_FD) {
                HILOG_WARN("[SOCKET] client already connected, reject new client fd %d", clientFd);
                CloseSocket(clientFd);
                continue;
            }
        }

        if (!SetSocketTimeout(clientFd, SO_RCVTIMEO, SOCKET_TIMEOUT_S)) {
            HILOG_ERROR("[SOCKET] set recv timeout failed for client fd %d, errno=%d", clientFd, errno);
            CloseSocket(clientFd);
            continue;
        }
        if (!SetSocketTimeout(clientFd, SO_SNDTIMEO, SOCKET_TIMEOUT_S)) {
            HILOG_ERROR("[SOCKET] set send timeout failed for client fd %d, errno=%d", clientFd, errno);
            CloseSocket(clientFd);
            continue;
        }

        {
            std::lock_guard<std::mutex> lock(clientMutex_);
            clientFd_ = clientFd;
        }

        if (clientThread_.joinable()) {
            clientThread_.join();
        }
        clientThread_ = std::thread(&TestSocket::HandleClient, this, clientFd);
    }
}

bool TestSocket::RecvMessage(int clientFd, char* buffer, size_t len)
{
    size_t totalSize = 0;
    while (totalSize < len && running_.load()) {
        ssize_t recvBytes = recv(clientFd, buffer + totalSize, len - totalSize, 0);
        if (recvBytes > 0) {
            totalSize += static_cast<size_t>(recvBytes);
        } else if (recvBytes == 0) {
            HILOG_INFO("[SOCKET] client close connect");
            return false;
        } else {
            if (errno == EINTR) {
                continue;
            }
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                HILOG_ERROR("[SOCKET] recv message timeout, client fd %d", clientFd);
                return false;
            }
            HILOG_ERROR("[SOCKET] recv message failed, client fd %d, errno=%d", clientFd, errno);
            return false;
        }
    }
    return running_.load() && totalSize == len;
}

void TestSocket::HandleClient(int clientFd)
{
    std::array<char, SOCKET_HEAD_SIZE> head = {0};
    while (running_.load()) {
        if (!RecvMessage(clientFd, head.data(), head.size())) {
            break;
        }

        uint32_t totalSize = 0;
        if (memcpy_s(&totalSize, sizeof(totalSize), head.data(), head.size()) != EOK) {
            HILOG_ERROR("[SOCKET] copy message head failed");
            break;
        }
        totalSize = ntohl(totalSize);
        if (totalSize > SOCKET_TOTAL_SIZE || totalSize <= SOCKET_HEAD_SIZE) {
            HILOG_ERROR("[SOCKET] message style error, packet length is %u", totalSize);
            break;
        }

        MessageBuffer body(totalSize - SOCKET_HEAD_SIZE, 0);
        if (!RecvMessage(clientFd, body.data(), body.size())) {
            break;
        }

        SocketRequestPtr request;
        SocketCommand parsedCommand = static_cast<SocketCommand>(0);
        if (!DecodeSocketRequest(body, FindSocketHandler, request, &parsedCommand)) {
            SendErrorMessage(clientFd, parsedCommand, "Decode failed!");
            continue;
        }
        DispatchSocketRequest(clientFd, *request);
    }
    CloseClientSocket(clientFd);
}
} // namespace OHOS::UiTest
