#include <android/native_window.h>
#include <android/input.h>
#include <android/keycodes.h>
#include <android/log.h>
#include <GLES3/gl3.h>
#include <EGL/egl.h>
#include <math.h>
#include "imgui.h"

// Data
static EGLDisplay g_EglDisplay = EGL_NO_DISPLAY;
static EGLSurface g_EglSurface = EGL_NO_SURFACE;
static EGLContext g_EglContext = EGL_NO_CONTEXT;
static ANativeWindow* g_Window = NULL;
static bool g_Initialized = false;

// OpenGL Data
static GLuint g_FontTexture = 0;
static GLuint g_ShaderHandle = 0;
static GLuint g_VertHandle = 0;
static GLuint g_FragHandle = 0;
static GLint g_AttribLocationTex = 0;
static GLint g_AttribLocationProjMtx = 0;
static GLint g_AttribLocationPosition = 0;
static GLint g_AttribLocationUV = 0;
static GLint g_AttribLocationColor = 0;
static GLuint g_VboHandle = 0;
static GLuint g_ElementsHandle = 0;

// Shader source code
static const char* g_VertexShaderSource = 
    "uniform mat4 ProjMtx;\n"
    "attribute vec2 Position;\n"
    "attribute vec2 UV;\n"
    "attribute vec4 Color;\n"
    "varying vec2 Frag_UV;\n"
    "varying vec4 Frag_Color;\n"
    "void main()\n"
    "{\n"
    "    Frag_UV = UV;\n"
    "    Frag_Color = Color;\n"
    "    gl_Position = ProjMtx * vec4(Position.xy, 0, 1);\n"
    "}\n";

static const char* g_FragmentShaderSource = 
    "precision mediump float;\n"
    "uniform sampler2D Texture;\n"
    "varying vec2 Frag_UV;\n"
    "varying vec4 Frag_Color;\n"
    "void main()\n"
    "{\n"
    "    gl_FragColor = Frag_Color * texture2D(Texture, Frag_UV);\n"
    "}\n";

// Helper function to check shader compilation/linking errors
static bool CheckShader(GLuint handle, const char* desc)
{
    GLint status = 0, log_length = 0;
    glGetShaderiv(handle, GL_COMPILE_STATUS, &status);
    glGetShaderiv(handle, GL_INFO_LOG_LENGTH, &log_length);
    if (status == GL_FALSE)
    {
        if (log_length > 1)
        {
            char* buf = (char*)malloc(log_length + 1);
            glGetShaderInfoLog(handle, log_length, NULL, buf);
            __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "ERROR: %s shader failed to compile: %s", desc, buf);
            free(buf);
        }
        return false;
    }
    return true;
}

static bool CheckProgram(GLuint handle, const char* desc)
{
    GLint status = 0, log_length = 0;
    glGetProgramiv(handle, GL_LINK_STATUS, &status);
    glGetProgramiv(handle, GL_INFO_LOG_LENGTH, &log_length);
    if (status == GL_FALSE)
    {
        if (log_length > 1)
        {
            char* buf = (char*)malloc(log_length + 1);
            glGetProgramInfoLog(handle, log_length, NULL, buf);
            __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "ERROR: %s program failed to link: %s", desc, buf);
            free(buf);
        }
        return false;
    }
    return true;
}

// Create OpenGL objects (shaders, buffers)
static bool CreateDeviceObjects()
{
    // Create shaders
    g_VertHandle = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(g_VertHandle, 1, &g_VertexShaderSource, 0);
    glCompileShader(g_VertHandle);
    CheckShader(g_VertHandle, "vertex shader");

    g_FragHandle = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(g_FragHandle, 1, &g_FragmentShaderSource, 0);
    glCompileShader(g_FragHandle);
    CheckShader(g_FragHandle, "fragment shader");

    g_ShaderHandle = glCreateProgram();
    glAttachShader(g_ShaderHandle, g_VertHandle);
    glAttachShader(g_ShaderHandle, g_FragHandle);
    glLinkProgram(g_ShaderHandle);
    CheckProgram(g_ShaderHandle, "shader program");

    g_AttribLocationTex = glGetUniformLocation(g_ShaderHandle, "Texture");
    g_AttribLocationProjMtx = glGetUniformLocation(g_ShaderHandle, "ProjMtx");
    g_AttribLocationPosition = glGetAttribLocation(g_ShaderHandle, "Position");
    g_AttribLocationUV = glGetAttribLocation(g_ShaderHandle, "UV");
    g_AttribLocationColor = glGetAttribLocation(g_ShaderHandle, "Color");

    // Create buffers
    glGenBuffers(1, &g_VboHandle);
    glGenBuffers(1, &g_ElementsHandle);

    return true;
}

