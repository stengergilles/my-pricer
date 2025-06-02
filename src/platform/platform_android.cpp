#include "platform/platform_android.h"
#include "imgui.h"
#include "imgui_impl_android.h"
#include "imgui_impl_opengl3.h"

// Add missing header for AConfiguration_getScreenDensity
#include <android/configuration.h>

#include <android/log.h>
#include <android/native_window.h>
#include <android/input.h>
#include <android_native_app_glue.h>

#include <EGL/egl.h>
#include <GLES3/gl3.h>

#define LOGI(...) ((void)__android_log_print(ANDROID_LOG_INFO, "ImGui", __VA_ARGS__))
#define LOGW(...) ((void)__android_log_print(ANDROID_LOG_WARN, "ImGui", __VA_ARGS__))
#define LOGE(...) ((void)__android_log_print(ANDROID_LOG_ERROR, "ImGui", __VA_ARGS__))

// EGL context globals
static EGLDisplay g_EglDisplay = EGL_NO_DISPLAY;
static EGLSurface g_EglSurface = EGL_NO_SURFACE;
static EGLContext g_EglContext = EGL_NO_CONTEXT;

// Forward declarations
static int InitializeOpenGL();
static void ShutdownOpenGL();
static void HandleAppCommand(struct android_app* app, int32_t appCmd);
static int32_t HandleInputEvent(struct android_app* app, AInputEvent* event);

PlatformAndroid::PlatformAndroid(const std::string& title) : PlatformBase(title) {
    // Initialize platform-specific members
    m_androidApp = nullptr;
}

PlatformAndroid::~PlatformAndroid() {
    // Clean up platform-specific resources
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplAndroid_Shutdown();
    ImGui::DestroyContext();
    
    ShutdownOpenGL();
}

bool PlatformAndroid::platformInit() {
    // Get the android_app instance
    struct android_app* app = static_cast<struct android_app*>(m_androidApp);
    if (!app) {
        LOGE("Android app instance is null");
        return false;
    }
    
    // Set callbacks
    app->onAppCmd = HandleAppCommand;
    app->onInputEvent = HandleInputEvent;
    app->userData = this;
    
    // Wait for window to be initialized
    while (app->window == nullptr) {
        int events;
        struct android_poll_source* source;
        
        // Process events
        if (ALooper_pollAll(0, nullptr, &events, (void**)&source) >= 0) {
            if (source != nullptr) {
                source->process(app, source);
            }
        }
    }
    
    // Initialize OpenGL
    if (!InitializeOpenGL()) {
        LOGE("Failed to initialize OpenGL");
        return false;
    }
    
    // Setup Dear ImGui context
    IMGUI_CHECKVERSION();
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
    // Start the Dear ImGui frame
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplAndroid_NewFrame();
    ImGui::NewFrame();
}

void PlatformAndroid::platformRender() {
    // Rendering
    ImGui::Render();
    
    glViewport(0, 0, (int)ImGui::GetIO().DisplaySize.x, (int)ImGui::GetIO().DisplaySize.y);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    eglSwapBuffers(g_EglDisplay, g_EglSurface);
}

bool PlatformAndroid::platformHandleEvents() {
    // Get the android_app instance
    struct android_app* app = static_cast<struct android_app*>(m_androidApp);
    if (!app) {
        return false;
    }
    
    // Process events
    int events;
    struct android_poll_source* source;
    
    // Poll for events without blocking
    while (ALooper_pollAll(0, nullptr, &events, (void**)&source) >= 0) {
        if (source != nullptr) {
            source->process(app, source);
        }
        
        // Check if we are exiting
        if (app->destroyRequested != 0) {
            return false;
        }
    }
    
    return true;
}

// Public setter for m_androidApp to fix private member access issue
void PlatformAndroid::setAndroidApp(void* app) {
    m_androidApp = app;
}

