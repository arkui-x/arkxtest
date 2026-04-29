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

package ohos.ace.plugin.display;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.content.pm.ActivityInfo;
import android.util.Log;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.util.Map;

import ohos.ace.plugin.display.CurrentActivityHolder;

/**
 * DisplayPlatform
 *
 * @since 1
 */
public class DisplayPlatform {
    private static final String LOG_TAG = "DisplayPlatform";
    private static final int ROTATION_0 = 0;
    private static final int ROTATION_90 = 1;
    private static final int ROTATION_180 = 2;
    private static final int ROTATION_270 = 3;

    private Context context;

    /**
     * DisplayPlatform on platform
     *
     * @param context context of the application
     */
    public DisplayPlatform(Context context) {
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

    /**
     * Sets the display rotation to the specified value.
     *
     * @param rotation The rotation value to set.
     */
    public void setDisplayRotation(int rotation) {
        Activity activity = getActivity();
        if (activity == null) {
            Log.e(LOG_TAG, "setDisplayRotation: activity is null");
            return;
        }
        switch (rotation) {
            case ROTATION_0:
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
                break;
            case ROTATION_90:
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_REVERSE_LANDSCAPE);
                break;
            case ROTATION_180:
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT);
                break;
            case ROTATION_270:
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
                break;
            default:
                return;
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
            Log.e(LOG_TAG, "getActivity failed: ClassNotFoundException");
        } catch (InvocationTargetException e) {
            Log.e(LOG_TAG, "getActivity failed: InvocationTargetException");
        } catch (NoSuchMethodException e) {
            Log.e(LOG_TAG, "getActivity failed: NoSuchMethodException");
        } catch (NoSuchFieldException e) {
            Log.e(LOG_TAG, "getActivity failed: NoSuchFieldException");
        } catch (IllegalAccessException e) {
            Log.e(LOG_TAG, "getActivity failed: IllegalAccessException");
        }
        return null;
    }

    private native void nativeInit();
}
