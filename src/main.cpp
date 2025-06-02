#include <iostream>

#if defined(__ANDROID__)
    #include "../include/platform/platform_android.h"
    typedef PlatformAndroid PlatformType;
#elif defined(__EMSCRIPTEN__)
    #include "../include/platform/platform_wasm.h"
    typedef PlatformWasm PlatformType;
#else
    // Default to GLFW for desktop platforms (Windows, Linux, macOS)
    #include "../include/platform/platform_glfw.h"
    typedef PlatformGLFW PlatformType;
#endif

int main(int argc, char** argv)
{
    try {
        // Create platform-specific application instance
        PlatformType app("ImGui Hello World");
        
        // Run the application
        app.run();
        
        return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
