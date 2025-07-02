cmake_minimum_required(VERSION 3.10)
project(imgui_hello_world)
set(PROJECT_ROOT ${CMAKE_SOURCE_DIR})

option(BUILD_TESTS "Build tests" OFF)

# For tests
# Automatically detect if there are any test files
file(GLOB_RECURSE TEST_FILES
    "tests/test_*.cpp"
    "tests/integration_*.cpp"
)

if(BUILD_TESTS AND NOT TEST_FILES)
    message(FATAL_ERROR "BUILD_TESTS is ON, but no test files found in 'tests/' directory. Aborting configuration.")
elseif(NOT TEST_FILES)
    message(STATUS "No test files found in 'tests/' directory. Disabling BUILD_TESTS.")
    set(BUILD_TESTS OFF CACHE BOOL "Build tests" FORCE)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Gtest

if (BUILD_TESTS)
  set(GTEST_ROOT "$ENV{HOME}/.local")
  set(GTEST_INCLUDE_DIR "${GTEST_ROOT}/include")
  set(GTEST_LIBRARY "${GTEST_ROOT}/lib/libgtest.a")
  set(GTEST_MAIN_LIBRARY "${GTEST_ROOT}/lib/libgtest_main.a")
  enable_testing()
else()
  set(GTEST_INCLUDE_DIR "")
endif()

# Prebuild openssl for everything except Android

message(STATUS "CMAKE_SYSTEM_NAME ${CMAKE_SYSTEM_NAME}")
message(STATUS "BUILD_TESTS ${BUILD_TESTS}")

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Android" AND BUILD_TESTS OR EXISTS "/data/data/com.termux/files/usr")
  if(NOT EXISTS "${PROJECT_ROOT}/external/openssl/native/include/openssl/opensslconf.h")
    execute_process(
        COMMAND bash -c "
	    cd ${PROJECT_ROOT}/external/openssl-src
	    ./Configure no-tests --prefix=${PROJECT_ROOT}/external/openssl/native
	    make -j\$(nproc)
	    make install
        "
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        RESULT_VARIABLE OPENSSL_BUILD_RESULT
    )
    if(NOT OPENSSL_BUILD_RESULT EQUAL 0)
        message(FATAL_ERROR "Failed to build OpenSSL!")
    endif()
  endif()
endif()

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include/app
    ${CMAKE_CURRENT_SOURCE_DIR}/external/imgui
    ${CMAKE_CURRENT_SOURCE_DIR}/external/imgui/backends
    ${PROJECT_ROOT}/external/json/include
    ${PROJECT_ROOT}/external/curl/include
    ${GTEST_INCLUDE_DIR}
)

set(SOURCES
    src/application.cpp
    src/platform/platform_base.cpp
    src/main.cpp
    src/http_client_curl.cpp
    src/write_cacert.cpp
    src/tempfile.cpp
)

set(IMGUI_SOURCES
    external/imgui/imgui.cpp
    external/imgui/imgui_demo.cpp
    external/imgui/imgui_draw.cpp
    external/imgui/imgui_tables.cpp
    external/imgui/imgui_widgets.cpp
)

set(APP_MAIN_FILE "${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_main.cpp")
if(EXISTS ${APP_MAIN_FILE})
    list(APPEND SOURCES ${APP_MAIN_FILE})
    add_definitions(-DUSE_EXTERNAL_RENDER_IMGUI)
endif()

