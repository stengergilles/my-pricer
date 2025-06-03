#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Function to show the keyboard from native code
void showKeyboard();

// Function to hide the keyboard from native code
void hideKeyboard();

// Safer version that returns success/failure
bool showKeyboardSafely();

// Safer version that returns success/failure
bool hideKeyboardSafely();

#ifdef __cplusplus
}
#endif
