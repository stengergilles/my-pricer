#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Function to show the keyboard
void showKeyboard();

// Function to hide the keyboard
void hideKeyboard();

// Safe implementation that checks for null pointers
bool showKeyboardSafely();

// Safe implementation that checks for null pointers
bool hideKeyboardSafely();

#ifdef __cplusplus
}
#endif