// Create font texture
static bool CreateFontsTexture()
{
    ImGuiIO& io = ImGui::GetIO();
    
    // Build texture atlas
    unsigned char* pixels;
    int width, height;
    io.Fonts->GetTexDataAsRGBA32(&pixels, &width, &height);
    
    // Upload texture to graphics system
    GLint last_texture;
    glGetIntegerv(GL_TEXTURE_BINDING_2D, &last_texture);
    glGenTextures(1, &g_FontTexture);
    glBindTexture(GL_TEXTURE_2D, g_FontTexture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
    
    // Store our identifier
    io.Fonts->TexID = (ImTextureID)(intptr_t)g_FontTexture;
    
    // Restore state
    glBindTexture(GL_TEXTURE_2D, last_texture);
    
    return true;
}

bool ImGui_ImplAndroid_Init(ANativeWindow* window)
{
    g_Window = window;
    if (!window)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Null window passed to ImGui_ImplAndroid_Init");
        return false;
    }
    
    // Verify window is valid
    ANativeWindow_acquire(window);
    int32_t windowWidth = ANativeWindow_getWidth(window);
    int32_t windowHeight = ANativeWindow_getHeight(window);
    ANativeWindow_release(window);
    
    if (windowWidth <= 0 || windowHeight <= 0)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Invalid window dimensions");
        return false;
    }
    
    // Initialize EGL
    g_EglDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g_EglDisplay == EGL_NO_DISPLAY)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to get EGL display");
        return false;
    }
    
    EGLint major, minor;
    if (eglInitialize(g_EglDisplay, &major, &minor) != EGL_TRUE)
    {
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
    if (eglChooseConfig(g_EglDisplay, attribs, &config, 1, &numConfigs) != EGL_TRUE)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to choose EGL config");
        return false;
    }
    
    // Create surface
    g_EglSurface = eglCreateWindowSurface(g_EglDisplay, config, g_Window, NULL);
    if (g_EglSurface == EGL_NO_SURFACE)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to create EGL surface");
        return false;
    }
    
    // Create context
    EGLint contextAttribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };
    g_EglContext = eglCreateContext(g_EglDisplay, config, EGL_NO_CONTEXT, contextAttribs);
    if (g_EglContext == EGL_NO_CONTEXT)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to create EGL context");
        return false;
    }
    
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE)
    {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to make EGL context current");
        return false;
    }
    
    // Setup ImGui context with the window dimensions
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    
    // Load DroidSans.ttf font
    io.Fonts->AddFontFromFileTTF("/system/fonts/DroidSans.ttf", 16.0f);
    
    // Create OpenGL objects
    CreateDeviceObjects();
    CreateFontsTexture();
    
    g_Initialized = true;
    return true;
}

