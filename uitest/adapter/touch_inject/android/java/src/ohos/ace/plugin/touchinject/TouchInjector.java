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

package ohos.ace.plugin.touchinject;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.util.Log;
import android.view.InputDevice;
import android.view.MotionEvent;
import android.view.MotionEvent.PointerCoords;
import android.view.MotionEvent.PointerProperties;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import ohos.ace.plugin.touchinject.CurrentActivityHolder;

/**
 * TouchInjector
 *
 * @since 1
 */
public class TouchInjector extends TouchInjectorBase {
    private static final String TAG = "TouchInjector";
    private static final long UI_DISPATCH_TIMEOUT_MS = 200L;

    /**
     * TouchInjector on platform
     *
     * @param context context of the application
     */
    public TouchInjector(Context context) {
        if (context != null) {
            Object appContext = context.getApplicationContext();
            if (appContext instanceof Application) {
                Application app = (Application) appContext;
                app.registerActivityLifecycleCallbacks(new CurrentActivityHolder());
            }
        }
        nativeInit();
    }

    /**
     * Encapsulates touch event parameters
     */
    public static class TouchEventParam {

        /**
         * action: MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE, MotionEvent.ACTION_UP
         */
        public final int action;

        /**
         * x：x position of the touch event
         */
        public final float x;

        /**
         * y：y position of the touch event
         */
        public final float y;

        /**
         * downTime: The time (in ms) when the touch event started
         */
        public final long downTime;

        /**
         * eventTime: The time (in ms) when the touch event occurred
         */
        public final long eventTime;

        /**
         * deviceId: The ID of the input device that generated the touch event
         */
        public final int deviceId;

        /**
         * Constructor for TouchEventParam
         *
         * @param action action: MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE, MotionEvent.ACTION_UP
         * @param x x position of the touch event
         * @param y y position of the touch event
         * @param downTime The time (in ms) when the touch event started
         * @param eventTime The time (in ms) when the touch event occurred
         * @param deviceId The ID of the input device that generated the touch event
         * @return TouchEventParam object
         */
        public TouchEventParam(int action, float x, float y, long downTime, long eventTime, int deviceId) {
            this.action = action;
            this.x = x;
            this.y = y;
            this.downTime = downTime;
            this.eventTime = eventTime;
            this.deviceId = deviceId;
        }
    }

    private int getTouchDeviceId() {
        try {
            int[] deviceIds = InputDevice.getDeviceIds();
            for (int deviceId : deviceIds) {
                InputDevice device = InputDevice.getDevice(deviceId);
                if (device != null && (device.getSources() & InputDevice.SOURCE_TOUCHSCREEN) != 0) {
                    return deviceId;
                }
            }
        } catch (SecurityException e) {
            Log.e(TAG, "getTouchDeviceId: SecurityException");
        }
        return -1;
    }

    /**
     * create MotionEvent object based on TouchEventParam
     *
     * @param param TouchEventParam object containing touch event parameters
     * @return MotionEvent object
     */
    public static MotionEvent makeMotionEvent(TouchEventParam param) {
        PointerProperties[] properties = new PointerProperties[1];
        properties[0] = new PointerProperties();
        properties[0].id = 0;
        properties[0].toolType = MotionEvent.TOOL_TYPE_FINGER;

        PointerCoords[] coords = new PointerCoords[1];
        coords[0] = new PointerCoords();
        coords[0].x = param.x;
        coords[0].y = param.y;
        coords[0].pressure = 1.0f;
        coords[0].size = 1.0f;

        return MotionEvent.obtain(param.downTime, param.eventTime, param.action, 1, properties, coords, 0, 0, 1.0f,
            1.0f, param.deviceId, 0, InputDevice.SOURCE_TOUCHSCREEN, 0);
    }

    @Override
    public boolean injectTouchEvent(int action, float x, float y, long downTime, long eventTime) {
        try {
            Activity activity = getActivity();
            if (activity == null) {
                Log.e(TAG, "injectTouchEvent: no active Activity found");
                return false;
            }

            View decorView = activity.getWindow().getDecorView();
            if (decorView == null) {
                Log.e(TAG, "injectTouchEvent: decorView is null");
                return false;
            }

            List<SurfaceView> surfaceViews = new ArrayList<>();
            collectSurfaceViews(decorView, surfaceViews);
            int deviceId = getTouchDeviceId();
            TouchEventParam param = new TouchEventParam(action, x, y, downTime, eventTime, deviceId);
            dispatchTouchToSurfaceViews(surfaceViews, param);
            return true;
        } catch (SecurityException e) {
            Log.e(TAG, "injectTouchEvent: SecurityException");
            return false;
        } catch (IllegalArgumentException e) {
            Log.e(TAG, "injectTouchEvent: IllegalArgumentException");
            return false;
        }
    }

    private void dispatchTouchToSurfaceViews(List<SurfaceView> surfaceViews, TouchEventParam param) {
        if (surfaceViews == null || surfaceViews.isEmpty()) {
            return;
        }
        for (SurfaceView sv : surfaceViews) {
            sv.post(() -> {
                MotionEvent event = makeMotionEvent(param);
                event.setSource(android.view.InputDevice.SOURCE_TOUCHSCREEN);
                sv.dispatchTouchEvent(event);
                event.recycle();
            });
        }
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
}
