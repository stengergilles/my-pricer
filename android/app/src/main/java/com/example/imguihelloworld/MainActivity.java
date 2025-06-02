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
        
        // Set up a tap listener to show keyboard
        getWindow().getDecorView().setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Log.d(TAG, "View clicked, showing keyboard");
                showSoftKeyboard();
            }
        });
        
        // Show keyboard after a short delay
        mHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                Log.d(TAG, "Initial keyboard show attempt");
                showSoftKeyboard();
            }
        }, 1000); // 1 second delay
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        
        // Store instance for JNI access (in case it was lost)
        instance = this;
        
        // Show keyboard when app resumes
        mHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                Log.d(TAG, "onResume keyboard show attempt");
                showSoftKeyboard();
            }
        }, 500); // 0.5 second delay
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
        super.showSoftKeyboard();
        
        // Try an alternative method if the first one doesn't work
        try {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                View view = getWindow().getDecorView().getRootView();
                imm.showSoftInput(view, InputMethodManager.SHOW_IMPLICIT);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error in alternative keyboard show: " + e.getMessage());
        }
    }
}
