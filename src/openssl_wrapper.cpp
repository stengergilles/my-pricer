#include <jni.h>
#include <string>
#include <openssl/opensslv.h>
#include <openssl/crypto.h>

extern "C" {

// JNI function to get OpenSSL version
JNIEXPORT jstring JNICALL
Java_com_example_imguihelloworld_OpenSSLLoader_getOpenSSLVersion(JNIEnv *env, jclass clazz) {
    // Get OpenSSL version string
    const char* version = OpenSSL_version(OPENSSL_VERSION);
    return env->NewStringUTF(version);
}

} // extern "C"
