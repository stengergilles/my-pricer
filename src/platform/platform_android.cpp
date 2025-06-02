#include <android/configuration.h>  // Added for AConfiguration_getScreenDensity
#include <android/native_activity.h>
#include <android/input.h>
#include <android/looper.h>  // For ALooper_pollAll
#include "imgui.h"
#include "../include/platform/platform_android.h"

// Define AConfiguration_getScreenDensity if it's not available
#ifndef AConfiguration_getScreenDensity
#define AConfiguration_getScreenDensity(config) 160  // Default density
#endif

// Forward declarations for Android NDK types
struct android_app;
struct android_poll_source {
    int32_t id;
    android_app* app;
    void (*process)(android_app* app, android_poll_source* source);
};

// Forward declaration for android_app structure
struct android_app {
    void* userData;
    void (*onAppCmd)(android_app* app, int32_t cmd);
    int32_t (*onInputEvent)(android_app* app, AInputEvent* event);
    struct ANativeActivity* activity;
    struct AConfiguration* config;
    // ... other fields not needed for this example
};

// ImGui Android implementation
extern bool ImGui_ImplAndroid_Init(ANativeWindow* window);
extern void ImGui_ImplAndroid_Shutdown();
extern void ImGui_ImplAndroid_NewFrame();
extern void ImGui_ImplAndroid_RenderDrawData(ImDrawData* draw_data);
extern bool ImGui_ImplAndroid_HandleInputEvent(const AInputEvent* input_event);

// Forward declaration of helper function
static AInputEvent* createTouchEvent(int32_t action, int32_t pointer_id, float x, float y);

// Helper function to get the Android app instance
static struct android_app* ImGui_ImplAndroid_GetApp() {
    // Implementation depends on how you store the android_app pointer
    // This is just a placeholder
    return (struct android_app*)Application::getInstance();  // Modified to avoid getPlatform()
}

PlatformAndroid::PlatformAndroid(const std::string& title) 
    : PlatformBase(title), m_androidApp(nullptr) {
}

PlatformAndroid::~PlatformAndroid() {
    platformShutdown();
}

void PlatformAndroid::setAndroidApp(void* app) {
    m_androidApp = app;
}

void* PlatformAndroid::getAndroidApp() {
    return m_androidApp;
}

bool PlatformAndroid::platformInit() {
    struct android_app* app = (struct android_app*)m_androidApp;
    if (!app) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "No Android app in platformInit");
        return false;
    }
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Creating ImGui context");
    ImGui::CreateContext();
    
    // Configure ImGui style
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = nullptr;
    
    // Set display metrics
    float xdpi = AConfiguration_getScreenDensity(app->config);
    float scale = xdpi / 160.0f;
    io.FontGlobalScale = scale;
    
    // Initialize ImGui for Android
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Initializing ImGui for Android");
    bool success = ImGui_ImplAndroid_Init(app->window);
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "ImGui Android init result: %s", success ? "SUCCESS" : "FAILED");
    
    return success;
}

void PlatformAndroid::platformNewFrame() {
    ImGui_ImplAndroid_NewFrame();
    ImGui::NewFrame();
}

void PlatformAndroid::platformRender() {
    // Begin ImGui frame
    ImGui::NewFrame();
    
    // Create a simple ImGui window
    ImGui::Begin("Hello, Android!");
    ImGui::Text("This is an ImGui window on Android");
    ImGui::Text("Application average %.3f ms/frame (%.1f FPS)", 
                1000.0f / ImGui::GetIO().Framerate, ImGui::GetIO().Framerate);
    ImGui::End();
    
    // Render ImGui
    ImGui::Render();
    ImGui_ImplAndroid_RenderDrawData(ImGui::GetDrawData());
}

bool PlatformAndroid::platformHandleEvents() {
    struct android_app* app = (struct android_app*)m_androidApp;
    if (!app) return false;
    
    // Process Android events
    int events;
    android_poll_source* source;
    
    // Poll for events
    if (ALooper_pollAll(0, nullptr, &events, (void**)&source) >= 0) {
        if (source != nullptr) {
            source->process(app, source);
        }
    }
    
    return true;
}

void PlatformAndroid::platformShutdown() {
    ImGui_ImplAndroid_Shutdown();
    ImGui::DestroyContext();
}

// Touch handling functions
bool handleTouchDown(int pointer_id, float x, float y) {
    AInputEvent* event = createTouchEvent(AMOTION_EVENT_ACTION_DOWN, pointer_id, x, y);
    bool result = ImGui_ImplAndroid_HandleInputEvent(event);
    // Free event if needed
    return result;
}

bool handleTouchMove(int pointer_id, float x, float y) {
    AInputEvent* event = createTouchEvent(AMOTION_EVENT_ACTION_MOVE, pointer_id, x, y);
    bool result = ImGui_ImplAndroid_HandleInputEvent(event);
    // Free event if needed
    return result;
}

bool handleTouchUp(int pointer_id, float x, float y) {
    AInputEvent* event = createTouchEvent(AMOTION_EVENT_ACTION_UP, pointer_id, x, y);
    bool result = ImGui_ImplAndroid_HandleInputEvent(event);
    // Free event if needed
    return result;
}

bool handleTouchCancel(int pointer_id, float x, float y) {
    AInputEvent* event = createTouchEvent(AMOTION_EVENT_ACTION_CANCEL, pointer_id, x, y);
    bool result = ImGui_ImplAndroid_HandleInputEvent(event);
    // Free event if needed
    return result;
}

// Helper function to create touch events
static AInputEvent* createTouchEvent(int32_t action, int32_t pointer_id, float x, float y) {
    // This is a placeholder - in a real implementation, you would use the Android NDK
    // to create proper input events. This is complex and requires more code than shown here.
    // For now, we'll return nullptr to indicate this needs proper implementation
    return nullptr;
}
