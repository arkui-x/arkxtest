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

#include "common_type.h"
#include "display_impl.h"
#include "utils/log.h"

namespace OHOS::UiTest {
namespace {
const char* const K_ORIENTATION_MASK_UPDATE_NOTIFICATION_NAME =
    "arkui_x.iosPlatform.setPreferredOrientationNotificationName";
const char* const K_ORIENTATION_MASK_UPDATE_NOTIFICATION_KEY =
    "arkui_x.iosPlatform.setPreferredOrientationNotificationKey";

static UIInterfaceOrientationMask GetOrientationMask(int rotation) {
    switch (static_cast<DisplayRotation>(rotation)) {
        case ROTATION_0:
            return UIInterfaceOrientationMaskPortrait;
        case ROTATION_90:
            return UIInterfaceOrientationMaskLandscapeLeft;
        case ROTATION_180:
            return UIInterfaceOrientationMaskPortraitUpsideDown;
        case ROTATION_270:
            return UIInterfaceOrientationMaskLandscapeRight;
        default:
            HILOG_WARN("SetDisplayRotationIOS: unknown rotation %{public}d, using portrait", rotation);
            return UIInterfaceOrientationMaskPortrait;
    }
}

static void PostOrientationMaskNotification(UIInterfaceOrientationMask mask) {
    [[NSNotificationCenter defaultCenter] postNotificationName:@(K_ORIENTATION_MASK_UPDATE_NOTIFICATION_NAME)
                                                        object:nil
                                                      userInfo:@{
                                                          @(K_ORIENTATION_MASK_UPDATE_NOTIFICATION_KEY) : @(mask)
                                                      }];
}
}  // namespace

void DisplayImpl::SetDisplayRotation(const int rotation) {
    UIInterfaceOrientationMask mask = GetOrientationMask(rotation);
    dispatch_async(dispatch_get_main_queue(), ^{
        PostOrientationMaskNotification(mask);
    });
}
}  // namespace OHOS::UiTest