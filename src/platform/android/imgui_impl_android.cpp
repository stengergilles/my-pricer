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
    g_Window = window;
    if (!window) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Null window passed to ImGui_ImplAndroid_Init");
        return false;
    }
    
    // Verify window is valid
    ANativeWindow_acquire(window);
    int32_t windowWidth = ANativeWindow_getWidth(window);
    int32_t windowHeight = ANativeWindow_getHeight(window);
    ANativeWindow_release(window);
    
    if (windowWidth <= 0 || windowHeight <= 0) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Invalid window dimensions");
        return false;
    }
    
    // Initialize EGL
    g_EglDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g_EglDisplay == EGL_NO_DISPLAY) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to get EGL display");
        return false;
    }
    
    EGLint major, minor;
    if (eglInitialize(g_EglDisplay, &major, &minor) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to initialize EGL");
        return false;
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
    
    EGLConfig config;
    EGLint numConfigs;
    if (eglChooseConfig(g_EglDisplay, attribs, &config, 1, &numConfigs) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to choose EGL config");
        return false;
    }
    
    // Create surface
    g_EglSurface = eglCreateWindowSurface(g_EglDisplay, config, g_Window, NULL);
    if (g_EglSurface == EGL_NO_SURFACE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to create EGL surface");
        return false;
    }
    
    // Create context
    EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };
    g_EglContext = eglCreateContext(g_EglDisplay, config, EGL_NO_CONTEXT, contextAttribs);
    if (g_EglContext == EGL_NO_CONTEXT) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to create EGL context");
        return false;
    }
    
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to make EGL context current");
        return false;
    }
    
    // Setup ImGui context with the window dimensions
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    
    // Load DroidSans.ttf font
    io.Fonts->AddFontFromFileTTF("/system/fonts/DroidSans.ttf", 16.0f);
    
    // Create font texture
    unsigned char* pixels;
    int width, height;
    io.Fonts->GetTexDataAsRGBA32(&pixels, &width, &height);
    
    // Upload texture to graphics system
    GLuint font_texture;
    glGenTextures(1, &font_texture);
    glBindTexture(GL_TEXTURE_2D, font_texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
    
    // Store our identifier
    io.Fonts->TexID = (ImTextureID)(intptr_t)font_texture;
    
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
    
    // Make sure the correct context is current
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to make context current in NewFrame");
        return;
    }
    
    ImGuiIO& io = ImGui::GetIO();
    
    // Setup display size (every frame to accommodate for window resizing)
    int32_t windowWidth = ANativeWindow_getWidth(g_Window);
    int32_t windowHeight = ANativeWindow_getHeight(g_Window);
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    
    // Setup time step
    static double g_Time = 0.0;
    double current_time = (double)ImGui::GetTime();
    io.DeltaTime = g_Time > 0.0 ? (float)(current_time - g_Time) : (float)(1.0f / 60.0f);
    g_Time = current_time;
    
    // Verify that the font atlas is built
    if (!io.Fonts->IsBuilt()) {
        // Create font texture
        unsigned char* pixels;
        int width, height;
        io.Fonts->GetTexDataAsRGBA32(&pixels, &width, &height);
        
        // Upload texture to graphics system
        GLuint font_texture;
        glGenTextures(1, &font_texture);
        glBindTexture(GL_TEXTURE_2D, font_texture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
        
        // Store our identifier
        io.Fonts->TexID = (ImTextureID)(intptr_t)font_texture;
    }
}

void ImGui_ImplAndroid_RenderDrawData(ImDrawData* draw_data) {
    if (!g_Initialized || !draw_data)
        return;
    
    // Make sure the correct context is current
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE)
        return;
    
    // Get the current viewport size
    int fb_width = (int)(draw_data->DisplaySize.x * draw_data->FramebufferScale.x);
    int fb_height = (int)(draw_data->DisplaySize.y * draw_data->FramebufferScale.y);
    if (fb_width <= 0 || fb_height <= 0)
        return;
    
    // Setup render state
    glViewport(0, 0, fb_width, fb_height);
    glClearColor(0.1f, 0.1f, 0.1f, 1.0f);  // Dark gray background
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Setup orthographic projection matrix
    const float ortho_projection[4][4] =
    {
        { 2.0f/draw_data->DisplaySize.x, 0.0f,                   0.0f, 0.0f },
        { 0.0f,                  2.0f/-draw_data->DisplaySize.y, 0.0f, 0.0f },
        { 0.0f,                  0.0f,                  -1.0f, 0.0f },
        {-1.0f,                  1.0f,                   0.0f, 1.0f },
    };
    
    // Simple rendering for demonstration purposes
    // In a real implementation, you would use shaders and process all ImGui draw commands
    
    // Swap buffers
    eglSwapBuffers(g_EglDisplay, g_EglSurface);
}
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
