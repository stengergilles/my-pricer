package com.example.imguihelloworld;

/**
 * JNI interface for ImGui on Android.
 * This class provides static methods to communicate with the native ImGui code.
 */
public class ImGuiJNI {
    
    // Load the native library
    static {
        System.loadLibrary("imgui_hello_world");
    }
    
    /**
     * Pass a key event to the native ImGui code
     * @param keyCode The Android key code
     * @param action The key action (0 = down, 1 = up)
     * @param metaState The meta state (shift, ctrl, etc.)
     */
    public static native void onKeyEvent(int keyCode, int action, int metaState);
    
    /**
     * Pass text input to the native ImGui code
     * @param text The text to input
     */
    public static native void onTextInput(String text);
    
    /**
     * Check if ImGui wants text input (has an active input field)
     * @return true if ImGui wants text input
     */
    public static native boolean wantsTextInput();
    
    /**
     * Show the keyboard from native code
     */
    public static void showKeyboard() {
        // This will be called from Java code
        if (MainActivity.instance != null) {
            MainActivity.instance.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    MainActivity.instance.showSoftKeyboard();
                }
            });
        }
    }
}
