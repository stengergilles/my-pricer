package com.example.imguihelloworld;

/**
 * JNI interface for ImGui Android application.
 * This class provides native method declarations and handles loading the native library.
 */
public class ImGuiJNI {
    // Load the native library
    static {
        System.loadLibrary("imgui_hello_world");
    }
    
    // Native methods that will be implemented in C++
    public static native void onKeyEvent(int keyCode, int action, int metaState);
    public static native void onTextInput(String text);
    
    // Method to convert Android key codes to ImGui key codes
    public static int convertKeyCode(int androidKeyCode) {
        // This would be implemented in the native code
        return androidKeyCode;
    }
}
