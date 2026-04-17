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

#ifndef UITEST_TEST_SOCKET_SERVER_H
#define UITEST_TEST_SOCKET_SERVER_H

#include <netinet/in.h>

#include <atomic>
#include <mutex>
#include <thread>

namespace OHOS::UiTest {

class TestSocket {
public:
    explicit TestSocket(int port);
    ~TestSocket();

    bool Start();
    void Stop();

private:
    bool SetUpServer();
    void AcceptConnections();
    bool RecvMessage(int clientFd, char* buffer, size_t len);
    void HandleClient(int clientFd);
    void CloseClientSocket(int clientFd);

    std::atomic<bool> running_;
    int serverFd_;
    const int port_;
    int clientFd_ = -1;
    std::mutex clientMutex_;
    std::thread acceptThread_;
    std::thread clientThread_;
};
} // namespace OHOS::UiTest
#endif // UITEST_TEST_SOCKET_SERVER_H
