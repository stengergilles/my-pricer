# Dear ImGui Hello World Application

This is a cross-platform Dear ImGui hello world application that can be built for multiple platforms including:
- Android
- Linux
- Windows
- macOS
- WebAssembly (WASM)

## Project Structure

The application is designed with a clean separation between platform-specific code and ImGui rendering code:

```
my-pricer/
├── include/                     # Header files
│   ├── application.h            # Main application interface
│   └── platform/                # Platform-specific headers
│       ├── platform_base.h      # Base platform class
│       ├── platform_glfw.h      # GLFW implementation (desktop)
│       ├── platform_android.h   # Android implementation
│       └── platform_wasm.h      # WebAssembly implementation
├── src/                         # Source files
│   ├── application.cpp          # Platform-independent application code
│   ├── main.cpp                 # Entry point
│   └── platform/                # Platform-specific implementations
│       ├── platform_base.cpp    # Base platform implementation
│       ├── platform_glfw.cpp    # GLFW implementation (desktop)
│       ├── platform_android.cpp # Android implementation
│       └── platform_wasm.cpp    # WebAssembly implementation
├── external/                    # External dependencies
│   └── imgui/                   # Dear ImGui library
├── build/                       # Build directory
└── CMakeLists.txt               # CMake build configuration
```

## Building the Application

### Prerequisites

- CMake 3.10 or higher
- C++17 compatible compiler
- Platform-specific dependencies:
  - Desktop: GLFW3 and OpenGL
  - Android: Android NDK
  - WebAssembly: Emscripten SDK

### Getting Dear ImGui

Before building, you need to download Dear ImGui:

```bash
mkdir -p external
git clone https://github.com/ocornut/imgui.git external/imgui
```

### Building for Desktop (Linux, Windows, macOS)

```bash
mkdir -p build && cd build
cmake ..
make
```

### Building for WebAssembly

```bash
mkdir -p build_wasm && cd build_wasm
emcmake cmake ..
emmake make
```

### Building for Android

```bash
mkdir -p build_android && cd build_android
cmake .. -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
         -DANDROID_ABI=arm64-v8a \
         -DANDROID_PLATFORM=android-24
make
```

## Architecture

The application uses a clean architecture that separates platform-specific code from the ImGui rendering code:

1. `Application` class: Handles the platform-independent ImGui setup and rendering
2. `PlatformBase` class: Abstract base class for platform-specific implementations
3. Platform implementations:
   - `PlatformGLFW`: For desktop platforms (Windows, Linux, macOS)
   - `PlatformAndroid`: For Android
   - `PlatformWasm`: For WebAssembly

This design allows for easy extension to other platforms while keeping the ImGui code consistent across all platforms.

## License

This project is licensed under the MIT License.
