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
    
    // Flag to track keyboard visibility
    private boolean mKeyboardVisible = false;
    
    // EditText for capturing input
    private android.widget.EditText mInputEditText = null;
    
    // Native method to check if ImGui wants text input
    private native boolean nativeWantsTextInput();
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Store instance for JNI access
        instance = this;
        
        Log.d(TAG, "MainActivity created");
        
        // Start a periodic check for keyboard visibility
        startKeyboardVisibilityCheck();
        
        // Set up an EditText to capture text input
        setupInputCapture();
    }
    
    /**
     * Set up an invisible EditText to capture text input
     */
    private void setupInputCapture() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    // Create a new EditText that will capture input
                    final android.widget.EditText editText = new android.widget.EditText(MainActivity.this);
                    editText.setVisibility(View.INVISIBLE);
                    editText.setWidth(1);
                    editText.setHeight(1);
                    
                    // Add it to the layout
                    android.widget.FrameLayout layout = new android.widget.FrameLayout(MainActivity.this);
                    layout.addView(editText);
                    addContentView(layout, new android.view.ViewGroup.LayoutParams(
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT));
                    
                    // Set up a text watcher to capture input
                    editText.addTextChangedListener(new android.text.TextWatcher() {
                        @Override
                        public void beforeTextChanged(CharSequence s, int start, int count, int after) {
                            // Not used
                        }
                        
                        @Override
                        public void onTextChanged(CharSequence s, int start, int before, int count) {
                            if (count > 0) {
                                String newText = s.subSequence(start, start + count).toString();
                                Log.d(TAG, "Text changed: " + newText);
                                ImGuiJNI.onTextInput(newText);
                            }
                        }
                        
                        @Override
                        public void afterTextChanged(android.text.Editable s) {
                            // Clear the text so we only get the delta
                            s.clear();
                        }
                    });
                    
                    // Store the EditText for later use
                    mInputEditText = editText;
                    
                    Log.d(TAG, "Input capture setup complete");
                } catch (Exception e) {
                    Log.e(TAG, "Error setting up input capture: " + e.getMessage(), e);
                }
            }
        });
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
                Log.d(TAG, "Sending text input to ImGui: " + characters);
                ImGuiJNI.onTextInput(characters);
                return true;
            }
        }
        
        // For normal keys, pass to the native code
        if (action == KeyEvent.ACTION_DOWN || action == KeyEvent.ACTION_UP) {
            Log.d(TAG, "Sending key event to ImGui: " + keyCode + ", action: " + action);
            ImGuiJNI.onKeyEvent(keyCode, action, event.getMetaState());
            
            // For character keys, also send the character
            if (action == KeyEvent.ACTION_DOWN && keyCode >= KeyEvent.KEYCODE_A && keyCode <= KeyEvent.KEYCODE_Z) {
                char c = (char) ('a' + (keyCode - KeyEvent.KEYCODE_A));
                if (event.isShiftPressed()) {
                    c = Character.toUpperCase(c);
                }
                String charStr = String.valueOf(c);
                Log.d(TAG, "Sending character to ImGui: " + charStr);
                ImGuiJNI.onTextInput(charStr);
            } else if (action == KeyEvent.ACTION_DOWN && keyCode >= KeyEvent.KEYCODE_0 && keyCode <= KeyEvent.KEYCODE_9) {
                char c = (char) ('0' + (keyCode - KeyEvent.KEYCODE_0));
                String charStr = String.valueOf(c);
                Log.d(TAG, "Sending character to ImGui: " + charStr);
                ImGuiJNI.onTextInput(charStr);
            } else if (action == KeyEvent.ACTION_DOWN) {
                // Handle special characters
                char c = 0;
                switch (keyCode) {
                    case KeyEvent.KEYCODE_SPACE: c = ' '; break;
                    case KeyEvent.KEYCODE_PERIOD: c = '.'; break;
                    case KeyEvent.KEYCODE_COMMA: c = ','; break;
                    case KeyEvent.KEYCODE_SLASH: c = '/'; break;
                    case KeyEvent.KEYCODE_BACKSLASH: c = '\\'; break;
                    case KeyEvent.KEYCODE_SEMICOLON: c = ';'; break;
                    case KeyEvent.KEYCODE_APOSTROPHE: c = '\''; break;
                    case KeyEvent.KEYCODE_MINUS: c = '-'; break;
                    case KeyEvent.KEYCODE_EQUALS: c = '='; break;
                    case KeyEvent.KEYCODE_LEFT_BRACKET: c = '['; break;
                    case KeyEvent.KEYCODE_RIGHT_BRACKET: c = ']'; break;
                    case KeyEvent.KEYCODE_GRAVE: c = '`'; break;
                }
                
                if (c != 0) {
                    String charStr = String.valueOf(c);
                    Log.d(TAG, "Sending special character to ImGui: " + charStr);
                    ImGuiJNI.onTextInput(charStr);
                }
            }
            
            return true;
        }
        
        return super.dispatchKeyEvent(event);
    }
    
    /**
     * Start a periodic check for keyboard visibility based on ImGui's WantTextInput flag
     */
    private void startKeyboardVisibilityCheck() {
        mHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                try {
                    // Check if ImGui wants text input
                    boolean wantsTextInput = ImGuiJNI.wantsTextInput();
                    Log.d(TAG, "ImGui WantTextInput: " + wantsTextInput + ", Keyboard visible: " + mKeyboardVisible);
                    
                    // Show or hide keyboard based on ImGui's WantTextInput flag
                    if (wantsTextInput && !mKeyboardVisible) {
                        showKeyboard();
                    } else if (!wantsTextInput && mKeyboardVisible) {
                        hideKeyboard();
                    }
                    
                    // Continue checking
                    mHandler.postDelayed(this, 500); // Check every 500ms
                } catch (Exception e) {
                    Log.e(TAG, "Error in keyboard visibility check: " + e.getMessage(), e);
                }
            }
        }, 1000); // Start after 1 second
    }
    
    /**
     * Static method to show the keyboard - called from native code via JNI
     */
    public static void showKeyboard() {
        Log.d(TAG, "Static showKeyboard called");
        if (instance != null) {
            // Run on UI thread to avoid crashes
            instance.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Log.d(TAG, "Showing keyboard on UI thread");
                        
                        // Focus the input EditText if available
                        if (instance.mInputEditText != null) {
                            instance.mInputEditText.requestFocus();
                            
                            InputMethodManager imm = (InputMethodManager) instance.getSystemService(Context.INPUT_METHOD_SERVICE);
                            if (imm != null) {
                                // Show keyboard for the EditText
                                imm.showSoftInput(instance.mInputEditText, InputMethodManager.SHOW_FORCED);
                                
                                // Update visibility flag
                                instance.mKeyboardVisible = true;
                                
                                Log.d(TAG, "Keyboard shown for EditText");
                            }
                        } else {
                            // Fallback to showing keyboard for the main view
                            InputMethodManager imm = (InputMethodManager) instance.getSystemService(Context.INPUT_METHOD_SERVICE);
                            if (imm != null) {
                                View view = instance.getWindow().getDecorView().getRootView();
                                view.requestFocus();
                                imm.showSoftInput(view, InputMethodManager.SHOW_FORCED);
                                imm.toggleSoftInput(InputMethodManager.SHOW_FORCED, 0);
                                
                                // Update visibility flag
                                instance.mKeyboardVisible = true;
                                
                                Log.d(TAG, "Keyboard shown for main view (fallback)");
                            } else {
                                Log.e(TAG, "InputMethodManager is null");
                            }
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
    
    /**
     * Static method to hide the keyboard - called from native code via JNI
     */
    public static void hideKeyboard() {
        Log.d(TAG, "Static hideKeyboard called");
        if (instance != null) {
            // Run on UI thread to avoid crashes
            instance.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Log.d(TAG, "Hiding keyboard on UI thread");
                        InputMethodManager imm = (InputMethodManager) instance.getSystemService(Context.INPUT_METHOD_SERVICE);
                        if (imm != null) {
                            // If we have an EditText, hide keyboard for it
                            if (instance.mInputEditText != null) {
                                imm.hideSoftInputFromWindow(instance.mInputEditText.getWindowToken(), 0);
                            } else {
                                // Fallback to hiding keyboard for the main view
                                View view = instance.getWindow().getDecorView().getRootView();
                                imm.hideSoftInputFromWindow(view.getWindowToken(), 0);
                            }
                            
                            // Update visibility flag
                            instance.mKeyboardVisible = false;
                            
                            Log.d(TAG, "Keyboard hide attempted");
                        } else {
                            Log.e(TAG, "InputMethodManager is null");
                        }
                    } catch (Exception e) {
                        Log.e(TAG, "Error hiding keyboard: " + e.getMessage(), e);
                    }
                }
            });
        } else {
            Log.e(TAG, "Cannot hide keyboard - instance is null");
        }
    }
}
