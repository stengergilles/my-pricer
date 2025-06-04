cmake_minimum_required(VERSION 3.10)
project(imgui_hello_world)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/include
    ${CMAKE_CURRENT_SOURCE_DIR}/external/imgui
    ${CMAKE_CURRENT_SOURCE_DIR}/external/imgui/backends
)

# Source files
set(SOURCES
    src/application.cpp
    src/platform/platform_base.cpp
    src/main.cpp
)

# ImGui source files
set(IMGUI_SOURCES
    external/imgui/imgui.cpp
    external/imgui/imgui_demo.cpp
    external/imgui/imgui_draw.cpp
    external/imgui/imgui_tables.cpp
    external/imgui/imgui_widgets.cpp
)

# Platform-specific source files and libraries
if(ANDROID)
    # Android-specific setup
    # Don't specify a C++ standard library explicitly
    # Let the NDK use its default (libc++)
    
    # Define a macro to indicate we're not using Python
    add_definitions(-DNO_PYTHON)
    
    set(PLATFORM_SOURCES
        src/platform/platform_android.cpp
        src/platform/android/android_native_app_glue.c
        src/platform/android/jni_bridge.cpp
        src/platform/android/android_main.cpp
        src/platform/android/imgui_impl_android.cpp
        src/platform/android/keyboard_helper.cpp
        src/openssl_wrapper.cpp
        external/imgui/backends/imgui_impl_opengl3.cpp
    )
    
    # Include Android-specific directories
    include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/src/platform/android
        ${ANDROID_NDK}/sources/android/native_app_glue
    )
    
    # Find OpenSSL
    if(DEFINED OPENSSL_ROOT_DIR)
        message(STATUS "Using OpenSSL from: ${OPENSSL_ROOT_DIR}")
        
        # Set OpenSSL include and library paths based on the current ABI
        if(ANDROID_ABI)
            set(OPENSSL_INCLUDE_DIR "${OPENSSL_ROOT_DIR}/${ANDROID_ABI}/include")
            set(OPENSSL_CRYPTO_LIBRARY "${OPENSSL_ROOT_DIR}/${ANDROID_ABI}/lib/libcrypto.a")
            set(OPENSSL_SSL_LIBRARY "${OPENSSL_ROOT_DIR}/${ANDROID_ABI}/lib/libssl.a")
            
            include_directories(${OPENSSL_INCLUDE_DIR})
            message(STATUS "OpenSSL include dir: ${OPENSSL_INCLUDE_DIR}")
            message(STATUS "OpenSSL crypto library: ${OPENSSL_CRYPTO_LIBRARY}")
            message(STATUS "OpenSSL SSL library: ${OPENSSL_SSL_LIBRARY}")
        else()
            message(WARNING "ANDROID_ABI not defined, cannot set OpenSSL paths correctly")
        endif()
    else()
        message(WARNING "OPENSSL_ROOT_DIR not defined, OpenSSL support will be disabled")
    endif()
    
    # Android-specific libraries
    set(PLATFORM_LIBS
        android
        EGL
        GLESv3
        log
    )
    
    # Add OpenSSL libraries if available
    if(DEFINED OPENSSL_CRYPTO_LIBRARY AND DEFINED OPENSSL_SSL_LIBRARY)
        list(APPEND PLATFORM_LIBS ${OPENSSL_SSL_LIBRARY} ${OPENSSL_CRYPTO_LIBRARY})
    endif()
    
    # Set to build a shared library for Android
    add_library(${PROJECT_NAME} SHARED ${SOURCES} ${IMGUI_SOURCES} ${PLATFORM_SOURCES})
elseif(EMSCRIPTEN)
    # WebAssembly-specific setup
    set(PLATFORM_SOURCES
        src/platform/platform_wasm.cpp
        external/imgui/backends/imgui_impl_sdl2.cpp
        external/imgui/backends/imgui_impl_opengl3.cpp
    )
    
    # Emscripten-specific settings
    set(CMAKE_EXECUTABLE_SUFFIX ".html")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s USE_SDL=2 -s WASM=1 -s ALLOW_MEMORY_GROWTH=1 -s USE_WEBGL2=1")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --shell-file ${CMAKE_CURRENT_SOURCE_DIR}/src/platform/wasm/shell.html")
    
    # No additional libraries needed for Emscripten
    set(PLATFORM_LIBS)
    
    # Create executable for WebAssembly
    add_executable(${PROJECT_NAME} ${SOURCES} ${IMGUI_SOURCES} ${PLATFORM_SOURCES})
else()
    # Desktop platforms (Windows, Linux, macOS)
    set(PLATFORM_SOURCES
        src/platform/platform_glfw.cpp
        external/imgui/backends/imgui_impl_glfw.cpp
        external/imgui/backends/imgui_impl_opengl3.cpp
    )
    
    # Find required packages
    find_package(OpenGL REQUIRED)
    
    # Platform-specific libraries
    set(PLATFORM_LIBS
        OpenGL::GL
        glfw
    )
    
    # macOS-specific settings
    if(APPLE)
        find_library(COCOA_LIBRARY Cocoa)
        find_library(IOKIT_LIBRARY IOKit)
        find_library(CORE_FOUNDATION_LIBRARY CoreFoundation)
        find_library(CORE_VIDEO_LIBRARY CoreVideo)
        list(APPEND PLATFORM_LIBS ${COCOA_LIBRARY} ${IOKIT_LIBRARY} ${CORE_FOUNDATION_LIBRARY} ${CORE_VIDEO_LIBRARY})
    endif()
    
    # Windows-specific settings
    if(WIN32)
        # Add Windows-specific libraries if needed
    endif()
    
    # Create executable for desktop platforms
    add_executable(${PROJECT_NAME} ${SOURCES} ${IMGUI_SOURCES} ${PLATFORM_SOURCES})
endif()

# Link libraries
target_link_libraries(${PROJECT_NAME} ${PLATFORM_LIBS})

# Installation
if(NOT ANDROID)
    install(TARGETS ${PROJECT_NAME} DESTINATION bin)
endif()
