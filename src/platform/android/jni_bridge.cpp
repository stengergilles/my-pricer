#include <jni.h>
#include <android/log.h>
#include <imgui.h>
#include <string>

#ifdef __cplusplus
extern "C" {
#endif

// Log tag for Android logcat
#define TAG "ImGuiJNI"

// Function to handle key events from Java
JNIEXPORT void JNICALL
Java_com_example_imguihelloworld_ImGuiJNI_onKeyEvent(JNIEnv *env, jclass clazz, 
                                                    jint keyCode, jint action, jint metaState) {
    // Process key events for ImGui
    ImGuiIO& io = ImGui::GetIO();
    
    // Convert Android key code to ImGui key code
    ImGuiKey imguiKey = ImGuiKey_None;
    
    // Map Android key codes to ImGui key codes
    // This is a simplified mapping, you may need to expand it
    switch (keyCode) {
        case 19: imguiKey = ImGuiKey_UpArrow; break;    // KEYCODE_DPAD_UP
        case 20: imguiKey = ImGuiKey_DownArrow; break;  // KEYCODE_DPAD_DOWN
        case 21: imguiKey = ImGuiKey_LeftArrow; break;  // KEYCODE_DPAD_LEFT
        case 22: imguiKey = ImGuiKey_RightArrow; break; // KEYCODE_DPAD_RIGHT
        case 66: imguiKey = ImGuiKey_Enter; break;      // KEYCODE_ENTER
        case 67: imguiKey = ImGuiKey_Backspace; break;  // KEYCODE_DEL
        case 61: imguiKey = ImGuiKey_Tab; break;        // KEYCODE_TAB
        case 62: imguiKey = ImGuiKey_Space; break;      // KEYCODE_SPACE
        // Add more key mappings as needed
    }
    
    // Process the key event
    if (imguiKey != ImGuiKey_None) {
        if (action == 0) { // ACTION_UP
            io.AddKeyEvent(imguiKey, false);
        } else if (action == 1) { // ACTION_DOWN
            io.AddKeyEvent(imguiKey, true);
        }
    }
}

// Function to handle text input from Java
JNIEXPORT void JNICALL
Java_com_example_imguihelloworld_ImGuiJNI_onTextInput(JNIEnv *env, jclass clazz, jstring text) {
    const char* utf8Text = env->GetStringUTFChars(text, nullptr);
    if (utf8Text) {
        ImGuiIO& io = ImGui::GetIO();
        io.AddInputCharactersUTF8(utf8Text);
        env->ReleaseStringUTFChars(text, utf8Text);
    }
}

// Function to check if ImGui wants text input
JNIEXPORT jboolean JNICALL
Java_com_example_imguihelloworld_ImGuiJNI_wantsTextInput(JNIEnv *env, jclass clazz) {
    ImGuiIO& io = ImGui::GetIO();
    return io.WantTextInput ? JNI_TRUE : JNI_FALSE;
}

// Function to get OpenSSL version from native code
JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_ImGuiJNI_getOpenSSLVersionFromNative(JNIEnv *env, jclass clazz) {
    // Call the OpenSSL version function from OpenSSLLoader
    jclass openSSLLoaderClass = env->FindClass("com/example/imguihelloworld/OpenSSLLoader");
    if (openSSLLoaderClass == nullptr) {
        return env->NewStringUTF("Error: OpenSSLLoader class not found");
    }
    
    jmethodID getVersionMethod = env->GetStaticMethodID(openSSLLoaderClass, "getOpenSSLVersion", "()Ljava/lang/String;");
    if (getVersionMethod == nullptr) {
        return env->NewStringUTF("Error: getOpenSSLVersion method not found");
    }
    
    jobject versionObj = env->CallStaticObjectMethod(openSSLLoaderClass, getVersionMethod);
    if (versionObj == nullptr) {
        return env->NewStringUTF("Error: Failed to get OpenSSL version");
    }
    
    return (jstring)versionObj;
}

#ifdef __cplusplus
}
#endif
