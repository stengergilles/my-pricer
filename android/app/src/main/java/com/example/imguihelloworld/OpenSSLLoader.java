package com.example.imguihelloworld;

import android.content.Context;
import android.util.Log;

/**
 * Helper class to load OpenSSL native libraries
 */
public class OpenSSLLoader {
    private static final String TAG = "OpenSSLLoader";
    private static boolean isLoaded = false;
    
    /**
     * Load the OpenSSL native libraries
     * @param context Android context
     * @return true if libraries were loaded successfully
     */
    public static synchronized boolean loadOpenSSL(Context context) {
        if (isLoaded) {
            Log.d(TAG, "OpenSSL already loaded");
            return true;
        }
        
        try {
            // Load the OpenSSL library
            System.loadLibrary("crypto");
            System.loadLibrary("ssl");
            
            Log.i(TAG, "Successfully loaded OpenSSL 3.0.4 libraries");
            isLoaded = true;
            return true;
        } catch (UnsatisfiedLinkError e) {
            Log.e(TAG, "Failed to load OpenSSL libraries: " + e.getMessage(), e);
            return false;
        }
    }
    
    /**
     * Check if OpenSSL is loaded
     * @return true if OpenSSL is loaded
     */
    public static boolean isOpenSSLLoaded() {
        return isLoaded;
    }
    
    /**
     * Get the OpenSSL version (requires JNI implementation)
     * @return OpenSSL version string
     */
    public static native String getOpenSSLVersion();
}
