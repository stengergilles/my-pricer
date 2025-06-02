#include "keyboard_helper.h"
#include <jni.h>
#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "KeyboardHelper", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "KeyboardHelper", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "KeyboardHelper", __VA_ARGS__))

// Forward declaration of the JavaVM reference from jni_bridge.cpp
extern JavaVM* g_JavaVM;

// Safe implementation of showKeyboard that checks for null pointers
bool showKeyboardSafely() {
    if (!g_JavaVM) {
        LOGE("JavaVM is null, cannot show keyboard");
        return false;
    }
    
    JNIEnv* env = nullptr;
    bool attached = false;
    
    // Get the JNIEnv safely
    jint result = g_JavaVM->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    if (result == JNI_EDETACHED) {
        if (g_JavaVM->AttachCurrentThread(&env, nullptr) != 0) {
            LOGE("Failed to attach thread to JavaVM");
            return false;
        }
        attached = true;
    } else if (result != JNI_OK || env == nullptr) {
        LOGE("Failed to get JNIEnv");
        return false;
    }
    
    // Find the MainActivity class
    jclass mainActivityClass = env->FindClass("com/example/imguihelloworld/MainActivity");
    if (mainActivityClass == nullptr) {
        LOGE("Failed to find MainActivity class");
        if (attached) g_JavaVM->DetachCurrentThread();
        return false;
    }
    
    // Find the static instance field
    jfieldID instanceField = env->GetStaticFieldID(mainActivityClass, "instance", "Lcom/example/imguihelloworld/MainActivity;");
    if (instanceField == nullptr) {
        LOGE("Failed to find instance field");
        env->DeleteLocalRef(mainActivityClass);
        if (attached) g_JavaVM->DetachCurrentThread();
        return false;
    }
    
    // Get the instance object
    jobject instance = env->GetStaticObjectField(mainActivityClass, instanceField);
    if (instance == nullptr) {
        LOGE("MainActivity instance is null");
        env->DeleteLocalRef(mainActivityClass);
        if (attached) g_JavaVM->DetachCurrentThread();
        return false;
    }
    
    // Find the showSoftKeyboard method
    jmethodID showKeyboardMethod = env->GetMethodID(mainActivityClass, "showSoftKeyboard", "()V");
    if (showKeyboardMethod == nullptr) {
        LOGE("Failed to find showSoftKeyboard method");
        env->DeleteLocalRef(instance);
        env->DeleteLocalRef(mainActivityClass);
        if (attached) g_JavaVM->DetachCurrentThread();
        return false;
    }
    
    // Call the method
    env->CallVoidMethod(instance, showKeyboardMethod);
    
    // Clean up local references
    env->DeleteLocalRef(instance);
    env->DeleteLocalRef(mainActivityClass);
    
    // Detach the thread if we attached it
    if (attached) {
        g_JavaVM->DetachCurrentThread();
    }
    
    return true;
}

// Original showKeyboard function - now just calls the safe version
extern "C" void showKeyboard() {
    showKeyboardSafely();
}
