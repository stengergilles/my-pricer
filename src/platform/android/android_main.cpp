#include <android/log.h>
#include <android_native_app_glue.h>
#include "../../include/platform/platform_android.h"
#include "../../include/application.h"

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "ImGuiApp", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "ImGuiApp", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", __VA_ARGS__))

// Global application instance
static PlatformAndroid* g_app = nullptr;
static bool g_initialized = false;

// Process Android command events
static void handle_cmd(android_app* app, int32_t cmd) {
    switch (cmd) {
        case APP_CMD_INIT_WINDOW:
            // Window is being shown, initialize
            LOGI("APP_CMD_INIT_WINDOW received, window pointer: %p", app->window);
            if (app->window != nullptr) {
                if (g_app && !g_initialized) {
                    // Set the Android app pointer first
                    g_app->setAndroidApp(app);
                    
                    // Add a small delay to ensure window is fully initialized
                    struct timespec ts;
                    ts.tv_sec = 0;
                    ts.tv_nsec = 10 * 1000000; // 10ms delay
                    nanosleep(&ts, NULL);
                    
                    // Initialize the platform
                    bool success = g_app->platformInit();
                    if (success) {
                        LOGI("Platform initialized successfully");
                        g_initialized = true;
                    } else {
                        LOGE("Platform initialization failed, will retry");
                    }
                }
            }
            break;
        case APP_CMD_TERM_WINDOW:
            // Window is being hidden or closed
            LOGI("Window terminated");
            if (g_app) {
                g_app->platformShutdown();
                g_initialized = false;
            }
            break;
        case APP_CMD_GAINED_FOCUS:
            // App gained focus, start rendering
            LOGI("App gained focus");
            break;
        case APP_CMD_LOST_FOCUS:
            // App lost focus, stop rendering
            LOGI("App lost focus");
            break;
        default:
            break;
    }
}

// Process Android input events
static int32_t handle_input(android_app* app, AInputEvent* event) {
    // Forward to ImGui
    if (AInputEvent_getType(event) == AINPUT_EVENT_TYPE_MOTION) {
        // Handle touch events
        return 1; // Event was handled
    }
    return 0; // Event was not handled
}

// Main entry point for Android applications using native_app_glue
void android_main(struct android_app* app) {
    // Make sure glue isn't stripped
    app_dummy();
    
    // Set callbacks
    app->onAppCmd = handle_cmd;
    app->onInputEvent = handle_input;
    
    // Create application instance
    g_app = new PlatformAndroid("ImGui Hello World");
    
    LOGI("Starting application main loop");
    
    // Main loop
    while (1) {
        // Read all pending events
        int events;
        android_poll_source* source;
        
        // Process events - block until we get events
        while ((ALooper_pollAll(g_initialized ? 0 : -1, nullptr, &events, (void**)&source)) >= 0) {
            if (source != nullptr) {
                source->process(app, source);
            }
            
            // Check if we are exiting
            if (app->destroyRequested != 0) {
                LOGI("Exiting application");
                if (g_app) {
                    delete g_app;
                    g_app = nullptr;
                }
                return;
            }
        }
        
        // If initialized, run the application frame
        if (g_initialized) {
            // Run a single frame of the application
            Application::getInstance()->renderFrame();
            
            // Sleep a bit to avoid busy waiting
            struct timespec ts;
            ts.tv_sec = 0;
            ts.tv_nsec = 16 * 1000000; // 16ms ~= 60fps
            nanosleep(&ts, NULL);
        }
    }
}
