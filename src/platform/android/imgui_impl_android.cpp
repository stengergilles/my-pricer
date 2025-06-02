#include <android/native_window.h>
#include <android/input.h>
#include <android/keycodes.h>
#include <android/log.h>
#include <GLES3/gl3.h>
#include <EGL/egl.h>
#include <math.h>  // For sin function
#include "imgui.h"

// Simple implementation of ImGui_ImplAndroid functions
// This is a minimal implementation - you might want to replace this with the official ImGui Android backend

// Data
static EGLDisplay g_EglDisplay = EGL_NO_DISPLAY;
static EGLSurface g_EglSurface = EGL_NO_SURFACE;
static EGLContext g_EglContext = EGL_NO_CONTEXT;
static ANativeWindow* g_Window = NULL;
static bool g_Initialized = false;

bool ImGui_ImplAndroid_Init(ANativeWindow* window) {
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "ImGui_ImplAndroid_Init called with window: %p", window);
    
    g_Window = window;
    if (!window) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Null window passed to ImGui_ImplAndroid_Init");
        return false;
    }
    
    // Verify window is valid
    ANativeWindow_acquire(window);
    int32_t windowWidth = ANativeWindow_getWidth(window);
    int32_t windowHeight = ANativeWindow_getHeight(window);
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Window dimensions: %dx%d", windowWidth, windowHeight);
    ANativeWindow_release(window);
    
    if (windowWidth <= 0 || windowHeight <= 0) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Invalid window dimensions: %dx%d", windowWidth, windowHeight);
        return false;
    }
    
    // Initialize EGL
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Getting EGL display");
    g_EglDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g_EglDisplay == EGL_NO_DISPLAY) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to get EGL display: %d", eglGetError());
        return false;
    }
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Initializing EGL");
    EGLint major, minor;
    if (eglInitialize(g_EglDisplay, &major, &minor) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to initialize EGL: %d", eglGetError());
        return false;
    }
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "EGL initialized: version %d.%d", major, minor);
    
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
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Choosing EGL config");
    EGLConfig config;
    EGLint numConfigs;
    if (eglChooseConfig(g_EglDisplay, attribs, &config, 1, &numConfigs) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to choose EGL config: %d", eglGetError());
        return false;
    }
    
    // Create surface
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Creating window surface");
    g_EglSurface = eglCreateWindowSurface(g_EglDisplay, config, g_Window, NULL);
    if (g_EglSurface == EGL_NO_SURFACE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to create EGL surface: %d", eglGetError());
        return false;
    }
    
    // Create context
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Creating EGL context");
    EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };
    g_EglContext = eglCreateContext(g_EglDisplay, config, EGL_NO_CONTEXT, contextAttribs);
    if (g_EglContext == EGL_NO_CONTEXT) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to create EGL context: %d", eglGetError());
        return false;
    }
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Making EGL context current");
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to make EGL context current: %d", eglGetError());
        return false;
    }
    
    // Setup ImGui context with the window dimensions we already retrieved
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Set ImGui display size: %dx%d", windowWidth, windowHeight);
    
    // Initialize OpenGL ES
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "OpenGL version: %s", glGetString(GL_VERSION));
    
    g_Initialized = true;
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "ImGui_ImplAndroid_Init completed successfully");
    return true;
}

