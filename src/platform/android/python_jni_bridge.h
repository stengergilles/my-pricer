#pragma once

#include <jni.h>

// JNI function declarations for Python bridge
extern "C" {

JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_initializePythonBridge(JNIEnv *env, jclass clazz);

JNIEXPORT jint JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_createTickerMonitor(JNIEnv *env, jclass clazz, 
                                                                      jstring ticker, jfloat entry_price, 
                                                                      jstring scope, jfloat leverage, 
                                                                      jfloat stop_loss);

JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_stopTickerMonitor(JNIEnv *env, jclass clazz, jint monitor_id);

JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_getNextMessage(JNIEnv *env, jclass clazz);

JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_waitForMessage(JNIEnv *env, jclass clazz, jint timeout_ms);

JNIEXPORT void JNICALL
Java_com_example_imguihelloworld_ImGuiPythonBridge_cleanupPythonBridge(JNIEnv *env, jclass clazz);

} // extern "C"
