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

/**
 * TouchInjectorBase
 *
 * @since 1
 */
public abstract class TouchInjectorBase {
    /**
     * injectTouchEvent
     *
     * @param action the action of the touch event
     * @param x the x coordinate of the touch event
     * @param y the y coordinate of the touch event
     * @param downTime the time when the touch event started, in milliseconds
     * @param eventTime the time when the touch event occurred, in milliseconds
     * @return true if the touch event was successfully injected, false otherwise
     * @since 1
     */
    public abstract boolean injectTouchEvent(int action, float x, float y, long downTime, long eventTime);

    /**
     * Initialize touchinjector plugin
     */
    protected native void nativeInit();
}
