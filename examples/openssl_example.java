package com.example.imguihelloworld;

import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;

/**
 * Example activity demonstrating OpenSSL integration
 */
public class OpenSSLExampleActivity extends MainActivity {
    private static final String TAG = "OpenSSLExample";
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Load OpenSSL
        boolean loaded = OpenSSLLoader.loadOpenSSL(this);
        Log.i(TAG, "OpenSSL loaded: " + loaded);
        
        if (loaded) {
            // Get OpenSSL version
            String version = ImGuiJNI.getOpenSSLVersionFromNative();
            Log.i(TAG, "OpenSSL version: " + version);
            
            // Display version in a TextView (if you want to show it in UI)
            TextView textView = new TextView(this);
            textView.setText("OpenSSL version: " + version);
            setContentView(textView);
        }
    }
}
