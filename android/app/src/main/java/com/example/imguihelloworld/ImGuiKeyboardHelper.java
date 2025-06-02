package com.example.imguihelloworld;

import android.app.NativeActivity;
import android.content.Context;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.InputMethodManager;

/**
 * Helper class to handle keyboard input for ImGui on Android.
 * This class extends NativeActivity to provide better keyboard support.
 */
public class ImGuiKeyboardHelper extends NativeActivity {
    
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
        
        switch (action) {
            case KeyEvent.ACTION_DOWN:
                nativeOnKeyDown(keyCode, metaState);
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
        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.showSoftInput(getWindow().getDecorView(), InputMethodManager.SHOW_IMPLICIT);
        }
    }
    
    /**
     * Hide the soft keyboard
     */
    public void hideSoftKeyboard() {
        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.hideSoftInputFromWindow(getWindow().getDecorView().getWindowToken(), 0);
        }
    }
    
    /**
     * Toggle the soft keyboard visibility
     */
    public void toggleSoftKeyboard() {
        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.toggleSoftInput(InputMethodManager.SHOW_FORCED, 0);
        }
    }
}
