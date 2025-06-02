#include "keyboard_helper.h"
#include <jni.h>
#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "KeyboardHelper", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "KeyboardHelper", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "KeyboardHelper", __VA_ARGS__))

// Forward declaration of the JavaVM reference from jni_bridge.cpp
extern JavaVM* g_JavaVM;

// Implementation of the showKeyboard function
void showKeyboard() {
    LOGI("showKeyboard called");
    
    // If we don't have a JavaVM reference, we can't do anything
    if (!g_JavaVM) {
        LOGE("No JavaVM reference available");
        return;
    }
    
    JNIEnv* env;
    bool attached = false;
    
    // Get the JNIEnv
    jint result = g_JavaVM->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    if (result == JNI_EDETACHED) {
        if (g_JavaVM->AttachCurrentThread(&env, nullptr) != 0) {
            LOGE("Failed to attach thread to JavaVM");
            return;
        }
        attached = true;
    } else if (result != JNI_OK) {
        LOGE("Failed to get JNIEnv");
        return;
    }
    
    // Find the MainActivity class
    jclass mainActivityClass = env->FindClass("com/example/imguihelloworld/MainActivity");
    if (mainActivityClass == nullptr) {
        LOGE("Failed to find MainActivity class");
        if (attached) g_JavaVM->DetachCurrentThread();
        return;
    }
    
    // Find the static instance field
    jfieldID instanceField = env->GetStaticFieldID(mainActivityClass, "instance", "Lcom/example/imguihelloworld/MainActivity;");
    if (instanceField == nullptr) {
        LOGE("Failed to find instance field");
        if (attached) g_JavaVM->DetachCurrentThread();
        return;
    }
    
    // Get the instance object
    jobject instance = env->GetStaticObjectField(mainActivityClass, instanceField);
    if (instance == nullptr) {
        LOGE("MainActivity instance is null");
        if (attached) g_JavaVM->DetachCurrentThread();
        return;
    }
    
    // Find the showSoftKeyboard method
    jmethodID showKeyboardMethod = env->GetMethodID(mainActivityClass, "showSoftKeyboard", "()V");
    if (showKeyboardMethod == nullptr) {
        LOGE("Failed to find showSoftKeyboard method");
        if (attached) g_JavaVM->DetachCurrentThread();
        return;
    }
    
    // Call the method
    env->CallVoidMethod(instance, showKeyboardMethod);
    
    // Detach the thread if we attached it
    if (attached) {
        g_JavaVM->DetachCurrentThread();
    }
}