# Auto-collect all *.cpp files from src/app
file(GLOB APP_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/src/app/*.cpp")
if(EXISTS ${APP_MAIN_FILE})
    list(REMOVE_ITEM APP_SOURCES ${APP_MAIN_FILE})
endif()
if(APP_SOURCES)
    add_library(appcode STATIC ${APP_SOURCES})
    target_include_directories(appcode PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include/app)
endif()

add_subdirectory(external/json)

# --- OpenSSL & curl reproducible build block ---

if(ANDROID)
    # Set ABI variable if not set by environment
    if(NOT DEFINED ANDROID_ABI)
        if(DEFINED CMAKE_ANDROID_ARCH_ABI)
            set(ANDROID_ABI ${CMAKE_ANDROID_ARCH_ABI})
        else()
            set(ANDROID_ABI "arm64-v8a")
        endif()
    endif()

    set(OPENSSL_ROOT_DIR "${PROJECT_ROOT}/external/openssl/android/${ANDROID_ABI}")
    set(OPENSSL_INCLUDE_DIR "${OPENSSL_ROOT_DIR}/include")
    set(OPENSSL_CRYPTO_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libcrypto.a")
    set(OPENSSL_SSL_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libssl.a")

    # Define imported OpenSSL targets for use by curl and your code
    if(NOT TARGET OpenSSL::SSL)
        add_library(OpenSSL::SSL STATIC IMPORTED GLOBAL)
        set_target_properties(OpenSSL::SSL PROPERTIES
            IMPORTED_LOCATION "${OPENSSL_SSL_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${OPENSSL_INCLUDE_DIR}"
        )
    endif()
    if(NOT TARGET OpenSSL::Crypto)
        add_library(OpenSSL::Crypto STATIC IMPORTED GLOBAL)
        set_target_properties(OpenSSL::Crypto PROPERTIES
            IMPORTED_LOCATION "${OPENSSL_CRYPTO_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${OPENSSL_INCLUDE_DIR}"
        )
    endif()

    set(CURL_USE_OPENSSL ON CACHE BOOL "Use OpenSSL with libcurl" FORCE)
    set(CURL_ENABLE_OPENSSL_AUTO_FETCH OFF CACHE BOOL "" FORCE)
    set(CURL_DISABLE_LIBPSL ON CACHE BOOL "Disable PSL support" FORCE)
    set(CURL_USE_LIBPSL OFF CACHE BOOL "Use PSL support" FORCE)

    add_subdirectory(external/curl)
else()
    # For native platforms, always use project-controlled OpenSSL build
    set(OPENSSL_ROOT_DIR "${PROJECT_ROOT}/external/openssl/native")
    set(OPENSSL_INCLUDE_DIR "${OPENSSL_ROOT_DIR}/include")
    set(OPENSSL_CRYPTO_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libcrypto.a")
    set(OPENSSL_SSL_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libssl.a")

    if(EXISTS "${OPENSSL_SSL_LIBRARY}" AND EXISTS "${OPENSSL_CRYPTO_LIBRARY}")
        if(NOT TARGET OpenSSL::SSL)
            add_library(OpenSSL::SSL STATIC IMPORTED GLOBAL)
            set_target_properties(OpenSSL::SSL PROPERTIES
                IMPORTED_LOCATION "${OPENSSL_SSL_LIBRARY}"
                INTERFACE_INCLUDE_DIRECTORIES "${OPENSSL_INCLUDE_DIR}"
            )
        endif()
        if(NOT TARGET OpenSSL::Crypto)
            add_library(OpenSSL::Crypto STATIC IMPORTED GLOBAL)
            set_target_properties(OpenSSL::Crypto PROPERTIES
                IMPORTED_LOCATION "${OPENSSL_CRYPTO_LIBRARY}"
                INTERFACE_INCLUDE_DIRECTORIES "${OPENSSL_INCLUDE_DIR}"
            )
        endif()
    else()
        message(FATAL_ERROR "OpenSSL libraries not found in ${OPENSSL_ROOT_DIR}. Build OpenSSL before configuring this project.")
    endif()

    set(CURL_USE_OPENSSL ON CACHE BOOL "Use OpenSSL with libcurl" FORCE)
    set(CURL_ENABLE_OPENSSL_AUTO_FETCH OFF CACHE BOOL "" FORCE)
    set(CURL_DISABLE_LIBPSL ON CACHE BOOL "Disable PSL support" FORCE)
    set(CURL_USE_LIBPSL OFF CACHE BOOL "Use PSL support" FORCE)

    add_subdirectory(external/curl)
endif()

get_target_property(CURL_INCLUDE_DIRS libcurl INTERFACE_INCLUDE_DIRECTORIES)

# --- End OpenSSL & curl reproducible build block ---

# Test executables

if(BUILD_TESTS)
  # Create a library with all application sources, excluding main.cpp
  set(LIB_SOURCES ${SOURCES})
  list(REMOVE_ITEM LIB_SOURCES "src/main.cpp")
  
  add_library(app STATIC
      ${LIB_SOURCES}
      ${IMGUI_SOURCES}
  )

  target_link_libraries(app PUBLIC
      CURL::libcurl
      OpenSSL::SSL
      OpenSSL::Crypto
      nlohmann_json::nlohmann_json
  )
  if(TARGET appcode)
      target_link_libraries(app PUBLIC appcode)
  endif()

  # Automatically discover and add tests
  file(GLOB_RECURSE TEST_SOURCES 
      "tests/test_*.cpp"
      "tests/integration_*.cpp"
  )

  foreach(TEST_SOURCE ${TEST_SOURCES})
      # Extract the filename without extension to use as the test name
      string(REGEX REPLACE ".*/([^/]+)\\.cpp$" "\\1" TEST_NAME ${TEST_SOURCE})
      add_executable(${TEST_NAME} ${TEST_SOURCE})
      target_link_libraries(${TEST_NAME} PRIVATE
          app
          "${GTEST_ROOT}/lib/libgtest.a"
          "${GTEST_ROOT}/lib/libgtest_main.a"
          pthread
      )
      add_test(NAME ${TEST_NAME} COMMAND ${TEST_NAME})

      # Add dependency on cacert header for fetcher integration tests
      if (TEST_SOURCE MATCHES "integration_.*_fetcher\.cpp")
          add_dependencies(${TEST_NAME} gen_cacert_header)
      endif()
  endforeach()
endif()
set(CACERT_PEM_URL "https://curl.se/ca/cacert.pem")
set(CACERT_PEM "${CMAKE_BINARY_DIR}/cacert.pem")
set(CACERT_HEADER "${CMAKE_SOURCE_DIR}/include/cacert_pem_data.hpp")

add_custom_command(
    OUTPUT ${CACERT_PEM}
    COMMAND ${CMAKE_COMMAND} -E echo "Downloading cacert.pem..."
    COMMAND ${CMAKE_COMMAND} -E remove -f ${CACERT_PEM}
    COMMAND curl -L -o ${CACERT_PEM} ${CACERT_PEM_URL}
    COMMENT "Downloading latest cacert.pem"
)

add_custom_command(
    OUTPUT ${CACERT_HEADER}
    DEPENDS ${CACERT_PEM}
    COMMAND xxd -i ${CACERT_PEM} > ${CACERT_HEADER}.tmp && mv ${CACERT_HEADER}.tmp ${CACERT_HEADER}
    COMMAND sed -i -e 's|unsigned char .*|unsigned char cacert_pem[] = {|g' "${CACERT_HEADER}"
    COMMAND sed -i -e 's|unsigned int[[:space:]]*.*|unsigned int cacert_pem_len = sizeof\(cacert_pem\)\;|' "${CACERT_HEADER}"
    COMMENT "Generating and fixing cacert_pem_data.hpp"
)

add_custom_target(gen_cacert_header ALL DEPENDS ${CACERT_HEADER})

if(ANDROID AND NOT BUILD_TESTS)
    set(PLATFORM_SOURCES
        src/platform/platform_android.cpp
        src/platform/android/android_native_app_glue.c
        src/platform/android/jni_bridge.cpp
        src/platform/android/android_main.cpp
        src/platform/android/imgui_impl_android.cpp
        src/platform/android/keyboard_helper.cpp
        external/imgui/backends/imgui_impl_opengl3.cpp
    )
    include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/src/platform/android
        ${ANDROID_NDK}/sources/android/native_app_glue
        ${CURL_INCLUDE_DIRS}
        ${PROJECT_ROOT}/external/json/include
        ${CMAKE_CURRENT_SOURCE_DIR}/include/app
    )
    set(PLATFORM_LIBS
        android
        EGL
        GLESv3
        log
        nlohmann_json::nlohmann_json
        CURL::libcurl
        OpenSSL::SSL
        OpenSSL::Crypto
    )
    add_library(${PROJECT_NAME} SHARED ${SOURCES} ${IMGUI_SOURCES} ${PLATFORM_SOURCES})
    target_link_libraries(${PROJECT_NAME} PRIVATE ${PLATFORM_LIBS})
    if(TARGET appcode)
        target_link_libraries(${PROJECT_NAME} PRIVATE appcode)
    endif()
    add_dependencies(${PROJECT_NAME} gen_cacert_header)

