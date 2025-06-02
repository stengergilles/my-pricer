#include <android/native_window.h>
#include <android/input.h>
#include <android/keycodes.h>
#include <android/log.h>
#include <GLES3/gl3.h>
#include <EGL/egl.h>
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
    g_Window = window;
    
    // Initialize EGL
    g_EglDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g_EglDisplay == EGL_NO_DISPLAY)
        return false;
    
    if (eglInitialize(g_EglDisplay, 0, 0) != EGL_TRUE)
        return false;
    
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
    
    EGLConfig config;
    EGLint numConfigs;
    if (eglChooseConfig(g_EglDisplay, attribs, &config, 1, &numConfigs) != EGL_TRUE)
        return false;
    
    // Create surface
    g_EglSurface = eglCreateWindowSurface(g_EglDisplay, config, g_Window, NULL);
    if (g_EglSurface == EGL_NO_SURFACE)
        return false;
    
    // Create context
    EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };
    g_EglContext = eglCreateContext(g_EglDisplay, config, EGL_NO_CONTEXT, contextAttribs);
    if (g_EglContext == EGL_NO_CONTEXT)
        return false;
    
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE)
        return false;
    
    // Setup ImGui context
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    
    // Setup display size
    int32_t width = ANativeWindow_getWidth(g_Window);
    int32_t height = ANativeWindow_getHeight(g_Window);
    io.DisplaySize = ImVec2((float)width, (float)height);
    
    g_Initialized = true;
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
    
    // Setup time step
    static double g_Time = 0.0;
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    double current_time = now.tv_sec + now.tv_nsec / 1000000000.0;
    io.DeltaTime = g_Time > 0.0 ? (float)(current_time - g_Time) : (float)(1.0f / 60.0f);
    g_Time = current_time;
    
    // Start the Dear ImGui frame
    ImGui::NewFrame();
}

void ImGui_ImplAndroid_RenderDrawData(ImDrawData* draw_data) {
    if (!g_Initialized)
        return;
    
    // Rendering
    ImVec4 clear_color = ImVec4(0.45f, 0.55f, 0.60f, 1.00f);
    glViewport(0, 0, (int)ImGui::GetIO().DisplaySize.x, (int)ImGui::GetIO().DisplaySize.y);
    glClearColor(clear_color.x, clear_color.y, clear_color.z, clear_color.w);
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Render ImGui (this is a simplified version - you should use proper rendering)
    // In a real implementation, you would use ImGui_ImplOpenGL3_RenderDrawData(draw_data)
    
    // Swap buffers
    eglSwapBuffers(g_EglDisplay, g_EglSurface);
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
