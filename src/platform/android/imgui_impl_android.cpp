#include <android/native_window.h>
#include <android/input.h>
#include <android/keycodes.h>
#include <android/log.h>
#include <GLES3/gl3.h>
#include <EGL/egl.h>
#include <math.h>
#include "imgui.h"

// Based on the official ImGui OpenGL3 backend with Android-specific modifications

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
static GLint g_AttribLocationVtxPos = 0;
static GLint g_AttribLocationVtxUV = 0;
static GLint g_AttribLocationVtxColor = 0;
static GLuint g_VboHandle = 0;
static GLuint g_ElementsHandle = 0;

// Shaders from the official ImGui OpenGL3 backend
static const char* g_VertexShaderGlsl =
    "#version 300 es\n"
    "precision mediump float;\n"
    "layout (location = 0) in vec2 Position;\n"
    "layout (location = 1) in vec2 UV;\n"
    "layout (location = 2) in vec4 Color;\n"
    "uniform mat4 ProjMtx;\n"
    "out vec2 Frag_UV;\n"
    "out vec4 Frag_Color;\n"
    "void main()\n"
    "{\n"
    "    Frag_UV = UV;\n"
    "    Frag_Color = Color;\n"
    "    gl_Position = ProjMtx * vec4(Position.xy, 0, 1);\n"
    "}\n";

static const char* g_FragmentShaderGlsl =
    "#version 300 es\n"
    "precision mediump float;\n"
    "uniform sampler2D Texture;\n"
    "in vec2 Frag_UV;\n"
    "in vec4 Frag_Color;\n"
    "layout (location = 0) out vec4 Out_Color;\n"
    "void main()\n"
    "{\n"
    "    Out_Color = Frag_Color * texture(Texture, Frag_UV.st);\n"
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
    glShaderSource(g_VertHandle, 1, &g_VertexShaderGlsl, 0);
    glCompileShader(g_VertHandle);
    CheckShader(g_VertHandle, "vertex shader");

    g_FragHandle = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(g_FragHandle, 1, &g_FragmentShaderGlsl, 0);
    glCompileShader(g_FragHandle);
    CheckShader(g_FragHandle, "fragment shader");

    g_ShaderHandle = glCreateProgram();
    glAttachShader(g_ShaderHandle, g_VertHandle);
    glAttachShader(g_ShaderHandle, g_FragHandle);
    glLinkProgram(g_ShaderHandle);
    CheckProgram(g_ShaderHandle, "shader program");

    g_AttribLocationTex = glGetUniformLocation(g_ShaderHandle, "Texture");
    g_AttribLocationProjMtx = glGetUniformLocation(g_ShaderHandle, "ProjMtx");
    g_AttribLocationVtxPos = glGetAttribLocation(g_ShaderHandle, "Position");
    g_AttribLocationVtxUV = glGetAttribLocation(g_ShaderHandle, "UV");
    g_AttribLocationVtxColor = glGetAttribLocation(g_ShaderHandle, "Color");

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
    
    // Initialize ImGui IO
    ImGuiIO& io = ImGui::GetIO();
    
    // Verify window is valid
    ANativeWindow_acquire(window);
    int32_t windowWidth = ANativeWindow_getWidth(window);
    int32_t windowHeight = ANativeWindow_getHeight(window);
    ANativeWindow_release(window);
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "ImGui_ImplAndroid_Init with window: %p, dimensions: %dx%d", 
                       window, windowWidth, windowHeight);
    
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
    
    // Update ImGui context with the window dimensions
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    
    // Configure ImGui for Android
    io.ConfigFlags |= ImGuiConfigFlags_IsTouchScreen;
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    
    // Let ImGui handle WantTextInput naturally
    // Do not manually set io.WantTextInput
    
    // Set up style with larger elements for touch
    ImGuiStyle& style = ImGui::GetStyle();
    style.ScaleAllSizes(2.0f);  // Scale up UI elements for touch
    
    // Load DroidSans.ttf font with larger size for touch
    io.Fonts->AddFontFromFileTTF("/system/fonts/DroidSans.ttf", 24.0f);
    
    // Create OpenGL objects
    CreateDeviceObjects();
    CreateFontsTexture();
    
    g_Initialized = true;
    return true;
}

void ImGui_ImplAndroid_Shutdown()
{
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "ImGui_ImplAndroid_Shutdown called");
    
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
        __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Destroying EGL resources");
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
    
    __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "ImGui_ImplAndroid_Shutdown completed");
}

