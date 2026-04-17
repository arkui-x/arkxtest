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

package ohos.ace.plugin.screencapture;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Rect;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import android.view.Display;
import android.view.PixelCopy;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import ohos.ace.plugin.screencapture.CurrentActivityHolder;

/**
 * ScreenCaptureHelper
 *
 * @since 1
 */
public class ScreenCaptureHelper extends ScreenCaptureHelperBase {
    private static final String TAG = "ScreenCaptureHelper";
    private static final long PIXEL_COPY_TIMEOUT_MS = 2000L;

    private HandlerThread mPixelCopyThread;
    private Handler mPixelCopyHandler;
    private Context context;

    /**
     * ScreenCaptureHelper on platform
     *
     * @param context context of the application
     */
    public ScreenCaptureHelper(Context context) {
        this.context = context;
        if (context != null) {
            Object appContext = context.getApplicationContext();
            if (appContext instanceof Application) {
                Application app = (Application) appContext;
                app.registerActivityLifecycleCallbacks(new CurrentActivityHolder());
            }
        }
        nativeInit();
    }

    @Override
    public boolean captureScreen(String savePath, CaptureRegion region, int displayId) {
        Activity activity = getActivity();
        if (activity == null) {
            Log.e(TAG, "captureScreen: activity is null");
            return false;
        }

        int currentDisplayId = getDisplayId(activity);
        if (currentDisplayId == -1) {
            Log.e(TAG, "captureScreen: failed to get displayId");
            return false;
        }

        if (displayId != currentDisplayId) {
            Log.e(TAG, "captureScreen: displayId mismatch, requested=" + displayId + ", current=" + currentDisplayId);
            return false;
        }

        String fullPath = resolvePath(activity, savePath);
        if (fullPath == null) {
            Log.e(TAG, "captureScreen: savePath invalid: " + savePath);
            return false;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            mPixelCopyThread = new HandlerThread("UiTestPixelCopy");
            mPixelCopyThread.start();
            mPixelCopyHandler = new Handler(mPixelCopyThread.getLooper());
            Bitmap screenshotBitmap =
                captureScreenWithPixelCopy(activity, region.left, region.top, region.right, region.bottom);
            release();
            if (screenshotBitmap != null) {
                return saveBitmapToFile(screenshotBitmap, fullPath);
            } else {
                Log.e(TAG, "captureScreen: screenshot bitmap is null");
                return false;
            }
        } else {
            Log.e(TAG, "captureScreen: PixelCopy(Window) requires API level 26 or higher");
        }
        return false;
    }

    private void release() {
        if (mPixelCopyThread != null) {
            mPixelCopyThread.quitSafely();
            mPixelCopyThread = null;
        }
        mPixelCopyHandler = null;
    }

    private String resolvePath(Activity activity, String savePath) {
        if (savePath.startsWith("/cache")) {
            return activity.getCacheDir().getAbsolutePath() + savePath.substring("/cache".length());
        } else if (savePath.startsWith("/files")) {
            return activity.getFilesDir().getAbsolutePath() + savePath.substring("/files".length());
        } else {
            return null;
        }
    }

    private Activity getActivity() {
        Activity activity = CurrentActivityHolder.getCurrentActivity();
        if (activity != null) {
            return activity;
        }
        try {
            Class<?> activityThreadClass = Class.forName("android.app.ActivityThread");
            Object activityThread = activityThreadClass.getMethod("currentActivityThread").invoke(null);
            Field activitiesField = activityThreadClass.getDeclaredField("mActivities");
            activitiesField.setAccessible(true);
            Map<?, ?> activitiesMap = (Map<?, ?>) activitiesField.get(activityThread);
            if (activitiesMap == null) {
                return null;
            }
            for (Object activityClientRecord : activitiesMap.values()) {
                if (activityClientRecord == null) {
                    continue;
                }
                Class<?> activityClientRecordClass = activityClientRecord.getClass();
                Field pausedField = activityClientRecordClass.getDeclaredField("paused");
                pausedField.setAccessible(true);
                if (pausedField.getBoolean(activityClientRecord)) {
                    continue;
                }
                Field activityField = activityClientRecordClass.getDeclaredField("activity");
                activityField.setAccessible(true);
                Object activityObj = activityField.get(activityClientRecord);
                if (activityObj instanceof Activity) {
                    return (Activity) activityObj;
                }
            }
        } catch (ClassNotFoundException e) {
            Log.e(TAG, "getActivity failed: ClassNotFoundException");
        } catch (InvocationTargetException e) {
            Log.e(TAG, "getActivity failed: InvocationTargetException");
        } catch (NoSuchMethodException e) {
            Log.e(TAG, "getActivity failed: NoSuchMethodException");
        } catch (NoSuchFieldException e) {
            Log.e(TAG, "getActivity failed: NoSuchFieldException");
        } catch (IllegalAccessException e) {
            Log.e(TAG, "getActivity failed: IllegalAccessException");
        }
        return null;
    }