void ImGui_ImplAndroid_Shutdown() {
    if (g_EglDisplay != EGL_NO_DISPLAY) {
        eglMakeCurrent(g_EglDisplay, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        
        if (g_EglContext != EGL_NO_CONTEXT)
            eglDestroyContext(g_EglDisplay, g_EglContext);
        
        if (g_EglSurface != EGL_NO_SURFACE)
            eglDestroySurface(g_EglDisplay, g_EglSurface);
        
        eglTerminate(g_EglDisplay);
    }
    
    g_EglDisplay = EGL_NO_DISPLAY;
    g_EglContext = EGL_NO_CONTEXT;
    g_EglSurface = EGL_NO_SURFACE;
    g_Window = NULL;
    g_Initialized = false;
}

void ImGui_ImplAndroid_NewFrame() {
    if (!g_Initialized)
        return;
    
    ImGuiIO& io = ImGui::GetIO();
    
    // Setup time step using a simpler approach without timespec
    static double g_Time = 0.0;
    double current_time = (double)ImGui::GetTime();  // Use ImGui's built-in time function
    io.DeltaTime = g_Time > 0.0 ? (float)(current_time - g_Time) : (float)(1.0f / 60.0f);
    g_Time = current_time;
    
    // Start the Dear ImGui frame
    ImGui::NewFrame();
}

void ImGui_ImplAndroid_RenderDrawData(ImDrawData* draw_data) {
    if (!g_Initialized) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Trying to render with uninitialized ImGui");
        return;
    }
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Rendering frame with draw_data: %p", draw_data);
    
    // Make sure the correct context is current
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to make context current for rendering: %d", eglGetError());
        return;
    }
    
    // Get the current viewport size
    ImGuiIO& io = ImGui::GetIO();
    int width = (int)io.DisplaySize.x;
    int height = (int)io.DisplaySize.y;
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Viewport size: %dx%d", width, height);
    
    // Clear the screen with a bright color to verify rendering is working
    glViewport(0, 0, width, height);
    glClearColor(1.0f, 0.0f, 1.0f, 1.0f);  // Bright magenta for visibility
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Draw a simple test pattern with more visible colors
    static float time = 0.0f;
    time += io.DeltaTime;
    
    // Draw a moving green square
    int squareSize = height / 3;
    int x = (int)(width/2 + sin(time) * (width/4 - squareSize/2)) - squareSize/2;
    int y = height/2 - squareSize/2;
    
    glEnable(GL_SCISSOR_TEST);
    glScissor(x, y, squareSize, squareSize);
    glClearColor(0.0f, 1.0f, 0.0f, 1.0f);  // Bright green
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Draw a yellow square in the corner
    glScissor(0, 0, squareSize/2, squareSize/2);
    glClearColor(1.0f, 1.0f, 0.0f, 1.0f);  // Bright yellow
    glClear(GL_COLOR_BUFFER_BIT);
    glDisable(GL_SCISSOR_TEST);
    
    // Swap buffers
    if (eglSwapBuffers(g_EglDisplay, g_EglSurface) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to swap buffers: %d", eglGetError());
    } else {
        __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Successfully swapped buffers");
    }
}

bool ImGui_ImplAndroid_HandleInputEvent(const AInputEvent* event) {
    if (!g_Initialized)
        return false;
    
    ImGuiIO& io = ImGui::GetIO();
    
    if (AInputEvent_getType(event) == AINPUT_EVENT_TYPE_MOTION) {
        // Handle touch input
        int32_t action = AMotionEvent_getAction(event);
        int32_t pointerIndex = (action & AMOTION_EVENT_ACTION_POINTER_INDEX_MASK) >> AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT;
        int32_t pointerId = AMotionEvent_getPointerId(event, pointerIndex);
        int32_t actionMasked = action & AMOTION_EVENT_ACTION_MASK;
        
        switch (actionMasked) {
            case AMOTION_EVENT_ACTION_DOWN:
            case AMOTION_EVENT_ACTION_POINTER_DOWN:
                io.MouseDown[0] = true;
                io.MousePos = ImVec2(AMotionEvent_getX(event, pointerIndex), AMotionEvent_getY(event, pointerIndex));
                return io.WantCaptureMouse;
                
            case AMOTION_EVENT_ACTION_MOVE:
                io.MousePos = ImVec2(AMotionEvent_getX(event, pointerIndex), AMotionEvent_getY(event, pointerIndex));
                return io.WantCaptureMouse;
                
            case AMOTION_EVENT_ACTION_UP:
            case AMOTION_EVENT_ACTION_POINTER_UP:
                io.MouseDown[0] = false;
                return io.WantCaptureMouse;
        }
    }
    
    return false;
}
