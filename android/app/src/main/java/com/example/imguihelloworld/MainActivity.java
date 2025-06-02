package com.example.imguihelloworld;

import android.os.Bundle;
import android.view.KeyEvent;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.view.View;

/**
 * Main activity for the ImGui Hello World application.
 * This extends our custom ImGuiKeyboardHelper which provides better keyboard support.
 */
public class MainActivity extends ImGuiKeyboardHelper {
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Set up a long click listener to toggle the keyboard
        getWindow().getDecorView().setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                toggleSoftKeyboard();
                return true;
            }
        });
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
}
