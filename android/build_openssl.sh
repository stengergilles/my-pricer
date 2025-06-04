#!/bin/bash

# Script to build OpenSSL for Android
# This script provides a manual way to build OpenSSL if the Gradle task isn't working

set -e  # Exit on error

# Configuration
OPENSSL_VERSION="3.0.4"
DOWNLOAD_URL="https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"
BUILD_DIR="$(pwd)/app/build"
OPENSSL_SRC_DIR="${BUILD_DIR}/openssl-${OPENSSL_VERSION}"
OPENSSL_ARCHIVE="${BUILD_DIR}/openssl-${OPENSSL_VERSION}.tar.gz"

# Get Android NDK path from local.properties or environment
if [ -f "local.properties" ]; then
    NDK_DIR=$(grep -o "ndk.dir=.*" local.properties | cut -d'=' -f2)
fi

if [ -z "$NDK_DIR" ]; then
    if [ -z "$ANDROID_NDK_HOME" ]; then
        echo "Error: Android NDK path not found. Set ANDROID_NDK_HOME environment variable."
        exit 1
    else
        NDK_DIR="$ANDROID_NDK_HOME"
    fi
fi

echo "Using Android NDK at: $NDK_DIR"

# Android API level
API_LEVEL=21

# ABIs to build for
ABIS=("armeabi-v7a" "arm64-v8a" "x86" "x86_64")

# Create build directory
mkdir -p "$BUILD_DIR"

# Download OpenSSL if needed
if [ ! -f "$OPENSSL_ARCHIVE" ]; then
    echo "Downloading OpenSSL ${OPENSSL_VERSION}..."
    curl -L "$DOWNLOAD_URL" -o "$OPENSSL_ARCHIVE"
fi

# Extract OpenSSL if needed
if [ ! -d "$OPENSSL_SRC_DIR" ]; then
    echo "Extracting OpenSSL..."
    tar -xzf "$OPENSSL_ARCHIVE" -C "$BUILD_DIR"
fi

# Build for each ABI
for ABI in "${ABIS[@]}"; do
    echo "Building OpenSSL for $ABI..."
    
    # Set up toolchain paths
    TOOLCHAIN="${NDK_DIR}/toolchains/llvm/prebuilt/linux-x86_64"
    INSTALL_DIR="${BUILD_DIR}/openssl/${ABI}"
    mkdir -p "$INSTALL_DIR"
    
    # Configure compiler based on ABI
    case "$ABI" in
        "armeabi-v7a")
            OPENSSL_TARGET="android-arm"
            CC="${TOOLCHAIN}/bin/armv7a-linux-androideabi${API_LEVEL}-clang"
            ;;
        "arm64-v8a")
            OPENSSL_TARGET="android-arm64"
            CC="${TOOLCHAIN}/bin/aarch64-linux-android${API_LEVEL}-clang"
            ;;
        "x86")
            OPENSSL_TARGET="android-x86"
            CC="${TOOLCHAIN}/bin/i686-linux-android${API_LEVEL}-clang"
            ;;
        "x86_64")
            OPENSSL_TARGET="android-x86_64"
            CC="${TOOLCHAIN}/bin/x86_64-linux-android${API_LEVEL}-clang"
            ;;
    esac
    
    # Configure and build OpenSSL
    cd "$OPENSSL_SRC_DIR"
    
    # Clean any previous build
    make clean || true
    
    # Configure
    export ANDROID_NDK_HOME="$NDK_DIR"
    export PATH="${TOOLCHAIN}/bin:$PATH"
    export CC="$CC"
    
    ./Configure "$OPENSSL_TARGET" -D__ANDROID_API__="$API_LEVEL" \
        --prefix="$INSTALL_DIR" \
        --openssldir="$INSTALL_DIR" \
        no-shared no-tests
    
    # Build and install
    make -j$(nproc)
    make install_sw
    
    # Copy libraries to jniLibs directory
    JNI_LIBS_DIR="$(pwd)/../app/src/main/jniLibs/${ABI}"
    mkdir -p "$JNI_LIBS_DIR"
    cp -f "${INSTALL_DIR}/lib/"*.a "$JNI_LIBS_DIR/"
    
    echo "OpenSSL for $ABI built successfully"
done

echo "All OpenSSL builds completed successfully!"
