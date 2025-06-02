#include "keyboard_helper.h"
#include <jni.h>
#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "KeyboardHelper", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "KeyboardHelper", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "KeyboardHelper", __VA_ARGS__))

// Forward declaration of the JavaVM reference from jni_bridge.cpp
extern JavaVM* g_JavaVM;

// Implementation of the showKeyboard function is now in jni_bridge.cpp
// This file is kept for organization purposes but doesn't define the function
