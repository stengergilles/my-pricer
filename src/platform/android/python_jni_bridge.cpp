#include "python_jni_bridge.h"
#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "python_jni_bridge", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "python_jni_bridge", __VA_ARGS__))

// Stub implementation since we've removed Chaquopy
extern "C" {

JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_initializePythonBridge(JNIEnv *env, jclass clazz) {
    LOGI("Python bridge initialization requested, but Python support is disabled");
    return JNI_FALSE;
}

JNIEXPORT jint JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_createTickerMonitor(JNIEnv *env, jclass clazz, 
                                                                      jstring ticker, jfloat entry_price, 
                                                                      jstring scope, jfloat leverage, 
                                                                      jfloat stop_loss) {
    LOGI("Ticker monitor creation requested, but Python support is disabled");
    return -1;
}

JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_stopTickerMonitor(JNIEnv *env, jclass clazz, jint monitor_id) {
    LOGI("Stop ticker monitor requested, but Python support is disabled");
    return JNI_FALSE;
}

JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_getNextMessage(JNIEnv *env, jclass clazz) {
    return env->NewStringUTF("Python support is disabled");
}

JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_waitForMessage(JNIEnv *env, jclass clazz, jint timeout_ms) {
    return env->NewStringUTF("Python support is disabled");
}

JNIEXPORT void JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_cleanupPythonBridge(JNIEnv *env, jclass clazz) {
    LOGI("Python bridge cleanup requested, but Python support is disabled");
}

} // extern "C"
