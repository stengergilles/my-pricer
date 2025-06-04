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
    
    # Python integration
    if(ANDROID)
        # For Android, use the Python headers from Chaquopy
        if(DEFINED PYTHON_INCLUDE_DIR)
            # Use the Python include directory provided by Gradle
            include_directories(${PYTHON_INCLUDE_DIR})
            message(STATUS "Using Python headers from: ${PYTHON_INCLUDE_DIR}")
            
            # Define a macro to indicate we're using Python
            add_definitions(-DWITH_PYTHON)
        else()
            # Try several possible locations for Python headers
            set(POSSIBLE_PYTHON_INCLUDE_DIRS
                "${CMAKE_CURRENT_SOURCE_DIR}/android/app/build/generated/chaquopy/include/python3.11"
                "${ANDROID_NDK}/sources/python/3.11/include/python"
                "${ANDROID_NDK}/sources/python/3.11/include"
                "${CMAKE_CURRENT_SOURCE_DIR}/android/app/src/main/python/include"
                "${CMAKE_CURRENT_SOURCE_DIR}/android/app/.cxx/python/include"
                "$ENV{HOME}/.chaquopy/3.11/include/python3.11"
                "$ENV{PREFIX}/include/python3.11"
            )
            
            # Find the first valid Python include directory
            foreach(PYTHON_DIR ${POSSIBLE_PYTHON_INCLUDE_DIRS})
                if(EXISTS "${PYTHON_DIR}/Python.h")
                    set(PYTHON_INCLUDE_DIR "${PYTHON_DIR}")
                    break()
                endif()
            endforeach()
            
            # If we found a valid Python include directory
            if(DEFINED PYTHON_INCLUDE_DIR)
                include_directories(${PYTHON_INCLUDE_DIR})
                message(STATUS "Using Python headers from: ${PYTHON_INCLUDE_DIR}")
                
                # Define a macro to indicate we're using Python
                add_definitions(-DWITH_PYTHON)
            else()
                # If we couldn't find Python headers, we'll build without Python support
                message(WARNING "Python headers not found. Building without Python support.")
                add_definitions(-DNO_PYTHON)
            endif()
        endif()
    else()
        # For non-Android platforms, use find_package
        find_package(Python3 COMPONENTS Development)
        if(Python3_FOUND)
            include_directories(${Python3_INCLUDE_DIRS})
            message(STATUS "Found Python3: ${Python3_INCLUDE_DIRS}")
            add_definitions(-DWITH_PYTHON)
        else()
            message(WARNING "Python3 development package not found. Building without Python support.")
            add_definitions(-DNO_PYTHON)
        endif()
    endif()
    
    set(PLATFORM_SOURCES
        src/platform/platform_android.cpp
        src/platform/android/android_native_app_glue.c
        src/platform/android/jni_bridge.cpp
        src/platform/android/python_jni_bridge.cpp
        src/platform/android/android_main.cpp
        src/platform/android/imgui_impl_android.cpp
        src/platform/android/keyboard_helper.cpp
        src/python_bridge.cpp
        external/imgui/backends/imgui_impl_opengl3.cpp
    )
    
    # Include Android-specific directories
    include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/src/platform/android
        ${ANDROID_NDK}/sources/android/native_app_glue
    )
    
    # Android-specific libraries
    set(PLATFORM_LIBS
        android
        EGL
        GLESv3
        log
    )
    
    # Find and link Python library
    if(DEFINED PYTHON_LIB_DIR)
        find_library(PYTHON_LIBRARY 
                    NAMES python3.11 python3 python
                    PATHS "${PYTHON_LIB_DIR}/${ANDROID_ABI}"
                          "${PYTHON_LIB_DIR}/arm64-v8a"
                          "${PYTHON_LIB_DIR}/armeabi-v7a"
                          "${PYTHON_LIB_DIR}/x86"
                          "${PYTHON_LIB_DIR}/x86_64"
                    NO_DEFAULT_PATH)
        if(PYTHON_LIBRARY)
            message(STATUS "Found Python library: ${PYTHON_LIBRARY}")
            list(APPEND PLATFORM_LIBS ${PYTHON_LIBRARY})
        else()
            message(WARNING "Python library not found in ${PYTHON_LIB_DIR}")
            # Try to find it in system paths
            find_library(PYTHON_LIBRARY python3.11)
            if(PYTHON_LIBRARY)
                message(STATUS "Found Python library in system paths: ${PYTHON_LIBRARY}")
                list(APPEND PLATFORM_LIBS ${PYTHON_LIBRARY})
            else()
                message(WARNING "Python library not found. Python functionality will not be available.")
            endif()
        endif()
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