    private static class SurfaceRegion {
        Rect srcRect;
        Rect drawRect;
    }

    private Bitmap captureScreenWithPixelCopy(Activity activity, int left, int top, int right, int bottom) {
        Window window = activity.getWindow();
        if (window == null) {
            return null;
        }
        View decorView = window.getDecorView();
        if (decorView == null) {
            return null;
        }
        Rect captureRect = buildCaptureRegion(decorView, left, top, right, bottom);
        if (captureRect == null) {
            return null;
        }

        Bitmap resultBitmap = Bitmap.createBitmap(captureRect.width(), captureRect.height(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(resultBitmap);

        // Step 1: Capture Window surface
        captureWindow(activity.getWindow(), captureRect, canvas);

        // Step 2: Overlay each SurfaceView
        List<SurfaceView> surfaceViews = new ArrayList<>();
        collectSurfaceViews(decorView, surfaceViews);
        if (!surfaceViews.isEmpty()) {
            drawSurfaceViews(surfaceViews, captureRect, canvas);
        }
        return resultBitmap;
    }

    private Rect buildCaptureRegion(View decorView, int left, int top, int right, int bottom) {
        int width = decorView.getWidth();
        int height = decorView.getHeight();
        if (width <= 0 || height <= 0) {
            Log.e(TAG, "Invalid view dimensions: " + width + "x" + height);
            return null;
        }

        Rect boundsRect = new Rect(0, 0, width, height);
        Rect requestRect =
            new Rect(Math.max(0, left), Math.max(0, top), (right > 0) ? right : width, (bottom > 0) ? bottom : height);
        Rect captureRect = new Rect();
        if (!captureRect.setIntersect(boundsRect, requestRect)) {
            Log.e(TAG,
                "Invalid capture region: " + requestRect.left + "," + requestRect.top + "," + requestRect.right + ","
                    + requestRect.bottom);
            return null;
        }

        return captureRect;
    }

    private void captureWindow(Window window, Rect captureRect, Canvas canvas) {
        Bitmap windowBitmap = Bitmap.createBitmap(captureRect.width(), captureRect.height(), Bitmap.Config.ARGB_8888);
        final boolean[] copySuccess = {false};
        final CountDownLatch latch = new CountDownLatch(1);
        try {
            PixelCopy.request(window, captureRect, windowBitmap, (copyResult) -> {
                copySuccess[0] = (copyResult == PixelCopy.SUCCESS);
                latch.countDown();
            }, mPixelCopyHandler);
            latch.await(PIXEL_COPY_TIMEOUT_MS, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Log.e(TAG, "captureWindow: wait interrupted");
        }
        if (copySuccess[0]) {
            canvas.drawBitmap(windowBitmap, 0, 0, null);
        } else {
            Log.w(TAG, "captureWindow: PixelCopy failed");
        }
        windowBitmap.recycle();
    }

    private void collectSurfaceViews(View root, List<SurfaceView> surfaceViews) {
        if (root == null) {
            return;
        }
        if (root instanceof SurfaceView) {
            surfaceViews.add((SurfaceView) root);
        }
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) {
                collectSurfaceViews(group.getChildAt(i), surfaceViews);
            }
        }
    }

    private void drawSurfaceViews(List<SurfaceView> surfaceViews, Rect captureRect, Canvas canvas) {
        for (SurfaceView surfaceView : surfaceViews) {
            if (surfaceView.getVisibility() != View.VISIBLE || surfaceView.getWidth() <= 0
                || surfaceView.getHeight() <= 0) {
                continue;
            }
            SurfaceRegion surfaceRegion = buildSurfaceRegion(surfaceView, captureRect);
            if (surfaceRegion != null) {
                drawSingleSurface(surfaceView, surfaceRegion, canvas);
            }
        }
    }

    private SurfaceRegion buildSurfaceRegion(SurfaceView surfaceView, Rect captureRect) {
        int[] loc = new int[2];
        surfaceView.getLocationInWindow(loc);
        int left = loc[0];
        int top = loc[1];
        int right = left + surfaceView.getWidth();
        int bottom = top + surfaceView.getHeight();

        Rect surfaceRect = new Rect(left, top, right, bottom);
        Rect intersectRect = new Rect();
        if (!intersectRect.setIntersect(captureRect, surfaceRect)) {
            return null;
        }

        SurfaceRegion surfaceRegion = new SurfaceRegion();
        // Convert to SurfaceView-local coordinates for PixelCopy source rect
        surfaceRegion.srcRect = new Rect(
            intersectRect.left - left, intersectRect.top - top, intersectRect.right - left, intersectRect.bottom - top);
        // Calculate draw offset in resultBitmap
        int drawX = intersectRect.left - captureRect.left;
        int drawY = intersectRect.top - captureRect.top;
        surfaceRegion.drawRect = new Rect(drawX, drawY, drawX + intersectRect.width(), drawY + intersectRect.height());
        return surfaceRegion;
    }

    private void drawSingleSurface(SurfaceView surfaceView, SurfaceRegion surfaceRegion, Canvas canvas) {
        Bitmap surfaceBitmap = Bitmap.createBitmap(
            surfaceRegion.drawRect.width(), surfaceRegion.drawRect.height(), Bitmap.Config.ARGB_8888);
        final boolean[] copySuccess = {false};
        final CountDownLatch latch = new CountDownLatch(1);
        try {
            PixelCopy.request(surfaceView, surfaceRegion.srcRect, surfaceBitmap, (copyResult) -> {
                copySuccess[0] = (copyResult == PixelCopy.SUCCESS);
                latch.countDown();
            }, mPixelCopyHandler);
            latch.await(PIXEL_COPY_TIMEOUT_MS, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Log.e(TAG, "drawSingleSurface: wait interrupted");
        }
        if (copySuccess[0]) {
            canvas.drawBitmap(surfaceBitmap, surfaceRegion.drawRect.left, surfaceRegion.drawRect.top, null);
        } else {
            Log.w(TAG, "drawSingleSurface: PixelCopy failed for " + surfaceView.getClass().getSimpleName());
        }
        surfaceBitmap.recycle();
    }

    private boolean saveBitmapToFile(Bitmap bitmap, String savePath) {
        File file = new File(savePath);
        File parentDir = file.getParentFile();
        if (parentDir != null && !parentDir.exists() && !parentDir.mkdirs()) {
            Log.e(TAG, "saveBitmapToFile: create parent directory failed");
            return false;
        }
        try (FileOutputStream fos = new FileOutputStream(file)) {
            boolean isSuccess = bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos);
            if (isSuccess) {
                fos.flush();
                return true;
            } else {
                Log.e(TAG, "saveBitmapToFile: bitmap compress failed");
                return false;
            }
        } catch (IOException e) {
            Log.e(TAG, "saveBitmapToFile: save failed", e);
            return false;
        }
    }

    private int getDisplayId(Activity activity) {
        if (activity == null) {
            return -1;
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.JELLY_BEAN_MR1) {
            return 0;
        }
        Window window = activity.getWindow();
        if (window == null) {
            return -1;
        }
        View decorView = window.getDecorView();
        if (decorView == null) {
            return -1;
        }
        Display display = decorView.getDisplay();
        if (display == null) {
            return -1;
        }
        return display.getDisplayId();
    }
}
