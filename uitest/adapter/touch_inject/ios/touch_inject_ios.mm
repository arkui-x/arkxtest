/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
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

#import <UIKit/UIKit.h>
#import <dispatch/dispatch.h>
#import <objc/message.h>
#import <objc/runtime.h>

#include <chrono>
#include <mutex>
#include <thread>

#include "base/log/log_wrapper.h"
#include "base/utils/time_util.h"
#include "touch_inject_proxy.h"

@interface ArkUIDisplayLinkWaiter : NSObject
- (instancetype)initWithSemaphore:(dispatch_semaphore_t)semaphore;
- (void)start;
@end

@implementation ArkUIDisplayLinkWaiter {
    dispatch_semaphore_t semaphore_;
    CADisplayLink *displayLink_;
}

- (instancetype)initWithSemaphore:(dispatch_semaphore_t)semaphore {
    self = [super init];
    if (self) {
        semaphore_ = semaphore;
    }
    return self;
}

- (void)start {
    displayLink_ = [CADisplayLink displayLinkWithTarget:self selector:@selector(onDisplayLink:)];
    [displayLink_ addToRunLoop:[NSRunLoop mainRunLoop] forMode:NSRunLoopCommonModes];
}

- (void)dealloc {
    [displayLink_ invalidate];
    displayLink_ = nil;
    [super dealloc];
}

- (void)onDisplayLink:(CADisplayLink *)displayLink {
    [displayLink invalidate];
    displayLink_ = nil;
    dispatch_semaphore_signal(semaphore_);
}

@end

