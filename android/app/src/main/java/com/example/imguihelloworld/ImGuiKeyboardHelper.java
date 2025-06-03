package com.example.imguihelloworld;

import android.app.NativeActivity;
import android.content.Context;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.util.Log;

/**
 * Helper class to handle keyboard input for ImGui on Android.
 * This class extends NativeActivity to provide better keyboard support.
 */
public class ImGuiKeyboardHelper extends NativeActivity {
    
    private static final String TAG = "ImGuiKeyboardHelper";
    
    // Native methods to pass keyboard events to the native code
    private native void nativeOnKeyDown(int keyCode, int metaState);
    private native void nativeOnKeyUp(int keyCode, int metaState);
    private native void nativeOnKeyMultiple(int keyCode, int count, KeyEvent event);
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Set up keyboard visibility listener
        final View decorView = getWindow().getDecorView();
        decorView.setOnSystemUiVisibilityChangeListener(
            new View.OnSystemUiVisibilityChangeListener() {
                @Override
                public void onSystemUiVisibilityChange(int visibility) {
                    if ((visibility & View.SYSTEM_UI_FLAG_FULLSCREEN) == 0) {
                        // The system bars are visible, show keyboard if needed
                        showSoftKeyboard();
                    }
                }
            }
        );
        
        // Force the window to be focusable so the keyboard can show up
        decorView.setFocusable(true);
        decorView.setFocusableInTouchMode(true);
    }
    
    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // First, let the native activity handle the event
        if (super.dispatchKeyEvent(event)) {
            return true;
        }
        
        // If not handled, process it ourselves
        int action = event.getAction();
        int keyCode = event.getKeyCode();
        int metaState = event.getMetaState();
        
        Log.d(TAG, "dispatchKeyEvent: keyCode=" + keyCode + ", action=" + action);
        
        switch (action) {
            case KeyEvent.ACTION_DOWN:
                nativeOnKeyDown(keyCode, metaState);
                
                // For character keys, also send the character
                int unicodeChar = event.getUnicodeChar();
                if (unicodeChar != 0) {
                    String charStr = String.valueOf((char)unicodeChar);
                    Log.d(TAG, "Sending unicode character: " + charStr + " (code: " + unicodeChar + ")");
                    
                    // Send to ImGuiJNI
                    ImGuiJNI.onTextInput(charStr);
                }
                
                return true;
                
            case KeyEvent.ACTION_UP:
                nativeOnKeyUp(keyCode, metaState);
                return true;
                
            case KeyEvent.ACTION_MULTIPLE:
                nativeOnKeyMultiple(keyCode, event.getRepeatCount(), event);
                return true;
        }
        
        return false;
    }
    
    /**
     * Show the soft keyboard
     */
    public void showSoftKeyboard() {
        Log.d(TAG, "Showing soft keyboard");
        try {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                // Force the keyboard to show
                View view = getWindow().getDecorView();
                view.requestFocus();
                
                // Try multiple methods to ensure keyboard shows
                imm.showSoftInput(view, InputMethodManager.SHOW_FORCED);
                imm.toggleSoftInput(InputMethodManager.SHOW_FORCED, 0);
                
                Log.d(TAG, "Keyboard show methods called");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error showing keyboard: " + e.getMessage());
        }
    }
    
    /**
     * Hide the soft keyboard
     */
    public void hideSoftKeyboard() {
        Log.d(TAG, "Hiding soft keyboard");
        try {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                View view = getWindow().getDecorView();
                imm.hideSoftInputFromWindow(view.getWindowToken(), 0);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error hiding keyboard: " + e.getMessage());
        }
    }
    
    /**
     * Toggle the soft keyboard visibility
     */
    public void toggleSoftKeyboard() {
        Log.d(TAG, "Toggling soft keyboard");
        try {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                imm.toggleSoftInput(InputMethodManager.SHOW_FORCED, 0);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error toggling keyboard: " + e.getMessage());
        }
    }
}
