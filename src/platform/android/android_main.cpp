#include <android/log.h>
#include <android_native_app_glue.h>
#include "../../include/platform/platform_android.h"
#include "../../include/application.h"

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "ImGuiApp", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "ImGuiApp", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", __VA_ARGS__))

// Global application instance
static PlatformAndroid* g_app = nullptr;

// Process Android command events
static void handle_cmd(android_app* app, int32_t cmd) {
    switch (cmd) {
        case APP_CMD_INIT_WINDOW:
            // Window is being shown, initialize
            if (app->window != nullptr) {
                if (g_app) {
                    LOGI("Window initialized, setting up application");
                    g_app->setAndroidApp(app);
                    
                    // Don't start the application here, just initialize the platform
                    bool success = g_app->platformInit();
                    LOGI("Platform init result: %s", success ? "SUCCESS" : "FAILED");
                }
            }
            break;
        case APP_CMD_TERM_WINDOW:
            // Window is being hidden or closed
            if (g_app) {
                g_app->platformShutdown();
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
    g_app->setAndroidApp(app);
    
    // Main loop
    int frameCount = 0;
    while (1) {
        // Read all pending events
        int events;
        android_poll_source* source;
        
        // Process events
        while ((ALooper_pollAll(0, nullptr, &events, (void**)&source)) >= 0) {
            if (source != nullptr) {
                source->process(app, source);
            }
            
            // Check if we are exiting
            if (app->destroyRequested != 0) {
                LOGI("Exiting application");
                return;
            }
        }
        
        // If window is initialized, run the application
        if (app->window != nullptr) {
            static bool appStarted = false;
            if (!appStarted) {
                LOGI("Starting application main loop");
                Application::getInstance()->run();
                appStarted = true;
            }
            
            // If we're here, the application is running
            // Just sleep a bit to avoid busy waiting
            struct timespec ts;
            ts.tv_sec = 0;
            ts.tv_nsec = 16 * 1000000; // 16ms ~= 60fps
            nanosleep(&ts, NULL);
        }
            
            // Don't start the application here anymore
            // The application will be started in handle_cmd when the window is ready
            
            frameCount++;
        }
    }
    
    // Clean up
    delete g_app;
    g_app = nullptr;
}