elseif(EMSCRIPTEN AND NOT BUILD_TESTS)
    set(PLATFORM_SOURCES
        src/platform/platform_wasm.cpp
        external/imgui/backends/imgui_impl_sdl2.cpp
        external/imgui/backends/imgui_impl_opengl3.cpp
    )
    set(CMAKE_EXECUTABLE_SUFFIX ".html")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s USE_SDL=2 -s WASM=1 -s ALLOW_MEMORY_GROWTH=1 -s USE_WEBGL2=1")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --shell-file ${CMAKE_CURRENT_SOURCE_DIR}/src/platform/wasm/shell.html")
    set(PLATFORM_LIBS
    )
    add_executable(${PROJECT_NAME} ${SOURCES} ${IMGUI_SOURCES} ${PLATFORM_SOURCES})
    target_link_libraries(${PROJECT_NAME} PRIVATE ${PLATFORM_LIBS})
    if(TARGET appcode)
        target_link_libraries(${PROJECT_NAME} PRIVATE appcode)
    endif()
    add_dependencies(${PROJECT_NAME} gen_cacert_header)
else()
    if(NOT BUILD_TESTS)
      set(PLATFORM_SOURCES
          src/platform/platform_glfw.cpp
          external/imgui/backends/imgui_impl_glfw.cpp
          external/imgui/backends/imgui_impl_opengl3.cpp
      )
      if(POLICY CMP0072)
        cmake_policy(SET CMP0072 NEW)
      endif()
      find_package(OpenGL REQUIRED)
      set(PLATFORM_LIBS
        OpenGL::GL
        glfw
        CURL::libcurl
        OpenSSL::SSL
        OpenSSL::Crypto
      )
      if(TARGET appcode)
          list(APPEND PLATFORM_LIBS appcode)
      endif()
      if(APPLE AND NOT BUILD_TESTS)
        find_library(COCOA_LIBRARY Cocoa)
        find_library(IOKIT_LIBRARY IOKit)
        find_library(CORE_FOUNDATION_LIBRARY CoreFoundation)
        find_library(CORE_VIDEO_LIBRARY CoreVideo)
        list(APPEND PLATFORM_LIBS ${COCOA_LIBRARY} ${IOKIT_LIBRARY} ${CORE_FOUNDATION_LIBRARY} ${CORE_VIDEO_LIBRARY})
      endif()
      if(WIN32 AND NOT BUILD_TESTS)
        # Add Windows-specific libraries if needed
      endif()
      add_executable(${PROJECT_NAME} ${SOURCES} ${IMGUI_SOURCES} ${PLATFORM_SOURCES})
      target_link_libraries(${PROJECT_NAME} PRIVATE ${PLATFORM_LIBS})
      add_dependencies(${PROJECT_NAME} gen_cacert_header)
   endif()
endif()



if(NOT ANDROID)
    install(TARGETS ${PROJECT_NAME} DESTINATION bin)
endif()
