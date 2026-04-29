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

/**
 * ScreenCaptureHelperBase
 *
 * @since 1
 */
public abstract class ScreenCaptureHelperBase {

    /**
     * CaptureRegion defines the region to be captured on the screen
     */
    public static class CaptureRegion {

        /**
         * left: the left coordinate of the capture region
         */
        public final int left;

        /**
         * top: the top coordinate of the capture region
         */
        public final int top;

        /**
         * right: the right coordinate of the capture region
         */
        public final int right;

        /**
         * bottom: the bottom coordinate of the capture region
         */
        public final int bottom;

        /**
         * Constructor for CaptureRegion
         *
         * @param left the left coordinate of the capture region
         * @param top the top coordinate of the capture region
         * @param right the right coordinate of the capture region
         * @param bottom the bottom coordinate of the capture region
         */
        public CaptureRegion(int left, int top, int right, int bottom) {
            this.left = left;
            this.top = top;
            this.right = right;
            this.bottom = bottom;
        }
    }

    /**
     * captureScreen
     *
     * @param savePath the path to save the captured screen
     * @param region the region to capture
     * @param displayId the ID of the display to capture
     * @return true if the screen was successfully captured, false otherwise
     * @since 1
     */
    public abstract boolean captureScreen(String savePath, CaptureRegion region, int displayId);

    /**
     * Initialize screencapture plugin
     */
    protected native void nativeInit();
}