// OpenGL initialization
static int InitializeOpenGL() {
    // Initialize EGL
    g_EglDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g_EglDisplay == EGL_NO_DISPLAY) {
        LOGE("eglGetDisplay failed");
        return 0;
    }
    
    if (eglInitialize(g_EglDisplay, nullptr, nullptr) != EGL_TRUE) {
        LOGE("eglInitialize failed");
        return 0;
    }
    
    // Configure EGL
    EGLint attribs[] = {
        EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
        EGL_BLUE_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_RED_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_DEPTH_SIZE, 16,
        EGL_STENCIL_SIZE, 8,
        EGL_NONE
    };
    
    EGLint numConfigs;
    EGLConfig config;
    if (eglChooseConfig(g_EglDisplay, attribs, &config, 1, &numConfigs) != EGL_TRUE) {
        LOGE("eglChooseConfig failed");
        return 0;
    }
    
    // Create surface
    ANativeWindow* window = (ANativeWindow*)((struct android_app*)ImGui_ImplAndroid_GetApp())->window;
    g_EglSurface = eglCreateWindowSurface(g_EglDisplay, config, window, nullptr);
    if (g_EglSurface == EGL_NO_SURFACE) {
        LOGE("eglCreateWindowSurface failed");
        return 0;
    }
    
    // Create context
    EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };
    g_EglContext = eglCreateContext(g_EglDisplay, config, EGL_NO_CONTEXT, contextAttribs);
    if (g_EglContext == EGL_NO_CONTEXT) {
        LOGE("eglCreateContext failed");
        return 0;
    }
    
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE) {
        LOGE("eglMakeCurrent failed");
        return 0;
    }
    
    // Initialize ImGui backends
    ImGui_ImplAndroid_Init(window);
    ImGui_ImplOpenGL3_Init("#version 300 es");
    
    return 1;
}

