#include <jni.h>
#include <android/log.h>
#include "../../include/python_bridge.h"

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "ImGuiPythonBridge", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "ImGuiPythonBridge", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "ImGuiPythonBridge", __VA_ARGS__))

extern "C" {

JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_initializePythonBridge(JNIEnv *env, jclass clazz) {
    LOGI("Initializing Python bridge");
    bool result = pythonBridgeInitialize();
    if (result) {
        LOGI("Python bridge initialized successfully");
    } else {
        LOGE("Failed to initialize Python bridge");
    }
    return result ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jint JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_createTickerMonitor(JNIEnv *env, jclass clazz, 
                                                                      jstring ticker, jfloat entry_price, 
                                                                      jstring scope, jfloat leverage, 
                                                                      jfloat stop_loss) {
    const char* tickerStr = env->GetStringUTFChars(ticker, nullptr);
    const char* scopeStr = env->GetStringUTFChars(scope, nullptr);
    
    LOGI("Creating ticker monitor for %s with entry price %.2f", tickerStr, entry_price);
    
    int monitorId = pythonBridgeCreateTickerMonitor(tickerStr, entry_price, scopeStr, leverage, stop_loss);
    
    env->ReleaseStringUTFChars(ticker, tickerStr);
    env->ReleaseStringUTFChars(scope, scopeStr);
    
    if (monitorId >= 0) {
        LOGI("Created ticker monitor with ID: %d", monitorId);
    } else {
        LOGE("Failed to create ticker monitor");
    }
    
    return monitorId;
}

JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_stopTickerMonitor(JNIEnv *env, jclass clazz, jint monitor_id) {
    LOGI("Stopping ticker monitor with ID: %d", monitor_id);
    bool result = pythonBridgeStopTickerMonitor(monitor_id);
    if (result) {
        LOGI("Ticker monitor stopped successfully");
    } else {
        LOGE("Failed to stop ticker monitor");
    }
    return result ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_getNextMessage(JNIEnv *env, jclass clazz) {
    const char* message = pythonBridgeGetNextMessage();
    if (message && message[0] != '\0') {
        LOGI("Got message: %s", message);
        return env->NewStringUTF(message);
    }
    return env->NewStringUTF("");
}

JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_waitForMessage(JNIEnv *env, jclass clazz, jint timeout_ms) {
    const char* message = pythonBridgeWaitForMessage(timeout_ms);
    if (message && message[0] != '\0') {
        LOGI("Got message with wait: %s", message);
        return env->NewStringUTF(message);
    }
    return env->NewStringUTF("");
}

JNIEXPORT void JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_cleanupPythonBridge(JNIEnv *env, jclass clazz) {
    LOGI("Cleaning up Python bridge");
    pythonBridgeCleanup();
}

} // extern "C"
