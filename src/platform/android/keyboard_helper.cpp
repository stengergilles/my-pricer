#include "keyboard_helper.h"
#include <jni.h>
#include <android/log.h>
#include "imgui.h"  // Added ImGui header

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "KeyboardHelper", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "KeyboardHelper", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "KeyboardHelper", __VA_ARGS__))

// Forward declaration of the JavaVM reference from jni_bridge.cpp
extern JavaVM* g_JavaVM;

// These need to be declared as extern variables from jni_bridge.cpp
extern jclass g_MainActivityClass;
extern jmethodID g_ShowKeyboardMethod;
extern jmethodID g_HideKeyboardMethod;

// Implementation of the showKeyboard function
extern "C" void showKeyboard() {
    LOGI("showKeyboard called");
    showKeyboardSafely();
}

// Implementation of the hideKeyboard function
extern "C" void hideKeyboard() {
    LOGI("hideKeyboard called");
    hideKeyboardSafely();
}

// Safe implementation of showKeyboard that checks for null pointers
extern "C" bool showKeyboardSafely() {
    LOGI("showKeyboardSafely called - attempting to show keyboard");
    
    if (!g_JavaVM) {
        LOGE("JavaVM is null, cannot show keyboard");
        return false;
    }
    
    JNIEnv* env = nullptr;
    bool attached = false;
    
    // Get the JNIEnv safely
    jint result = g_JavaVM->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    if (result == JNI_EDETACHED) {
        LOGI("Thread not attached, attaching now");
        if (g_JavaVM->AttachCurrentThread(&env, nullptr) != 0) {
            LOGE("Failed to attach thread to JavaVM");
            return false;
        }
        attached = true;
    } else if (result != JNI_OK || env == nullptr) {
        LOGE("Failed to get JNIEnv");
        return false;
    }
    
    // Find the MainActivity class if not already cached
    jclass mainActivityClass = g_MainActivityClass;
    if (mainActivityClass == nullptr) {
        LOGI("Finding MainActivity class");
        mainActivityClass = env->FindClass("com/example/imguihelloworld/MainActivity");
        if (mainActivityClass == nullptr) {
            LOGE("Failed to find MainActivity class");
            env->ExceptionClear(); // Clear any pending exception
            if (attached) g_JavaVM->DetachCurrentThread();
            return false;
        }
        g_MainActivityClass = (jclass)env->NewGlobalRef(mainActivityClass);
    }
    
    // Find the showKeyboard method if not already cached
    jmethodID showKeyboardMethod = g_ShowKeyboardMethod;
    if (showKeyboardMethod == nullptr) {
        LOGI("Finding showKeyboard method");
        showKeyboardMethod = env->GetStaticMethodID(mainActivityClass, "showKeyboard", "()V");
        if (showKeyboardMethod == nullptr) {
            LOGE("Failed to find showKeyboard method");
            env->ExceptionClear(); // Clear any pending exception
            if (attached) g_JavaVM->DetachCurrentThread();
            return false;
        }
        g_ShowKeyboardMethod = showKeyboardMethod;
    }
    
    // Call the static method
    LOGI("Calling MainActivity.showKeyboard()");
    env->CallStaticVoidMethod(mainActivityClass, showKeyboardMethod);
    
    // Check for exceptions
    if (env->ExceptionCheck()) {
        LOGE("Exception occurred while calling showKeyboard");
        env->ExceptionDescribe();
        env->ExceptionClear();
        if (attached) g_JavaVM->DetachCurrentThread();
        return false;
    }
    
    // Detach the thread if we attached it
    if (attached) {
        LOGI("Detaching thread");
        g_JavaVM->DetachCurrentThread();
    }
    
    LOGI("showKeyboardSafely completed successfully");
    return true;
}

// Safe implementation of hideKeyboard that checks for null pointers
extern "C" bool hideKeyboardSafely() {
    LOGI("hideKeyboardSafely called - attempting to hide keyboard");
    
    if (!g_JavaVM) {
        LOGE("JavaVM is null, cannot hide keyboard");
        return false;
    }
    
    JNIEnv* env = nullptr;
    bool attached = false;
    
    // Get the JNIEnv safely
    jint result = g_JavaVM->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    if (result == JNI_EDETACHED) {
        LOGI("Thread not attached, attaching now");
        if (g_JavaVM->AttachCurrentThread(&env, nullptr) != 0) {
            LOGE("Failed to attach thread to JavaVM");
            return false;
        }
        attached = true;
    } else if (result != JNI_OK || env == nullptr) {
        LOGE("Failed to get JNIEnv");
        return false;
    }
    
    // Find the MainActivity class if not already cached
    jclass mainActivityClass = g_MainActivityClass;
    if (mainActivityClass == nullptr) {
        LOGI("Finding MainActivity class");
        mainActivityClass = env->FindClass("com/example/imguihelloworld/MainActivity");
        if (mainActivityClass == nullptr) {
            LOGE("Failed to find MainActivity class");
            env->ExceptionClear(); // Clear any pending exception
            if (attached) g_JavaVM->DetachCurrentThread();
            return false;
        }
        g_MainActivityClass = (jclass)env->NewGlobalRef(mainActivityClass);
    }
    
    // Find the hideKeyboard method if not already cached
    jmethodID hideKeyboardMethod = g_HideKeyboardMethod;
    if (hideKeyboardMethod == nullptr) {
        LOGI("Finding hideKeyboard method");
        hideKeyboardMethod = env->GetStaticMethodID(mainActivityClass, "hideKeyboard", "()V");
        if (hideKeyboardMethod == nullptr) {
            LOGE("Failed to find hideKeyboard method");
            env->ExceptionClear(); // Clear any pending exception
            if (attached) g_JavaVM->DetachCurrentThread();
            return false;
        }
        g_HideKeyboardMethod = hideKeyboardMethod;
    }
    
    // Call the static method
    LOGI("Calling MainActivity.hideKeyboard()");
    env->CallStaticVoidMethod(mainActivityClass, hideKeyboardMethod);
    
    // Check for exceptions
    if (env->ExceptionCheck()) {
        LOGE("Exception occurred while calling hideKeyboard");
        env->ExceptionDescribe();
        env->ExceptionClear();
        if (attached) g_JavaVM->DetachCurrentThread();
        return false;
    }
    
    // Detach the thread if we attached it
    if (attached) {
        LOGI("Detaching thread");
        g_JavaVM->DetachCurrentThread();
    }
    
    LOGI("hideKeyboardSafely completed successfully");
    return true;
}
