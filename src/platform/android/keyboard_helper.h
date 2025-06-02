#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Function to show the keyboard from native code
void showKeyboard();

// Safer version that returns success/failure
bool showKeyboardSafely();

#ifdef __cplusplus
}
#endif
