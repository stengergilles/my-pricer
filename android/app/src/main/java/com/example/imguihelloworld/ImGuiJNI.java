package com.example.imguihelloworld;

import android.util.Log;

/**
 * JNI interface for ImGui
 */
public class ImGuiJNI {
    private static final String TAG = "ImGuiJNI";
    
    // Load the native library
    static {
        try {
            System.loadLibrary("imgui_hello_world");
            Log.d(TAG, "Native library imgui_hello_world loaded successfully");
        } catch (UnsatisfiedLinkError e) {
            Log.e(TAG, "Failed to load native library imgui_hello_world: " + e.getMessage());
        }
    }
    
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