namespace OHOS::UiTest {

namespace {
constexpr int K_ACTION_DOWN = 0;
constexpr int K_ACTION_UP = 1;
constexpr int K_ACTION_MOVE = 2;
constexpr int32_t K_SYNTHETIC_POINTER_ID = 10000;
constexpr uint32_t K_SYNTHETIC_FIRST_MOVE_SETTLE_MS = 32;
std::mutex g_syntheticTouchMutex;

static void WaitForNextDisplayFrame(uint32_t timeoutMs) {
    if ([NSThread isMainThread]) {
        return;
    }
    dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
    dispatch_async(dispatch_get_main_queue(), ^{
        ArkUIDisplayLinkWaiter *waiter = [[ArkUIDisplayLinkWaiter alloc] initWithSemaphore:semaphore];
        [waiter start];
        [waiter release];
    });
    dispatch_semaphore_wait(semaphore,
                            dispatch_time(DISPATCH_TIME_NOW, static_cast<int64_t>(timeoutMs) * NSEC_PER_MSEC));
}

static UIWindow *GetKeyWindowFromScene(UIScene *scene) {
    if (scene.activationState != UISceneActivationStateForegroundActive) {
        return nil;
    }
    if (![scene isKindOfClass:[UIWindowScene class]]) {
        return nil;
    }
    UIWindowScene *windowScene = (UIWindowScene *)scene;
    for (UIWindow *window in windowScene.windows) {
        if (window.isKeyWindow) {
            return window;
        }
    }
    if (windowScene.windows.count > 0) {
        return windowScene.windows.firstObject;
    }
    return nil;
}

static UIWindow *GetTopKeyWindow() {
    if (@available(iOS 13.0, *)) {
        for (UIScene *scene in [UIApplication sharedApplication].connectedScenes) {
            UIWindow *window = GetKeyWindowFromScene(scene);
            if (window != nil) {
                return window;
            }
        }
    }
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    UIWindow *keyWindow = [UIApplication sharedApplication].keyWindow;
#pragma clang diagnostic pop
    if (keyWindow != nil) {
        return keyWindow;
    }
    return [UIApplication sharedApplication].windows.firstObject;
}

static UIViewController *GetTopViewController() {
    UIWindow *window = GetTopKeyWindow();
    if (window == nil) {
        return nil;
    }
    UIViewController *top = window.rootViewController;
    while (top != nil && top.presentedViewController != nil) {
        top = top.presentedViewController;
    }
    return top;
}

static UIViewController *GetStageTopViewController() {
    Class stageAppCls = NSClassFromString(@"StageApplication");
    if (stageAppCls == Nil) {
        return nil;
    }
    SEL sel = NSSelectorFromString(@"getApplicationTopViewController");
    if (![stageAppCls respondsToSelector:sel]) {
        return nil;
    }
    UIViewController *(*msgSend)(id, SEL) = (UIViewController * (*)(id, SEL)) objc_msgSend;
    return msgSend(stageAppCls, sel);
}

static UIView *GetActiveWindowView() {
    SEL getWindowViewSel = NSSelectorFromString(@"getWindowView");
    Class windowViewCls = NSClassFromString(@"WindowView");
    const auto resolveWindowView = ^UIView *(UIViewController *controller) {
        if (controller == nil || ![controller respondsToSelector:getWindowViewSel]) {
            return nil;
        }
        UIView *(*msgSend)(id, SEL) = (UIView * (*)(id, SEL)) objc_msgSend;
        UIView *view = msgSend(controller, getWindowViewSel);
        if (windowViewCls != Nil && [view isKindOfClass:windowViewCls]) {
            return view;
        }
        return nil;
    };

    if (auto *windowView = resolveWindowView(GetStageTopViewController())) {
        return windowView;
    }
    if (auto *windowView = resolveWindowView(GetTopViewController())) {
        return windowView;
    }

    UIWindow *window = GetTopKeyWindow();
    if (window != nil) {
        for (UIView *subview in window.subviews) {
            if (windowViewCls != Nil && [subview isKindOfClass:windowViewCls]) {
                return subview;
            }
        }
    }
    return nil;
}

static int64_t NormalizeSyntheticEventTime(int64_t eventTime) {
    if (eventTime <= 0) {
        const int64_t currentTimeUs = OHOS::Ace::GetMicroTickCount();
        return currentTimeUs;
    }
    constexpr int64_t kMillisToMicrosThreshold = 1000000000000LL;
    const int64_t normalizedEventTime =
        eventTime < kMillisToMicrosThreshold ? eventTime * 1000 : eventTime;

    return normalizedEventTime;
}

static UITouchPhase ConvertSyntheticTouchPhase(int action) {
    switch (action) {
        case K_ACTION_DOWN:
            return UITouchPhaseBegan;
        case K_ACTION_MOVE:
            return UITouchPhaseMoved;
        case K_ACTION_UP:
            return UITouchPhaseEnded;
        default:
            return UITouchPhaseCancelled;
    }
}

static bool DispatchSyntheticTouchEvent(int action, float x, float y, int64_t eventTime) {
    std::lock_guard<std::mutex> lock(g_syntheticTouchMutex);
    const int64_t normalizedEventTime = NormalizeSyntheticEventTime(eventTime);
    __block bool result = false;
    __block int64_t dispatchedEventTimeUs = normalizedEventTime;
    static bool firstSyntheticMovePending = false;

    auto block = ^{
        dispatchedEventTimeUs = OHOS::Ace::GetMicroTickCount();
        UIView *windowView = GetActiveWindowView();
        if (windowView == nil) {
            LOGE("DispatchSyntheticTouchEvent: windowView is nil");
            return;
        }
        SEL dispatchSel = NSSelectorFromString(@"dispatchSyntheticTouchWithPhase:pixelX:pixelY:pointerId:timeStamp:");
        if (![windowView respondsToSelector:dispatchSel]) {
            LOGE("DispatchSyntheticTouchEvent: selector missing");
            return;
        }
        using DispatchFunc = BOOL (*)(id, SEL, UITouchPhase, CGFloat, CGFloat, int32_t, int64_t);
        DispatchFunc msgSend = reinterpret_cast<DispatchFunc>(objc_msgSend);
        result = msgSend(windowView, dispatchSel, ConvertSyntheticTouchPhase(action), static_cast<CGFloat>(x),
                         static_cast<CGFloat>(y), K_SYNTHETIC_POINTER_ID, dispatchedEventTimeUs);
    };

    if ([NSThread isMainThread]) {
        block();
    } else {
        dispatch_sync(dispatch_get_main_queue(), block);
    }

    if (action == K_ACTION_DOWN) {
        firstSyntheticMovePending = true;
    } else if (action == K_ACTION_MOVE && result && firstSyntheticMovePending) {
        WaitForNextDisplayFrame(K_SYNTHETIC_FIRST_MOVE_SETTLE_MS);
        firstSyntheticMovePending = false;
    } else if (action == K_ACTION_UP) {
        firstSyntheticMovePending = false;
    }

    return result;
}
}  // namespace

bool InjectTouchEventOC(int action, float x, float y, int64_t downTime, int64_t eventTime) {
    (void)downTime;
    return DispatchSyntheticTouchEvent(action, x, y, eventTime);
}
}  // namespace OHOS::UiTest
