#include "keyboard_helper.h"
#include <android/log.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "KeyboardHelper", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "KeyboardHelper", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "KeyboardHelper", __VA_ARGS__))

// Stub implementation that doesn't try to call Java methods
extern "C" void showKeyboard() {
    LOGI("showKeyboard called - functionality disabled");
    // Do nothing for now - this prevents crashes
}

// Stub implementation that doesn't try to call Java methods
extern "C" bool showKeyboardSafely() {
    LOGI("showKeyboardSafely called - functionality disabled");
    // Return false to indicate keyboard wasn't shown
    return false;
}
