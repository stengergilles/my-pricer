package com.example.imguihelloworld;

import android.util.Log;

/**
 * JNI interface for Python integration
 */
public class ImGuiPythonBridge {
    private static final String TAG = "ImGuiPythonBridge";
    
    // Load the native library (already loaded by ImGuiJNI)
    
    // Native methods
    public static native boolean initializePythonBridge();
    public static native int createTickerMonitor(String ticker, float entryPrice, String scope, float leverage, float stopLoss);
    public static native boolean stopTickerMonitor(int monitorId);
    public static native String getNextMessage();
    public static native String waitForMessage(int timeoutMs);
    public static native void cleanupPythonBridge();
    
    // Helper methods
    public static int startMonitoring(String ticker, float entryPrice) {
        return startMonitoring(ticker, entryPrice, "intraday", 1.0f, 0.05f);
    }
    
    public static int startMonitoring(String ticker, float entryPrice, String scope, float leverage, float stopLoss) {
        Log.d(TAG, "Starting monitoring for " + ticker + " with entry price " + entryPrice);
        int monitorId = createTickerMonitor(ticker, entryPrice, scope, leverage, stopLoss);
        if (monitorId >= 0) {
            Log.d(TAG, "Monitor created with ID: " + monitorId);
        } else {
            Log.e(TAG, "Failed to create monitor for " + ticker);
        }
        return monitorId;
    }
}
