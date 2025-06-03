package com.example.imguihelloworld;

import android.os.Bundle;
import android.view.KeyEvent;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.view.View;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

/**
 * Main activity for the ImGui Hello World application.
 * This extends our custom ImGuiKeyboardHelper which provides better keyboard support.
 */
public class MainActivity extends ImGuiKeyboardHelper {
    
    private static final String TAG = "MainActivity";
    
    // Static instance for access from native code via JNI
    public static MainActivity instance;
    
    // Handler for delayed tasks
    private Handler mHandler = new Handler(Looper.getMainLooper());
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Store instance for JNI access
        instance = this;
        
        Log.d(TAG, "MainActivity created");
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        
        // Store instance for JNI access (in case it was lost)
        instance = this;
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        
        // Clear static instance if this instance is being destroyed
        if (instance == this) {
            instance = null;
        }
    }
    
    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event) {
        // Handle back button
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            // Let the native code handle it first using ImGuiJNI
            ImGuiJNI.onKeyEvent(keyCode, KeyEvent.ACTION_UP, event.getMetaState());
            
            // If we're still here, handle it normally
            return super.onKeyUp(keyCode, event);
        }
        
        return super.onKeyUp(keyCode, event);
    }
    
    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // Pass all key events to ImGui
        int action = event.getAction();
        int keyCode = event.getKeyCode();
        
        // Handle special keys
        if (keyCode == KeyEvent.KEYCODE_VOLUME_UP || 
            keyCode == KeyEvent.KEYCODE_VOLUME_DOWN ||
            keyCode == KeyEvent.KEYCODE_VOLUME_MUTE) {
            return super.dispatchKeyEvent(event);
        }
        
        // For text input, handle it specially
        if (action == KeyEvent.ACTION_MULTIPLE && keyCode == KeyEvent.KEYCODE_UNKNOWN) {
            String characters = event.getCharacters();
            if (characters != null && !characters.isEmpty()) {
                ImGuiJNI.onTextInput(characters);
                return true;
            }
        }
        
        // For normal keys, pass to the native code
        if (action == KeyEvent.ACTION_DOWN || action == KeyEvent.ACTION_UP) {
            ImGuiJNI.onKeyEvent(keyCode, action, event.getMetaState());
            return true;
        }
        
        return super.dispatchKeyEvent(event);
    }
    
    // Override the showSoftKeyboard method to add more logging
    @Override
    public void showSoftKeyboard() {
        Log.d(TAG, "MainActivity.showSoftKeyboard called");
        
        // Always show keyboard when requested from native code
        try {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                View view = getWindow().getDecorView().getRootView();
                
                // Force the keyboard to show with SHOW_FORCED flag
                imm.showSoftInput(view, InputMethodManager.SHOW_FORCED);
                
                // Try alternative methods if needed
                view.requestFocus();
                imm.toggleSoftInput(InputMethodManager.SHOW_FORCED, 0);
                
                Log.d(TAG, "Keyboard show requested with multiple methods");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error showing keyboard: " + e.getMessage());
        }
    }
    
    /**
     * Static method to show the keyboard - called from native code via JNI
     */
    public static void showKeyboard() {
        Log.d(TAG, "Static showKeyboard called from JNI");
        if (instance != null) {
            // Run on UI thread to avoid crashes
            instance.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Log.d(TAG, "Showing keyboard on UI thread");
                        InputMethodManager imm = (InputMethodManager) instance.getSystemService(Context.INPUT_METHOD_SERVICE);
                        if (imm != null) {
                            View view = instance.getWindow().getDecorView().getRootView();
                            
                            // Try multiple approaches to ensure keyboard shows
                            view.requestFocus();
                            
                            // Method 1: Direct show
                            imm.showSoftInput(view, InputMethodManager.SHOW_FORCED);
                            
                            // Method 2: Toggle
                            imm.toggleSoftInput(InputMethodManager.SHOW_FORCED, 0);
                            
                            // Method 3: Show with flags
                            imm.showSoftInput(view, InputMethodManager.SHOW_IMPLICIT | 
                                                  InputMethodManager.SHOW_FORCED);
                            
                            Log.d(TAG, "All keyboard show methods attempted");
                        } else {
                            Log.e(TAG, "InputMethodManager is null");
                        }
                    } catch (Exception e) {
                        Log.e(TAG, "Error showing keyboard: " + e.getMessage(), e);
                    }
                }
            });
        } else {
            Log.e(TAG, "Cannot show keyboard - instance is null");
        }
    }
}