void ImGui_ImplAndroid_Shutdown()
{
    // Cleanup OpenGL objects
    if (g_VboHandle) glDeleteBuffers(1, &g_VboHandle);
    if (g_ElementsHandle) glDeleteBuffers(1, &g_ElementsHandle);
    g_VboHandle = g_ElementsHandle = 0;
    
    if (g_ShaderHandle && g_VertHandle) glDetachShader(g_ShaderHandle, g_VertHandle);
    if (g_VertHandle) glDeleteShader(g_VertHandle);
    g_VertHandle = 0;
    
    if (g_ShaderHandle && g_FragHandle) glDetachShader(g_ShaderHandle, g_FragHandle);
    if (g_FragHandle) glDeleteShader(g_FragHandle);
    g_FragHandle = 0;
    
    if (g_ShaderHandle) glDeleteProgram(g_ShaderHandle);
    g_ShaderHandle = 0;
    
    if (g_FontTexture)
    {
        glDeleteTextures(1, &g_FontTexture);
        ImGui::GetIO().Fonts->TexID = 0;
        g_FontTexture = 0;
    }
    
    // Cleanup EGL
    if (g_EglDisplay != EGL_NO_DISPLAY)
    {
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

void ImGui_ImplAndroid_NewFrame()
{
    if (!g_Initialized)
        return;
    
    // Make sure the correct context is current
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE)
        return;
    
    ImGuiIO& io = ImGui::GetIO();
    
    // Setup display size (every frame to accommodate for window resizing)
    int32_t windowWidth = ANativeWindow_getWidth(g_Window);
    int32_t windowHeight = ANativeWindow_getHeight(g_Window);
    
    // Set display size and framebuffer scale
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    io.DisplayFramebufferScale = ImVec2(1.0f, 1.0f);
    
    // Setup time step
    static double g_Time = 0.0;
    double current_time = (double)ImGui::GetTime();
    io.DeltaTime = g_Time > 0.0 ? (float)(current_time - g_Time) : (float)(1.0f / 60.0f);
    g_Time = current_time;
    
    // Verify that the font atlas is built
    if (!io.Fonts->IsBuilt())
    {
        CreateFontsTexture();
    }
}

void ImGui_ImplAndroid_RenderDrawData(ImDrawData* draw_data)
{
    if (!g_Initialized || !draw_data)
        return;
    
    // Make sure the correct context is current
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE)
        return;
    
    // Avoid rendering when minimized
    int fb_width = (int)(draw_data->DisplaySize.x * draw_data->FramebufferScale.x);
    int fb_height = (int)(draw_data->DisplaySize.y * draw_data->FramebufferScale.y);
    if (fb_width <= 0 || fb_height <= 0)
        return;
    
    // Setup render state
    glEnable(GL_BLEND);
    glBlendEquation(GL_FUNC_ADD);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_CULL_FACE);
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_SCISSOR_TEST);
    glActiveTexture(GL_TEXTURE0);
    
    // Setup viewport
    glViewport(0, 0, fb_width, fb_height);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f); // Black background
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Setup orthographic projection matrix
    const float ortho_projection[4][4] =
    {
        { 2.0f/draw_data->DisplaySize.x, 0.0f,                   0.0f, 0.0f },
        { 0.0f,                  2.0f/-draw_data->DisplaySize.y, 0.0f, 0.0f },
        { 0.0f,                  0.0f,                  -1.0f, 0.0f },
        {-1.0f,                  1.0f,                   0.0f, 1.0f },
    };
    
    glUseProgram(g_ShaderHandle);
    glUniform1i(g_AttribLocationTex, 0);
    glUniformMatrix4fv(g_AttribLocationProjMtx, 1, GL_FALSE, &ortho_projection[0][0]);
    
    // Render command lists
    for (int n = 0; n < draw_data->CmdListsCount; n++)
    {
        const ImDrawList* cmd_list = draw_data->CmdLists[n];
        
        // Upload vertex and index buffers
        glBindBuffer(GL_ARRAY_BUFFER, g_VboHandle);
        glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)cmd_list->VtxBuffer.Size * sizeof(ImDrawVert), (const GLvoid*)cmd_list->VtxBuffer.Data, GL_STREAM_DRAW);
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, g_ElementsHandle);
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, (GLsizeiptr)cmd_list->IdxBuffer.Size * sizeof(ImDrawIdx), (const GLvoid*)cmd_list->IdxBuffer.Data, GL_STREAM_DRAW);
        
        // Setup attributes for ImDrawVert
        glEnableVertexAttribArray(g_AttribLocationPosition);
        glEnableVertexAttribArray(g_AttribLocationUV);
        glEnableVertexAttribArray(g_AttribLocationColor);
        
        glVertexAttribPointer(g_AttribLocationPosition, 2, GL_FLOAT, GL_FALSE, sizeof(ImDrawVert), (GLvoid*)offsetof(ImDrawVert, pos));
        glVertexAttribPointer(g_AttribLocationUV, 2, GL_FLOAT, GL_FALSE, sizeof(ImDrawVert), (GLvoid*)offsetof(ImDrawVert, uv));
        glVertexAttribPointer(g_AttribLocationColor, 4, GL_UNSIGNED_BYTE, GL_TRUE, sizeof(ImDrawVert), (GLvoid*)offsetof(ImDrawVert, col));
        
        // Draw command lists
        int idx_offset = 0;
        for (int cmd_i = 0; cmd_i < cmd_list->CmdBuffer.Size; cmd_i++)
        {
            const ImDrawCmd* pcmd = &cmd_list->CmdBuffer[cmd_i];
            if (pcmd->UserCallback)
            {
                pcmd->UserCallback(cmd_list, pcmd);
            }
            else
            {
                // Apply scissor/clipping rectangle
                int clip_x = (int)(pcmd->ClipRect.x);
                int clip_y = (int)(pcmd->ClipRect.y);
                int clip_w = (int)(pcmd->ClipRect.z - pcmd->ClipRect.x);
                int clip_h = (int)(pcmd->ClipRect.w - pcmd->ClipRect.y);
                glScissor(clip_x, fb_height - clip_y - clip_h, clip_w, clip_h);
                
                // Bind texture, Draw
                glBindTexture(GL_TEXTURE_2D, (GLuint)(intptr_t)pcmd->TextureId);
                glDrawElements(GL_TRIANGLES, (GLsizei)pcmd->ElemCount, GL_UNSIGNED_SHORT, (void*)(intptr_t)(idx_offset * sizeof(ImDrawIdx)));
            }
            idx_offset += pcmd->ElemCount;
        }
    }
    
    // Restore modified state
    glDisableVertexAttribArray(g_AttribLocationPosition);
    glDisableVertexAttribArray(g_AttribLocationUV);
    glDisableVertexAttribArray(g_AttribLocationColor);
    glDisable(GL_SCISSOR_TEST);
    
    // Swap buffers
    eglSwapBuffers(g_EglDisplay, g_EglSurface);
}