void ImGui_ImplAndroid_NewFrame()
{
    if (!g_Initialized) {
        __android_log_print(ANDROID_LOG_WARN, "ImGuiApp", "ImGui_ImplAndroid_NewFrame called but not initialized");
        return;
    }
    
    // Make sure the correct context is current
    if (eglMakeCurrent(g_EglDisplay, g_EglSurface, g_EglSurface, g_EglContext) != EGL_TRUE) {
        __android_log_print(ANDROID_LOG_ERROR, "ImGuiApp", "Failed to make EGL context current in NewFrame");
        return;
    }
    
    ImGuiIO& io = ImGui::GetIO();
    
    // Setup display size (every frame to accommodate for window resizing)
    int32_t windowWidth = ANativeWindow_getWidth(g_Window);
    int32_t windowHeight = ANativeWindow_getHeight(g_Window);
    
    // Check if orientation changed
    static int32_t lastWidth = 0;
    static int32_t lastHeight = 0;
    bool orientationChanged = (lastWidth != windowWidth || lastHeight != windowHeight);
    
    if (orientationChanged) {
        __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Orientation/size changed: %dx%d -> %dx%d", 
                           lastWidth, lastHeight, windowWidth, windowHeight);
    }
    
    lastWidth = windowWidth;
    lastHeight = windowHeight;
    
    // Set display size based on orientation
    io.DisplaySize = ImVec2((float)windowWidth, (float)windowHeight);
    
    // Calculate display scale based on screen density
    static float displayScale = 1.0f;
    if (orientationChanged) {
        // Get screen density from Android
        ANativeWindow_acquire(g_Window);
        float density = ANativeWindow_getWidth(g_Window) / (float)ANativeWindow_getHeight(g_Window);
        ANativeWindow_release(g_Window);
        
        // Adjust scale based on screen size
        if (windowWidth > 1080 || windowHeight > 1080) {
            displayScale = 2.0f; // High-res screens
        } else if (windowWidth > 720 || windowHeight > 720) {
            displayScale = 1.5f; // Medium-res screens
        } else {
            displayScale = 1.0f; // Low-res screens
        }
        
        // Apply the scale to ImGui
        ImGui::GetStyle().ScaleAllSizes(displayScale);
        io.FontGlobalScale = displayScale;
    }
    
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
    int fb_width = (int)(draw_data->DisplaySize.x);
    int fb_height = (int)(draw_data->DisplaySize.y);
    if (fb_width <= 0 || fb_height <= 0)
        return;
    
    // Backup GL state
    GLint last_active_texture; glGetIntegerv(GL_ACTIVE_TEXTURE, &last_active_texture);
    glActiveTexture(GL_TEXTURE0);
    GLint last_program; glGetIntegerv(GL_CURRENT_PROGRAM, &last_program);
    GLint last_texture; glGetIntegerv(GL_TEXTURE_BINDING_2D, &last_texture);
    GLint last_array_buffer; glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &last_array_buffer);
    GLint last_element_array_buffer; glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING, &last_element_array_buffer);
    GLint last_vertex_array; glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &last_vertex_array);
    GLint last_blend_src_rgb; glGetIntegerv(GL_BLEND_SRC_RGB, &last_blend_src_rgb);
    GLint last_blend_dst_rgb; glGetIntegerv(GL_BLEND_DST_RGB, &last_blend_dst_rgb);
    GLint last_blend_src_alpha; glGetIntegerv(GL_BLEND_SRC_ALPHA, &last_blend_src_alpha);
    GLint last_blend_dst_alpha; glGetIntegerv(GL_BLEND_DST_ALPHA, &last_blend_dst_alpha);
    GLint last_blend_equation_rgb; glGetIntegerv(GL_BLEND_EQUATION_RGB, &last_blend_equation_rgb);
    GLint last_blend_equation_alpha; glGetIntegerv(GL_BLEND_EQUATION_ALPHA, &last_blend_equation_alpha);
    GLint last_viewport[4]; glGetIntegerv(GL_VIEWPORT, last_viewport);
    GLint last_scissor_box[4]; glGetIntegerv(GL_SCISSOR_BOX, last_scissor_box);
    GLboolean last_enable_blend = glIsEnabled(GL_BLEND);
    GLboolean last_enable_cull_face = glIsEnabled(GL_CULL_FACE);
    GLboolean last_enable_depth_test = glIsEnabled(GL_DEPTH_TEST);
    GLboolean last_enable_scissor_test = glIsEnabled(GL_SCISSOR_TEST);
    
    // Setup render state
    glEnable(GL_BLEND);
    glBlendEquation(GL_FUNC_ADD);
    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_CULL_FACE);
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_SCISSOR_TEST);
    
    // Setup viewport
    glViewport(0, 0, fb_width, fb_height);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Setup orthographic projection matrix
    // For Android, we need to flip the Y axis
    float L = 0.0f;
    float R = draw_data->DisplaySize.x;
    float T = 0.0f;
    float B = draw_data->DisplaySize.y;
    
    // Detect orientation
    bool isPortrait = fb_height > fb_width;
    
    // This projection matrix works for Android's coordinate system
    float ortho_projection[4][4];
    
    // Always use the standard projection matrix for Android
    // This is the key to fixing the orientation issue
    ortho_projection[0][0] = 2.0f/(R-L);
    ortho_projection[0][1] = 0.0f;
    ortho_projection[0][2] = 0.0f;
    ortho_projection[0][3] = 0.0f;
    
    ortho_projection[1][0] = 0.0f;
    ortho_projection[1][1] = 2.0f/(T-B);  // Standard Y axis
    ortho_projection[1][2] = 0.0f;
    ortho_projection[1][3] = 0.0f;
    
    ortho_projection[2][0] = 0.0f;
    ortho_projection[2][1] = 0.0f;
    ortho_projection[2][2] = -1.0f;
    ortho_projection[2][3] = 0.0f;
    
    ortho_projection[3][0] = (R+L)/(L-R);
    ortho_projection[3][1] = (T+B)/(B-T);
    ortho_projection[3][2] = 0.0f;
    ortho_projection[3][3] = 1.0f;
    
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
        glEnableVertexAttribArray(g_AttribLocationVtxPos);
        glEnableVertexAttribArray(g_AttribLocationVtxUV);
        glEnableVertexAttribArray(g_AttribLocationVtxColor);
        
        glVertexAttribPointer(g_AttribLocationVtxPos, 2, GL_FLOAT, GL_FALSE, sizeof(ImDrawVert), (GLvoid*)offsetof(ImDrawVert, pos));
        glVertexAttribPointer(g_AttribLocationVtxUV, 2, GL_FLOAT, GL_FALSE, sizeof(ImDrawVert), (GLvoid*)offsetof(ImDrawVert, uv));
        glVertexAttribPointer(g_AttribLocationVtxColor, 4, GL_UNSIGNED_BYTE, GL_TRUE, sizeof(ImDrawVert), (GLvoid*)offsetof(ImDrawVert, col));
        
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
                // Apply scissor/clipping rectangle - adjusted for Android
                int scissor_x = (int)(pcmd->ClipRect.x);
                int scissor_y = (int)(fb_height - pcmd->ClipRect.w);  // Standard OpenGL Y-flip
                int scissor_w = (int)(pcmd->ClipRect.z - pcmd->ClipRect.x);
                int scissor_h = (int)(pcmd->ClipRect.w - pcmd->ClipRect.y);
                
                // Ensure scissor rectangle is valid
                if (scissor_x < 0) scissor_x = 0;
                if (scissor_y < 0) scissor_y = 0;
                if (scissor_w < 0) scissor_w = 0;
                if (scissor_h < 0) scissor_h = 0;
                
                glScissor(scissor_x, scissor_y, scissor_w, scissor_h);
                
                // Bind texture, Draw
                glBindTexture(GL_TEXTURE_2D, (GLuint)(intptr_t)pcmd->TextureId);
                glDrawElements(GL_TRIANGLES, (GLsizei)pcmd->ElemCount, sizeof(ImDrawIdx) == 2 ? GL_UNSIGNED_SHORT : GL_UNSIGNED_INT, (void*)(intptr_t)(idx_offset * sizeof(ImDrawIdx)));
            }
            idx_offset += pcmd->ElemCount;
        }
    }
    
    // Restore modified GL state
    glUseProgram(last_program);
    glBindTexture(GL_TEXTURE_2D, last_texture);
    glBindBuffer(GL_ARRAY_BUFFER, last_array_buffer);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, last_element_array_buffer);
    glBlendEquationSeparate(last_blend_equation_rgb, last_blend_equation_alpha);
    glBlendFuncSeparate(last_blend_src_rgb, last_blend_dst_rgb, last_blend_src_alpha, last_blend_dst_alpha);
    if (last_enable_blend) glEnable(GL_BLEND); else glDisable(GL_BLEND);
    if (last_enable_cull_face) glEnable(GL_CULL_FACE); else glDisable(GL_CULL_FACE);
    if (last_enable_depth_test) glEnable(GL_DEPTH_TEST); else glDisable(GL_DEPTH_TEST);
    if (last_enable_scissor_test) glEnable(GL_SCISSOR_TEST); else glDisable(GL_SCISSOR_TEST);
    glViewport(last_viewport[0], last_viewport[1], (GLsizei)last_viewport[2], (GLsizei)last_viewport[3]);
    glScissor(last_scissor_box[0], last_scissor_box[1], (GLsizei)last_scissor_box[2], (GLsizei)last_scissor_box[3]);
    
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
        
        // Log touch events for debugging
        __android_log_print(ANDROID_LOG_INFO, "ImGuiApp", "Touch event: action=%d, x=%f, y=%f", actionMasked, x, y);
        
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
        
        return true; // Return true to indicate we handled the event
    }
    
    return false;
}
