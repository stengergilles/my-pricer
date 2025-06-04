package com.example.imguihelloworld;

/**
 * JNI interface for ImGui native functions
 */
public class ImGuiJNI {
    // Load the native library
    static {
        System.loadLibrary("imgui_hello_world");
    }
    
    // Native methods
    public static native void onKeyEvent(int keyCode, int action, int metaState);
    public static native void onTextInput(String text);
    public static native boolean wantsTextInput();
    
    // OpenSSL integration
    public static native String getOpenSSLVersionFromNative();
}