bool ImGui_ImplAndroid_HandleInputEvent(const AInputEvent* event)
{
    if (!g_Initialized)
        return false;
    
    ImGuiIO& io = ImGui::GetIO();
    
    if (AInputEvent_getType(event) == AINPUT_EVENT_TYPE_MOTION)
    {
        int32_t action = AMotionEvent_getAction(event);
        int32_t actionMasked = action & AMOTION_EVENT_ACTION_MASK;
        
        // Get pointer index
        int32_t pointerIndex = (action & AMOTION_EVENT_ACTION_POINTER_INDEX_MASK) >> AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT;
        
        // Get pointer ID and coordinates
        int32_t pointerId = AMotionEvent_getPointerId(event, pointerIndex);
        float x = AMotionEvent_getX(event, pointerIndex);
        float y = AMotionEvent_getY(event, pointerIndex);
        
        // Process touch events
        switch (actionMasked)
        {
            case AMOTION_EVENT_ACTION_DOWN:
            case AMOTION_EVENT_ACTION_POINTER_DOWN:
                io.MouseDown[0] = true;
                io.MousePos = ImVec2(x, y);
                break;
                
            case AMOTION_EVENT_ACTION_MOVE:
                io.MousePos = ImVec2(x, y);
                break;
                
            case AMOTION_EVENT_ACTION_UP:
            case AMOTION_EVENT_ACTION_POINTER_UP:
            case AMOTION_EVENT_ACTION_CANCEL:
                io.MouseDown[0] = false;
                break;
        }
        
        return io.WantCaptureMouse;
    }
    
    return false;
}