static void ShutdownOpenGL() {
    if (g_EglDisplay != EGL_NO_DISPLAY) {
        eglMakeCurrent(g_EglDisplay, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        
        if (g_EglContext != EGL_NO_CONTEXT) {
            eglDestroyContext(g_EglDisplay, g_EglContext);
            g_EglContext = EGL_NO_CONTEXT;
        }
        
        if (g_EglSurface != EGL_NO_SURFACE) {
            eglDestroySurface(g_EglDisplay, g_EglSurface);
            g_EglSurface = EGL_NO_SURFACE;
        }
        
        eglTerminate(g_EglDisplay);
        g_EglDisplay = EGL_NO_DISPLAY;
    }
}

// Android app command handler
static void HandleAppCommand(struct android_app* app, int32_t appCmd) {
    switch (appCmd) {
        case APP_CMD_SAVE_STATE:
            // The system has asked us to save our current state
            LOGI("APP_CMD_SAVE_STATE");
            break;
            
        case APP_CMD_INIT_WINDOW:
            // The window is being shown, get it ready
            LOGI("APP_CMD_INIT_WINDOW");
            if (app->window != nullptr) {
                InitializeOpenGL();
            }
            break;
            
        case APP_CMD_TERM_WINDOW:
            // The window is being hidden or closed
            LOGI("APP_CMD_TERM_WINDOW");
            ShutdownOpenGL();
            break;
            
        case APP_CMD_GAINED_FOCUS:
            // App gains focus
            LOGI("APP_CMD_GAINED_FOCUS");
            break;
            
        case APP_CMD_LOST_FOCUS:
            // App loses focus
            LOGI("APP_CMD_LOST_FOCUS");
            break;
            
        default:
            break;
    }
}

// Android input event handler
static int32_t HandleInputEvent(struct android_app* app, AInputEvent* event) {
    ImGuiIO& io = ImGui::GetIO();
    
    int32_t eventType = AInputEvent_getType(event);
    
    if (eventType == AINPUT_EVENT_TYPE_MOTION) {
        int32_t action = AMotionEvent_getAction(event);
        int32_t pointerIndex = (action & AMOTION_EVENT_ACTION_POINTER_INDEX_MASK) >> AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT;
        int32_t pointerId = AMotionEvent_getPointerId(event, pointerIndex);
        int32_t actionMasked = action & AMOTION_EVENT_ACTION_MASK;
        
        switch (actionMasked) {
            case AMOTION_EVENT_ACTION_DOWN:
            case AMOTION_EVENT_ACTION_POINTER_DOWN:
                {
                    float x = AMotionEvent_getX(event, pointerIndex);
                    float y = AMotionEvent_getY(event, pointerIndex);
                    ImGui_ImplAndroid_HandleTouchDown(pointerId, x, y);
                }
                return 1;
                
            case AMOTION_EVENT_ACTION_MOVE:
                {
                    int32_t pointerCount = AMotionEvent_getPointerCount(event);
                    for (int i = 0; i < pointerCount; i++) {
                        float x = AMotionEvent_getX(event, i);
                        float y = AMotionEvent_getY(event, i);
                        int32_t id = AMotionEvent_getPointerId(event, i);
                        ImGui_ImplAndroid_HandleTouchMove(id, x, y);
                    }
                }
                return 1;
                
            case AMOTION_EVENT_ACTION_UP:
            case AMOTION_EVENT_ACTION_POINTER_UP:
                {
                    ImGui_ImplAndroid_HandleTouchUp(pointerId);
                }
                return 1;
                
            case AMOTION_EVENT_ACTION_CANCEL:
                {
                    int32_t pointerCount = AMotionEvent_getPointerCount(event);
                    for (int i = 0; i < pointerCount; i++) {
                        int32_t id = AMotionEvent_getPointerId(event, i);
                        ImGui_ImplAndroid_HandleTouchUp(id);
                    }
                }
                return 1;
        }
    }
    else if (eventType == AINPUT_EVENT_TYPE_KEY) {
        int32_t keyCode = AKeyEvent_getKeyCode(event);
        int32_t action = AKeyEvent_getAction(event);
        int32_t metaState = AKeyEvent_getMetaState(event);
        
        if (action == AKEY_EVENT_ACTION_DOWN || action == AKEY_EVENT_ACTION_UP) {
            // Map Android key codes to ImGui key codes
            ImGuiKey imguiKey = ImGuiKey_None;
            
            switch (keyCode) {
                case AKEYCODE_TAB: imguiKey = ImGuiKey_Tab; break;
                case AKEYCODE_DPAD_LEFT: imguiKey = ImGuiKey_LeftArrow; break;
                case AKEYCODE_DPAD_RIGHT: imguiKey = ImGuiKey_RightArrow; break;
                case AKEYCODE_DPAD_UP: imguiKey = ImGuiKey_UpArrow; break;
                case AKEYCODE_DPAD_DOWN: imguiKey = ImGuiKey_DownArrow; break;
                case AKEYCODE_PAGE_UP: imguiKey = ImGuiKey_PageUp; break;
                case AKEYCODE_PAGE_DOWN: imguiKey = ImGuiKey_PageDown; break;
                case AKEYCODE_MOVE_HOME: imguiKey = ImGuiKey_Home; break;
                case AKEYCODE_MOVE_END: imguiKey = ImGuiKey_End; break;
                case AKEYCODE_INSERT: imguiKey = ImGuiKey_Insert; break;
                case AKEYCODE_FORWARD_DEL: imguiKey = ImGuiKey_Delete; break;
                case AKEYCODE_DEL: imguiKey = ImGuiKey_Backspace; break;
                case AKEYCODE_SPACE: imguiKey = ImGuiKey_Space; break;
                case AKEYCODE_ENTER: imguiKey = ImGuiKey_Enter; break;
                case AKEYCODE_ESCAPE: imguiKey = ImGuiKey_Escape; break;
                case AKEYCODE_APOSTROPHE: imguiKey = ImGuiKey_Apostrophe; break;
                case AKEYCODE_COMMA: imguiKey = ImGuiKey_Comma; break;
                case AKEYCODE_MINUS: imguiKey = ImGuiKey_Minus; break;
                case AKEYCODE_PERIOD: imguiKey = ImGuiKey_Period; break;
                case AKEYCODE_SLASH: imguiKey = ImGuiKey_Slash; break;
                case AKEYCODE_SEMICOLON: imguiKey = ImGuiKey_Semicolon; break;
                case AKEYCODE_EQUALS: imguiKey = ImGuiKey_Equal; break;
                case AKEYCODE_LEFT_BRACKET: imguiKey = ImGuiKey_LeftBracket; break;
                case AKEYCODE_BACKSLASH: imguiKey = ImGuiKey_Backslash; break;
                case AKEYCODE_RIGHT_BRACKET: imguiKey = ImGuiKey_RightBracket; break;
                case AKEYCODE_GRAVE: imguiKey = ImGuiKey_GraveAccent; break;
                case AKEYCODE_CAPS_LOCK: imguiKey = ImGuiKey_CapsLock; break;
                case AKEYCODE_SCROLL_LOCK: imguiKey = ImGuiKey_ScrollLock; break;
                case AKEYCODE_NUM_LOCK: imguiKey = ImGuiKey_NumLock; break;
                case AKEYCODE_SYSRQ: imguiKey = ImGuiKey_PrintScreen; break;
                case AKEYCODE_BREAK: imguiKey = ImGuiKey_Pause; break;
                case AKEYCODE_NUMPAD_0: imguiKey = ImGuiKey_Keypad0; break;
                case AKEYCODE_NUMPAD_1: imguiKey = ImGuiKey_Keypad1; break;
                case AKEYCODE_NUMPAD_2: imguiKey = ImGuiKey_Keypad2; break;
                case AKEYCODE_NUMPAD_3: imguiKey = ImGuiKey_Keypad3; break;
                case AKEYCODE_NUMPAD_4: imguiKey = ImGuiKey_Keypad4; break;
                case AKEYCODE_NUMPAD_5: imguiKey = ImGuiKey_Keypad5; break;
                case AKEYCODE_NUMPAD_6: imguiKey = ImGuiKey_Keypad6; break;
                case AKEYCODE_NUMPAD_7: imguiKey = ImGuiKey_Keypad7; break;
                case AKEYCODE_NUMPAD_8: imguiKey = ImGuiKey_Keypad8; break;
                case AKEYCODE_NUMPAD_9: imguiKey = ImGuiKey_Keypad9; break;
                case AKEYCODE_NUMPAD_DOT: imguiKey = ImGuiKey_KeypadDecimal; break;
                case AKEYCODE_NUMPAD_DIVIDE: imguiKey = ImGuiKey_KeypadDivide; break;
                case AKEYCODE_NUMPAD_MULTIPLY: imguiKey = ImGuiKey_KeypadMultiply; break;
                case AKEYCODE_NUMPAD_SUBTRACT: imguiKey = ImGuiKey_KeypadSubtract; break;
                case AKEYCODE_NUMPAD_ADD: imguiKey = ImGuiKey_KeypadAdd; break;
                case AKEYCODE_NUMPAD_ENTER: imguiKey = ImGuiKey_KeypadEnter; break;
                case AKEYCODE_NUMPAD_EQUALS: imguiKey = ImGuiKey_KeypadEqual; break;
                case AKEYCODE_CTRL_LEFT: imguiKey = ImGuiKey_LeftCtrl; break;
                case AKEYCODE_SHIFT_LEFT: imguiKey = ImGuiKey_LeftShift; break;
                case AKEYCODE_ALT_LEFT: imguiKey = ImGuiKey_LeftAlt; break;
                case AKEYCODE_META_LEFT: imguiKey = ImGuiKey_LeftSuper; break;
                case AKEYCODE_CTRL_RIGHT: imguiKey = ImGuiKey_RightCtrl; break;
                case AKEYCODE_SHIFT_RIGHT: imguiKey = ImGuiKey_RightShift; break;
                case AKEYCODE_ALT_RIGHT: imguiKey = ImGuiKey_RightAlt; break;
                case AKEYCODE_META_RIGHT: imguiKey = ImGuiKey_RightSuper; break;
                case AKEYCODE_MENU: imguiKey = ImGuiKey_Menu; break;
                case AKEYCODE_0: imguiKey = ImGuiKey_0; break;
                case AKEYCODE_1: imguiKey = ImGuiKey_1; break;
                case AKEYCODE_2: imguiKey = ImGuiKey_2; break;
                case AKEYCODE_3: imguiKey = ImGuiKey_3; break;
                case AKEYCODE_4: imguiKey = ImGuiKey_4; break;
                case AKEYCODE_5: imguiKey = ImGuiKey_5; break;
                case AKEYCODE_6: imguiKey = ImGuiKey_6; break;
                case AKEYCODE_7: imguiKey = ImGuiKey_7; break;
                case AKEYCODE_8: imguiKey = ImGuiKey_8; break;
                case AKEYCODE_9: imguiKey = ImGuiKey_9; break;
                case AKEYCODE_A: imguiKey = ImGuiKey_A; break;
                case AKEYCODE_B: imguiKey = ImGuiKey_B; break;
                case AKEYCODE_C: imguiKey = ImGuiKey_C; break;
                case AKEYCODE_D: imguiKey = ImGuiKey_D; break;
                case AKEYCODE_E: imguiKey = ImGuiKey_E; break;
                case AKEYCODE_F: imguiKey = ImGuiKey_F; break;
                case AKEYCODE_G: imguiKey = ImGuiKey_G; break;
                case AKEYCODE_H: imguiKey = ImGuiKey_H; break;
                case AKEYCODE_I: imguiKey = ImGuiKey_I; break;
                case AKEYCODE_J: imguiKey = ImGuiKey_J; break;
                case AKEYCODE_K: imguiKey = ImGuiKey_K; break;
                case AKEYCODE_L: imguiKey = ImGuiKey_L; break;
                case AKEYCODE_M: imguiKey = ImGuiKey_M; break;
                case AKEYCODE_N: imguiKey = ImGuiKey_N; break;
                case AKEYCODE_O: imguiKey = ImGuiKey_O; break;
                case AKEYCODE_P: imguiKey = ImGuiKey_P; break;
                case AKEYCODE_Q: imguiKey = ImGuiKey_Q; break;
                case AKEYCODE_R: imguiKey = ImGuiKey_R; break;
                case AKEYCODE_S: imguiKey = ImGuiKey_S; break;
                case AKEYCODE_T: imguiKey = ImGuiKey_T; break;
                case AKEYCODE_U: imguiKey = ImGuiKey_U; break;
                case AKEYCODE_V: imguiKey = ImGuiKey_V; break;
                case AKEYCODE_W: imguiKey = ImGuiKey_W; break;
                case AKEYCODE_X: imguiKey = ImGuiKey_X; break;
                case AKEYCODE_Y: imguiKey = ImGuiKey_Y; break;
                case AKEYCODE_Z: imguiKey = ImGuiKey_Z; break;
                case AKEYCODE_F1: imguiKey = ImGuiKey_F1; break;
                case AKEYCODE_F2: imguiKey = ImGuiKey_F2; break;
                case AKEYCODE_F3: imguiKey = ImGuiKey_F3; break;
                case AKEYCODE_F4: imguiKey = ImGuiKey_F4; break;
                case AKEYCODE_F5: imguiKey = ImGuiKey_F5; break;
                case AKEYCODE_F6: imguiKey = ImGuiKey_F6; break;
                case AKEYCODE_F7: imguiKey = ImGuiKey_F7; break;
                case AKEYCODE_F8: imguiKey = ImGuiKey_F8; break;
                case AKEYCODE_F9: imguiKey = ImGuiKey_F9; break;
                case AKEYCODE_F10: imguiKey = ImGuiKey_F10; break;
                case AKEYCODE_F11: imguiKey = ImGuiKey_F11; break;
                case AKEYCODE_F12: imguiKey = ImGuiKey_F12; break;
            }
            
            if (imguiKey != ImGuiKey_None) {
                // Use the new ImGui input API instead of KeysDown array
                if (action == AKEY_EVENT_ACTION_DOWN) {
                    ImGui::GetIO().AddKeyEvent(imguiKey, true);
                    
                    // Handle modifiers
                    ImGuiIO& io = ImGui::GetIO();
                    io.KeyShift = (metaState & AMETA_SHIFT_ON) != 0;
                    io.KeyCtrl = (metaState & AMETA_CTRL_ON) != 0;
                    io.KeyAlt = (metaState & AMETA_ALT_ON) != 0;
                } else {
                    ImGui::GetIO().AddKeyEvent(imguiKey, false);
                    
                    // Update modifiers
                    ImGuiIO& io = ImGui::GetIO();
                    io.KeyShift = (metaState & AMETA_SHIFT_ON) != 0;
                    io.KeyCtrl = (metaState & AMETA_CTRL_ON) != 0;
                    io.KeyAlt = (metaState & AMETA_ALT_ON) != 0;
                }
                
                return 1;
            }
        }
    }
    
    return 0;
}

// Android main entry point
void android_main(struct android_app* app) {
    app_dummy();
    
    // Create and run the application
    PlatformAndroid platform("ImGui Hello World");
    platform.setAndroidApp(app);  // Use the setter method instead of direct access
    platform.run();
}
