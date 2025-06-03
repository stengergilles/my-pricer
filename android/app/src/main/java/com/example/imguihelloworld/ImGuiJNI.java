package com.example.imguihelloworld;

import android.util.Log;

/**
 * JNI interface for ImGui
 */
public class ImGuiJNI {
    private static final String TAG = "ImGuiJNI";
    
    // Native methods
    public static native void onKeyEvent(int keyCode, int action, int metaState);
    public static native void onTextInput(String text);
    public static native boolean wantsTextInput();
    
    // Helper method to log and forward text input
    public static void sendTextInput(String text) {
        Log.d(TAG, "Sending text input: " + text);
        onTextInput(text);
    }
}
