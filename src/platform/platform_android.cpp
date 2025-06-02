#include "../../include/platform/platform_android.h"
#include "imgui.h"
#include "imgui_impl_android.h"
#include "imgui_impl_opengl3.h"

#include <android/log.h>
#include <android/native_activity.h>
#include <android/input.h>
#include <android_native_app_glue.h>
#include <android/configuration.h>
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <jni.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "ImGuiApp", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "ImGuiApp", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", __VA_ARGS__))

// Global state for the Android app
struct AndroidAppState {
    ANativeWindow* window = nullptr;
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT;
    bool initialized = false;
    bool active = false;
    int32_t width = 0;
    int32_t height = 0;
    PlatformAndroid* app = nullptr;
};

// Forward declarations
static int32_t handleInputEvent(struct android_app* app, AInputEvent* event);
static void handleCmdEvent(struct android_app* app, int32_t cmd);
static bool initializeEGL(AndroidAppState* state);
static void terminateEGL(AndroidAppState* state);

PlatformAndroid::PlatformAndroid(const std::string& appName)
    : PlatformBase(appName)
    , m_androidApp(nullptr)
{
}

PlatformAndroid::~PlatformAndroid()
{
    platformShutdown();
}

bool PlatformAndroid::platformInit()
{
    // This function is called from the main thread after android_main has set up m_androidApp
    if (!m_androidApp) {
        LOGE("Android app not initialized");
        return false;
    }

    auto* app = static_cast<android_app*>(m_androidApp);
    auto* state = new AndroidAppState();
    state->app = this;
    app->userData = state;
    app->onAppCmd = handleCmdEvent;
    app->onInputEvent = handleInputEvent;

    // Wait for window to be initialized
    while (!state->initialized) {
        int events;
        android_poll_source* source;
        if (ALooper_pollAll(0, nullptr, &events, (void**)&source) >= 0) {
            if (source != nullptr) {
                source->process(app, source);
            }
        }
    }

    // Initialize ImGui for Android
    IMGUI_CHECKVERSION();
    ImGui_ImplAndroid_Init(app->window);
    ImGui_ImplOpenGL3_Init("#version 300 es");

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

void PlatformAndroid::platformShutdown()
{
    if (m_androidApp) {
        auto* app = static_cast<android_app*>(m_androidApp);
        if (app->userData) {
            auto* state = static_cast<AndroidAppState*>(app->userData);
            
            ImGui_ImplOpenGL3_Shutdown();
            ImGui_ImplAndroid_Shutdown();
            
            terminateEGL(state);
            delete state;
            app->userData = nullptr;
        }
        m_androidApp = nullptr;
    }
}

void PlatformAndroid::platformNewFrame()
{
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplAndroid_NewFrame();
}

void PlatformAndroid::platformRender()
{
    auto* app = static_cast<android_app*>(m_androidApp);
    auto* state = static_cast<AndroidAppState*>(app->userData);
    
    ImVec4 clear_color = ImVec4(0.45f, 0.55f, 0.60f, 1.00f);
    glViewport(0, 0, state->width, state->height);
    glClearColor(clear_color.x, clear_color.y, clear_color.z, clear_color.w);
    glClear(GL_COLOR_BUFFER_BIT);
    
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    eglSwapBuffers(state->display, state->surface);
}

bool PlatformAndroid::platformHandleEvents()
{
    auto* app = static_cast<android_app*>(m_androidApp);
    auto* state = static_cast<AndroidAppState*>(app->userData);
    
    // Process Android events
    int events;
    android_poll_source* source;
    while (ALooper_pollAll(0, nullptr, &events, (void**)&source) >= 0) {
        if (source != nullptr) {
            source->process(app, source);
        }
        
        // Check if we are exiting
        if (app->destroyRequested != 0) {
            return false;
        }
    }
    
    return state->active;
}

// Static helper functions

static int32_t handleInputEvent(struct android_app* app, AInputEvent* event)
{
    auto* state = static_cast<AndroidAppState*>(app->userData);
    if (!state || !state->initialized) return 0;
    
    if (ImGui_ImplAndroid_HandleInputEvent(event)) {
        return 1;
    }
    
    // Handle keyboard events
    if (AInputEvent_getType(event) == AINPUT_EVENT_TYPE_KEY) {
        int32_t keyCode = AKeyEvent_getKeyCode(event);
        int32_t action = AKeyEvent_getAction(event);
        int32_t metaState = AKeyEvent_getMetaState(event);
        
        ImGuiIO& io = ImGui::GetIO();
        
        if (action == AKEY_EVENT_ACTION_DOWN) {
            switch (keyCode) {
                case AKEYCODE_BACK:
                    // Handle back button
                    if (!io.WantCaptureMouse && !io.WantCaptureKeyboard) {
                        return 0;  // Let the system handle it
                    }
                    return 1;
                    
                default:
                    // Map Android key codes to ImGui key codes
                    int imguiKey = -1;
                    if (keyCode >= AKEYCODE_A && keyCode <= AKEYCODE_Z) {
                        imguiKey = ImGuiKey_A + (keyCode - AKEYCODE_A);
                    } else if (keyCode >= AKEYCODE_0 && keyCode <= AKEYCODE_9) {
                        imguiKey = ImGuiKey_0 + (keyCode - AKEYCODE_0);
                    } else {
                        // Map other keys as needed
                        switch (keyCode) {
                            case AKEYCODE_SPACE: imguiKey = ImGuiKey_Space; break;
                            case AKEYCODE_ENTER: imguiKey = ImGuiKey_Enter; break;
                            case AKEYCODE_ESCAPE: imguiKey = ImGuiKey_Escape; break;
                            case AKEYCODE_TAB: imguiKey = ImGuiKey_Tab; break;
                            case AKEYCODE_DEL: imguiKey = ImGuiKey_Backspace; break;
                            case AKEYCODE_FORWARD_DEL: imguiKey = ImGuiKey_Delete; break;
                            case AKEYCODE_DPAD_LEFT: imguiKey = ImGuiKey_LeftArrow; break;
                            case AKEYCODE_DPAD_RIGHT: imguiKey = ImGuiKey_RightArrow; break;
                            case AKEYCODE_DPAD_UP: imguiKey = ImGuiKey_UpArrow; break;
                            case AKEYCODE_DPAD_DOWN: imguiKey = ImGuiKey_DownArrow; break;
                            case AKEYCODE_PAGE_UP: imguiKey = ImGuiKey_PageUp; break;
                            case AKEYCODE_PAGE_DOWN: imguiKey = ImGuiKey_PageDown; break;
                            case AKEYCODE_HOME: imguiKey = ImGuiKey_Home; break;
                            case AKEYCODE_MOVE_END: imguiKey = ImGuiKey_End; break;
                        }
                    }
                    
                    if (imguiKey != -1) {
                        io.KeysDown[imguiKey] = true;
                        
                        // Handle modifiers
                        io.KeyShift = (metaState & AMETA_SHIFT_ON) != 0;
                        io.KeyCtrl = (metaState & AMETA_CTRL_ON) != 0;
                        io.KeyAlt = (metaState & AMETA_ALT_ON) != 0;
                        
                        return 1;
                    }
                    break;
            }
        } else if (action == AKEY_EVENT_ACTION_UP) {
            // Similar key mapping for key up events
            int imguiKey = -1;
            if (keyCode >= AKEYCODE_A && keyCode <= AKEYCODE_Z) {
                imguiKey = ImGuiKey_A + (keyCode - AKEYCODE_A);
            } else if (keyCode >= AKEYCODE_0 && keyCode <= AKEYCODE_9) {
                imguiKey = ImGuiKey_0 + (keyCode - AKEYCODE_0);
            } else {
                // Map other keys as needed (same mapping as above)
                switch (keyCode) {
                    case AKEYCODE_SPACE: imguiKey = ImGuiKey_Space; break;
                    case AKEYCODE_ENTER: imguiKey = ImGuiKey_Enter; break;
                    case AKEYCODE_ESCAPE: imguiKey = ImGuiKey_Escape; break;
                    case AKEYCODE_TAB: imguiKey = ImGuiKey_Tab; break;
                    case AKEYCODE_DEL: imguiKey = ImGuiKey_Backspace; break;
                    case AKEYCODE_FORWARD_DEL: imguiKey = ImGuiKey_Delete; break;
                    case AKEYCODE_DPAD_LEFT: imguiKey = ImGuiKey_LeftArrow; break;
                    case AKEYCODE_DPAD_RIGHT: imguiKey = ImGuiKey_RightArrow; break;
                    case AKEYCODE_DPAD_UP: imguiKey = ImGuiKey_UpArrow; break;
                    case AKEYCODE_DPAD_DOWN: imguiKey = ImGuiKey_DownArrow; break;
                    case AKEYCODE_PAGE_UP: imguiKey = ImGuiKey_PageUp; break;
                    case AKEYCODE_PAGE_DOWN: imguiKey = ImGuiKey_PageDown; break;
                    case AKEYCODE_HOME: imguiKey = ImGuiKey_Home; break;
                    case AKEYCODE_MOVE_END: imguiKey = ImGuiKey_End; break;
                }
            }
            
            if (imguiKey != -1) {
                ImGui::GetIO().KeysDown[imguiKey] = false;
                
                // Update modifiers
                ImGuiIO& io = ImGui::GetIO();
                io.KeyShift = (metaState & AMETA_SHIFT_ON) != 0;
                io.KeyCtrl = (metaState & AMETA_CTRL_ON) != 0;
                io.KeyAlt = (metaState & AMETA_ALT_ON) != 0;
                
                return 1;
            }
        }
    }
    
    return 0;
}

static void handleCmdEvent(struct android_app* app, int32_t cmd)
{
    auto* state = static_cast<AndroidAppState*>(app->userData);
    if (!state) return;
    
    switch (cmd) {
        case APP_CMD_SAVE_STATE:
            LOGI("APP_CMD_SAVE_STATE");
            break;
            
        case APP_CMD_INIT_WINDOW:
            LOGI("APP_CMD_INIT_WINDOW");
            if (app->window != nullptr) {
                state->window = app->window;
                if (initializeEGL(state)) {
                    state->initialized = true;
                    state->active = true;
                }
            }
            break;
            
        case APP_CMD_TERM_WINDOW:
            LOGI("APP_CMD_TERM_WINDOW");
            terminateEGL(state);
            state->initialized = false;
            state->active = false;
            break;
            
        case APP_CMD_GAINED_FOCUS:
            LOGI("APP_CMD_GAINED_FOCUS");
            state->active = true;
            break;
            
        case APP_CMD_LOST_FOCUS:
            LOGI("APP_CMD_LOST_FOCUS");
            state->active = false;
            break;
            
        case APP_CMD_WINDOW_RESIZED:
        case APP_CMD_CONFIG_CHANGED:
            LOGI("Window resized or config changed");
            // Update window size
            if (state->display != EGL_NO_DISPLAY && state->surface != EGL_NO_SURFACE) {
                eglQuerySurface(state->display, state->surface, EGL_WIDTH, &state->width);
                eglQuerySurface(state->display, state->surface, EGL_HEIGHT, &state->height);
                LOGI("New size: %dx%d", state->width, state->height);
            }
            break;
            
        default:
            break;
    }
}

static bool initializeEGL(AndroidAppState* state)
{
    // Initialize EGL
    EGLint majorVersion, minorVersion;
    EGLint format;
    EGLint numConfigs;
    EGLConfig config;
    EGLint attribs[] = {
        EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_DEPTH_SIZE, 16,
        EGL_STENCIL_SIZE, 8,
        EGL_NONE
    };
    
    EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };
    
    // Get display
    state->display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (state->display == EGL_NO_DISPLAY) {
        LOGE("eglGetDisplay failed: %d", eglGetError());
        return false;
    }
    
    // Initialize display
    if (!eglInitialize(state->display, &majorVersion, &minorVersion)) {
        LOGE("eglInitialize failed: %d", eglGetError());
        return false;
    }
    
    LOGI("EGL version: %d.%d", majorVersion, minorVersion);
    
    // Choose config
    if (!eglChooseConfig(state->display, attribs, &config, 1, &numConfigs) || numConfigs == 0) {
        LOGE("eglChooseConfig failed: %d", eglGetError());
        return false;
    }
    
    // Get the selected config's format
    if (!eglGetConfigAttrib(state->display, config, EGL_NATIVE_VISUAL_ID, &format)) {
        LOGE("eglGetConfigAttrib failed: %d", eglGetError());
        return false;
    }
    
    // Set the window's format
    ANativeWindow_setBuffersGeometry(state->window, 0, 0, format);
    
    // Create surface
    state->surface = eglCreateWindowSurface(state->display, config, state->window, nullptr);
    if (state->surface == EGL_NO_SURFACE) {
        LOGE("eglCreateWindowSurface failed: %d", eglGetError());
        return false;
    }
    
    // Create context
    state->context = eglCreateContext(state->display, config, EGL_NO_CONTEXT, contextAttribs);
    if (state->context == EGL_NO_CONTEXT) {
        LOGE("eglCreateContext failed: %d", eglGetError());
        return false;
    }
    
    // Make current
    if (!eglMakeCurrent(state->display, state->surface, state->surface, state->context)) {
        LOGE("eglMakeCurrent failed: %d", eglGetError());
        return false;
    }
    
    // Get surface dimensions
    eglQuerySurface(state->display, state->surface, EGL_WIDTH, &state->width);
    eglQuerySurface(state->display, state->surface, EGL_HEIGHT, &state->height);
    
    LOGI("EGL initialized: %dx%d", state->width, state->height);
    
    return true;
}

static void terminateEGL(AndroidAppState* state)
{
    if (state->display != EGL_NO_DISPLAY) {
        eglMakeCurrent(state->display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        
        if (state->context != EGL_NO_CONTEXT) {
            eglDestroyContext(state->display, state->context);
            state->context = EGL_NO_CONTEXT;
        }
        
        if (state->surface != EGL_NO_SURFACE) {
            eglDestroySurface(state->display, state->surface);
            state->surface = EGL_NO_SURFACE;
        }
        
        eglTerminate(state->display);
        state->display = EGL_NO_DISPLAY;
    }
}

// Android entry point
extern "C" void android_main(struct android_app* app)
{
    // Make sure glue isn't stripped
    app_dummy();
    
    // Create and run the application
    PlatformAndroid platform("ImGui Hello World");
    platform.m_androidApp = app;
    platform.run();
}
