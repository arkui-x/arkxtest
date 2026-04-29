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

#import <QuartzCore/QuartzCore.h>
#import <UIKit/UIKit.h>

#include "screen_capture_ios.h"
#include "utils/log.h"

namespace OHOS::UiTest {
namespace {
constexpr CFTimeInterval kFlushRunLoopWaitSeconds = 0.02;
constexpr CFTimeInterval kPresentRunLoopWaitSeconds = 0.03;

static UIWindow *GetWindowFromScene(UIScene *scene, UIWindow *&candidateWindow) {
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
        if (candidateWindow == nil) {
            candidateWindow = window;
        }
    }
    return nil;
}

static UIWindow *GetKeyWindow() {
    if (@available(iOS 13.0, *)) {
        NSSet<UIScene *> *scenes = [UIApplication sharedApplication].connectedScenes;
        UIWindow *candidateWindow = nil;
        for (UIScene *scene in scenes) {
            UIWindow *window = GetWindowFromScene(scene, candidateWindow);
            if (window != nil) {
                return window;
            }
        }
        if (candidateWindow != nil) {
            return candidateWindow;
        }
    }
    UIWindow *keyWindow = [UIApplication sharedApplication].keyWindow;
    if (keyWindow != nil) {
        return keyWindow;
    }
    NSArray<UIWindow *> *windows = [UIApplication sharedApplication].windows;
    return windows.count > 0 ? windows.firstObject : nil;
}

static CGRect ClampRectToSize(const CGRect rect, const CGSize size) {
    CGRect bounds = CGRectMake(0, 0, size.width, size.height);
    CGRect result = CGRectIntersection(rect, bounds);
    if (CGRectIsNull(result) || CGRectIsEmpty(result)) {
        return CGRectZero;
    }
    return result;
}

static CGRect MakePixelCropRect(const Rect &rect, const CGSize pixelSize) {
    if (rect.right <= rect.left || rect.bottom <= rect.top) {
        return CGRectZero;
    }
    CGRect cropRect = CGRectMake(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top);
    return CGRectIntegral(ClampRectToSize(cropRect, pixelSize));
}

static UIView *FindStageContainerView(UIView *view) {
    if (view == nil) {
        return nil;
    }
    Class stageContainerClass = NSClassFromString(@"StageContainerView");
    if (stageContainerClass != nil && [view isKindOfClass:stageContainerClass]) {
        return view;
    }
    for (UIView *subview in view.subviews) {
        UIView *target = FindStageContainerView(subview);
        if (target != nil) {
            return target;
        }
    }
    return nil;
}

static UIView *FindWindowView(UIView *view) {
    if (view == nil) {
        return nil;
    }
    Class windowViewClass = NSClassFromString(@"WindowView");
    if (windowViewClass != nil && [view isKindOfClass:windowViewClass]) {
        return view;
    }
    for (UIView *subview in view.subviews) {
        UIView *target = FindWindowView(subview);
        if (target != nil) {
            return target;
        }
    }
    return nil;
}

static bool ContainsNativeOverlayView(UIView *view) {
    if (view == nil) {
        return false;
    }

    NSString *className = NSStringFromClass(view.class);
    if ([className isEqualToString:@"AceSurfaceView"] || [className isEqualToString:@"WKWebView"] ||
        [className containsString:@"PlatformView"]) {
        return true;
    }

    for (UIView *subview in view.subviews) {
        if (ContainsNativeOverlayView(subview)) {
            return true;
        }
    }
    return false;
}

static bool PreferWindowHierarchyCapture(UIView *view) {
    if (view == nil) {
        return false;
    }

    NSString *className = NSStringFromClass(view.class);
    return [className isEqualToString:@"AccessibilityWindowView"];
}

static UIView *GetBestCaptureView(UIWindow *window) {
    if (window == nil) {
        return nil;
    }

    UIView *rootView = window.rootViewController.view ?: window;
    UIView *stageView = FindStageContainerView(rootView);
    Class stageContainerClass = NSClassFromString(@"StageContainerView");
    if (stageContainerClass != nil && [stageView isKindOfClass:stageContainerClass]) {
        UIView *activeWindow = nil;
        @try {
            id value = [stageView valueForKey:@"activeWindow"];
            if ([value isKindOfClass:[UIView class]]) {
                activeWindow = (UIView *)value;
            }
        } @catch (NSException *exception) {
            HILOG_WARN("ScreenCaptureToFile: failed to get activeWindow from StageContainerView");
        }
        if (activeWindow != nil && !activeWindow.hidden) {
            return activeWindow;
        }

        UIView *windowView = FindWindowView(stageView);
        if (windowView != nil && !windowView.hidden) {
            HILOG_WARN("ScreenCaptureToFile: activeWindow unavailable, fallback to WindowView");
            return windowView;
        }

        HILOG_WARN("ScreenCaptureToFile: StageContainerView has no active WindowView");
    }

    UIView *windowView = FindWindowView(rootView);
    if (windowView != nil && !windowView.hidden) {
        return windowView;
    }

    return rootView;
}

static void FlushUIUpdates(UIView *view) {
    if (view == nil) {
        return;
    }

    [view setNeedsLayout];
    [view layoutIfNeeded];
    [view.window setNeedsLayout];
    [view.window layoutIfNeeded];
    [CATransaction flush];
    CFRunLoopRunInMode(kCFRunLoopDefaultMode, kFlushRunLoopWaitSeconds, false);
    CFRunLoopRunInMode((CFStringRef)NSRunLoopCommonModes, kFlushRunLoopWaitSeconds, false);
}

static void WaitForPresentFrames(UIView *view, NSUInteger frameCount) {
    if (view == nil) {
        return;
    }

    for (NSUInteger index = 0; index < frameCount; index++) {
        FlushUIUpdates(view);
    }
}

static UIImage *RenderViewHierarchyImage(UIView *view, CGRect bounds) {
    if (view == nil || CGRectIsEmpty(bounds)) {
        HILOG_WARN("RenderViewHierarchyImage: view is nil or bounds empty");
        return nil;
    }

    UIGraphicsImageRendererFormat *format = [UIGraphicsImageRendererFormat defaultFormat];
    if (view.window.screen != nil) {
        format.scale = view.window.screen.scale;
    }
    __block BOOL drawn = NO;
    UIGraphicsImageRenderer *renderer = [[UIGraphicsImageRenderer alloc] initWithSize:bounds.size format:format];
    UIImage *image = [renderer imageWithActions:^(UIGraphicsImageRendererContext *context) {
        drawn = [view drawViewHierarchyInRect:bounds afterScreenUpdates:YES];
        if (!drawn) {
            [view.layer renderInContext:context.CGContext];
        }
    }];
    return image;
}

static UIImage *CaptureSnapshotViewImage(UIView *targetView) {
    if (targetView == nil || CGRectIsEmpty(targetView.bounds)) {
        HILOG_WARN("CaptureSnapshotViewImage: target view is nil or bounds empty");
        return nil;
    }

    WaitForPresentFrames(targetView, 3);
    UIImage *image = RenderViewHierarchyImage(targetView, targetView.bounds);
    return image;
}

static UIImage *CaptureNativeOverlayWindowImage(UIWindow *window) {
    UIView *rootView = window.rootViewController.view ?: window;
    if (!ContainsNativeOverlayView(rootView)) {
        return nil;
    }

    CGRect windowBounds = window.bounds;
    UIImage *image = RenderViewHierarchyImage(window, windowBounds);
    if (image != nil) {
        return image;
    }

    HILOG_WARN("ScreenCaptureToFile: window hierarchy capture failed for native overlay content");
    return nil;

}

static UIImage *CapturePreferredTargetViewImage(UIWindow *window, UIView *targetView) {
    if (targetView == nil) {
        return nil;
    }

    [targetView setNeedsLayout];
    [targetView layoutIfNeeded];

    if (PreferWindowHierarchyCapture(targetView)) {
        CGRect windowBounds = window.bounds;
        UIImage *preferredImage = RenderViewHierarchyImage(window, windowBounds);
        if (preferredImage != nil) {
            return preferredImage;
        }
        HILOG_WARN("ScreenCaptureToFile: preferred window hierarchy capture returned nil for %{public}s",
                   NSStringFromClass(targetView.class).UTF8String);
    }

    UIImage *snapshotImage = CaptureSnapshotViewImage(targetView);
    if (snapshotImage != nil) {
        return snapshotImage;
    }

    HILOG_WARN("ScreenCaptureToFile: snapshot capture returned nil for %{public}s",
               NSStringFromClass(targetView.class).UTF8String);
    return nil;

}

static UIImage *CaptureWindowHierarchyImage(UIWindow *window) {
    CGRect windowBounds = window.bounds;
    UIImage *image = RenderViewHierarchyImage(window, windowBounds);
    return image;
}

static UIImage *CaptureWindowImage(UIWindow *window) {
    if (window == nil) {
        return nil;
    }
    if (![NSThread isMainThread]) {
        HILOG_ERROR("CaptureWindowImage: must be called on main thread");
        return nil;
    }

    __block UIImage *image = nil;
    auto captureBlock = ^{
        WaitForPresentFrames(window, 3);

        // Keep the capture source in window coordinates first so crop Rect semantics stay stable.
        image = CaptureWindowHierarchyImage(window);
        if (image != nil) {
            return;
        }

        image = CaptureNativeOverlayWindowImage(window);
        if (image != nil) {
            return;
        }

        UIView *targetView = GetBestCaptureView(window);
        image = CapturePreferredTargetViewImage(window, targetView);
        if (image != nil) {
            return;
        }
    };

    captureBlock();
    return image;
}

static UIImage *CropImageIfNeeded(UIImage *image, const Rect &rect) {
    if (image == nil) {
        return nil;
    }
    if (rect.right <= rect.left || rect.bottom <= rect.top) {
        return image;
    }

    if (image.CGImage == nil) {
        HILOG_ERROR("ScreenCaptureToFile: image CGImage is nil");
        return image;
    }

    CGSize pixelSize = CGSizeMake(CGImageGetWidth(image.CGImage), CGImageGetHeight(image.CGImage));
    CGRect pixelCropRect = MakePixelCropRect(rect, pixelSize);
    if (CGRectIsEmpty(pixelCropRect)) {
        HILOG_ERROR("ScreenCaptureToFile: pixel crop rect out of bounds");
        return image;
    }

    CGImageRef cropped = CGImageCreateWithImageInRect(image.CGImage, pixelCropRect);
    if (cropped == nil) {
        HILOG_ERROR("ScreenCaptureToFile: crop failed");
        return image;
    }

    UIImage *target = [UIImage imageWithCGImage:cropped scale:image.scale orientation:image.imageOrientation];
    CGImageRelease(cropped);
    return target;
}

static NSString *ResolveSandboxPath(NSString *path, NSString *prefix, NSSearchPathDirectory directory) {
    if (![path hasPrefix:prefix] && ![path isEqualToString:[prefix substringToIndex:prefix.length - 1]]) {
        return path;
    }
    NSString *baseDir = NSSearchPathForDirectoriesInDomains(directory, NSUserDomainMask, YES).firstObject;
    if (baseDir == nil) {
        return path;
    }
    NSString *rootPath = [prefix substringToIndex:prefix.length - 1];
    NSString *subPath = [path isEqualToString:rootPath] ? @"" : [path substringFromIndex:prefix.length];
    return subPath.length > 0 ? [baseDir stringByAppendingPathComponent:subPath] : baseDir;
}

static NSString *ResolveOutputPath(NSString *path) {
    NSString *resolvedPath = ResolveSandboxPath(path, @"/Documents/", NSDocumentDirectory);
    resolvedPath = ResolveSandboxPath(resolvedPath, @"/Library/", NSLibraryDirectory);
    if ([resolvedPath hasPrefix:@"/tmp/"] || [resolvedPath isEqualToString:@"/tmp"]) {
        NSString *tmpDir = NSTemporaryDirectory();
        if (tmpDir == nil) {
            return resolvedPath;
        }
        NSString *subPath = [resolvedPath isEqualToString:@"/tmp"] ? @"" : [resolvedPath substringFromIndex:5];
        return subPath.length > 0 ? [tmpDir stringByAppendingPathComponent:subPath] : tmpDir;
    }
    return resolvedPath;
}

static void EnsureParentDirectoryExists(NSString *path) {
    NSString *parentDir = [path stringByDeletingLastPathComponent];
    if (parentDir.length == 0) {
        return;
    }
    NSError *dirError = nil;
    [[NSFileManager defaultManager] createDirectoryAtPath:parentDir
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:&dirError];
    if (dirError != nil) {
        HILOG_WARN("ScreenCaptureToFile: create dir failed path=%{public}s error=%{public}s", [parentDir UTF8String],
                   [dirError.localizedDescription ?: @"<nil>" UTF8String]);
    }
}

static bool IsPathInsideDirectory(NSString *path, NSString *directory) {
    if (path == nil || directory == nil) {
        return false;
    }
    NSString *normalizedPath = [path stringByStandardizingPath];
    NSString *normalizedDirectory = [directory stringByStandardizingPath];
    if ([normalizedPath isEqualToString:normalizedDirectory]) {
        return true;
    }
    NSString *directoryPrefix = [normalizedDirectory stringByAppendingString:@"/"];
    return [normalizedPath hasPrefix:directoryPrefix];
}

static bool IsSandboxWritablePath(NSString *path) {
    if (path == nil) {
        return false;
    }
    NSString *homeDir = NSHomeDirectory();
    if (IsPathInsideDirectory(path, homeDir)) {
        return true;
    }
    NSString *tmpDir = NSTemporaryDirectory();
    return IsPathInsideDirectory(path, tmpDir);
}

static NSData *EncodeImageToPngData(UIImage *image) {
    NSData *pngData = UIImagePNGRepresentation(image);
    if (pngData == nil) {
        HILOG_ERROR("ScreenCaptureToFile: png encode failed");
        return nil;
    }
    return pngData;
}

static NSString *ResolveValidatedOutputPath(const std::string &path) {
    NSString *originPath = [NSString stringWithUTF8String:path.c_str()];
    NSString *nsPath = originPath;
    if (nsPath == nil || nsPath.length == 0) {
        HILOG_ERROR("ScreenCaptureToFile: invalid path string");
        return nil;
    }

    nsPath = ResolveOutputPath(nsPath);
    if (!IsSandboxWritablePath(nsPath)) {
        HILOG_ERROR("ScreenCaptureToFile: path is outside sandbox, path=%{public}s", [nsPath UTF8String]);
        return nil;
    }
    return nsPath;
}

static bool PersistPngDataToPath(NSData *pngData, NSString *nsPath, NSString *originPath) {
    EnsureParentDirectoryExists(nsPath);
    HILOG_WARN("ScreenCaptureToFile will save to %{public}s (origin: %{public}s)", [nsPath UTF8String],
               [originPath UTF8String]);

    NSError *writeError = nil;
    BOOL ok = [pngData writeToFile:nsPath options:NSDataWritingAtomic error:&writeError];
    if (!ok) {
        HILOG_ERROR("ScreenCaptureToFile: write failed, path=%{public}s (origin: %{public}s)", [nsPath UTF8String],
                    [originPath UTF8String]);
        return false;
    }
    return true;
}

static bool WriteImageToPath(UIImage *image, const std::string &path) {
    if (image == nil) {
        return false;
    }

    NSData *pngData = EncodeImageToPngData(image);
    if (pngData == nil) {
        return false;
    }

    NSString *originPath = [NSString stringWithUTF8String:path.c_str()];
    NSString *nsPath = ResolveValidatedOutputPath(path);
    if (nsPath == nil) {
        return false;
    }

    return PersistPngDataToPath(pngData, nsPath, originPath);
}

static bool CaptureAndWriteImageOnMainThread(const std::string &path, const Rect &rect) {
    @autoreleasepool {
        UIWindow *window = GetKeyWindow();
        if (window == nil) {
            HILOG_ERROR("ScreenCaptureToFile: window is null");
            return false;
        }

        UIImage *image = CaptureWindowImage(window);
        if (image == nil) {
            HILOG_ERROR("ScreenCaptureToFile: capture failed");
            return false;
        }

        UIImage *target = CropImageIfNeeded(image, rect);
        if (target == nil) {
            HILOG_WARN("ScreenCaptureToFile: target image is nil after crop");
            return false;
        }
        return WriteImageToPath(target, path);
    }
}

static bool ValidateScreenCaptureRequest(const std::string &path, const Rect &rect)
{
    if (path.empty()) {
        HILOG_ERROR("ScreenCaptureToFile: empty path");
        return false;
    }
    return true;
}
}  // namespace

bool ScreenCaptureToFile(const std::string &path, const Rect &rect) {
    Rect normalizedRect = rect;
    if (!ValidateScreenCaptureRequest(path, normalizedRect)) {
        return false;
    }
    if (![NSThread isMainThread]) {
        HILOG_ERROR("ScreenCaptureToFile: must be called on main thread");
        return false;
    }
    return CaptureAndWriteImageOnMainThread(path, normalizedRect);
}
}  // namespace OHOS::UiTest
