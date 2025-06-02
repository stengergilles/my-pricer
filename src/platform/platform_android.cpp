#include <android/configuration.h>  // Added for AConfiguration_getScreenDensity
#include <android/native_activity.h>
#include <android/input.h>
#include "imgui.h"
#include "../include/platform/platform_android.h"
#include "../include/application.h"

// ImGui Android implementation
extern bool ImGui_ImplAndroid_Init(ANativeWindow* window);
extern void ImGui_ImplAndroid_Shutdown();
extern void ImGui_ImplAndroid_NewFrame();
extern void ImGui_ImplAndroid_RenderDrawData(ImDrawData* draw_data);
extern bool ImGui_ImplAndroid_HandleInputEvent(const AInputEvent* input_event);

// Helper function to get the Android app instance
static struct android_app* ImGui_ImplAndroid_GetApp() {
    // Implementation depends on how you store the android_app pointer
    // This is just a placeholder
    return (struct android_app*)Application::getInstance()->getPlatform()->getAndroidApp();
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
    if (!app) return false;
    
    ImGui::CreateContext();
    
    // Configure ImGui style
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;  // Enable keyboard navigation
    io.IniFilename = nullptr;  // Disable .ini file
    
    // Set display metrics
    float xdpi = AConfiguration_getScreenDensity(app->config);
    float scale = xdpi / 160.0f;
    io.FontGlobalScale = scale;
    
    return true;
}

void PlatformAndroid::platformNewFrame() {
    ImGui_ImplAndroid_NewFrame();
    ImGui::NewFrame();
}

void PlatformAndroid::platformRender() {
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
    return ImGui_ImplAndroid_HandleInputEvent(createTouchEvent(AMOTION_EVENT_ACTION_DOWN, pointer_id, x, y));
}

bool handleTouchMove(int pointer_id, float x, float y) {
    return ImGui_ImplAndroid_HandleInputEvent(createTouchEvent(AMOTION_EVENT_ACTION_MOVE, pointer_id, x, y));
}

bool handleTouchUp(int pointer_id, float x, float y) {
    return ImGui_ImplAndroid_HandleInputEvent(createTouchEvent(AMOTION_EVENT_ACTION_UP, pointer_id, x, y));
}

bool handleTouchCancel(int pointer_id, float x, float y) {
    return ImGui_ImplAndroid_HandleInputEvent(createTouchEvent(AMOTION_EVENT_ACTION_CANCEL, pointer_id, x, y));
}

// Helper function to create touch events
AInputEvent* createTouchEvent(int32_t action, int32_t pointer_id, float x, float y) {
    // This is a placeholder - in a real implementation, you would use the Android NDK
    // to create proper input events. This is complex and requires more code than shown here.
    // For now, we'll return nullptr to indicate this needs proper implementation
    return nullptr;
}
