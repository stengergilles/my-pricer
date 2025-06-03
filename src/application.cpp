#include "../include/application.h"
#include "imgui.h"
#include <iostream>

#ifdef __ANDROID__
#include "platform/android/keyboard_helper.h"
#endif

// Initialize static instance
Application* Application::s_instance = nullptr;

Application::Application(const std::string& appName)
    : m_appName(appName)
    , m_imguiContext(nullptr)
    , m_running(false)
{
    // Set singleton instance
    s_instance = this;
}

Application::~Application()
{
    // ImGui cleanup is handled in platformShutdown()
    if (s_instance == this) {
        s_instance = nullptr;
    }
}

bool Application::initImGui()
{
    // Create ImGui context
    m_imguiContext = ImGui::CreateContext();
    if (!m_imguiContext) {
        std::cerr << "Failed to create ImGui context" << std::endl;
        return false;
    }

    // Setup ImGui style
    ImGui::StyleColorsDark();
    
    return true;
}

void Application::run()
{
    // For Android, we don't run the main loop here
    // The main loop is handled in android_main.cpp
    #ifndef __ANDROID__
    // Initialize platform-specific components
    if (!platformInit()) {
        std::cerr << "Platform initialization failed" << std::endl;
        return;
    }

    // Initialize ImGui
    if (!initImGui()) {
        std::cerr << "ImGui initialization failed" << std::endl;
        platformShutdown();
        return;
    }

    // Main loop
    m_running = true;
    while (m_running) {
        // Handle platform events (may set m_running to false)
        m_running = platformHandleEvents();
        
        // Render a frame
        renderFrame();
    }

    // Cleanup
    platformShutdown();
    #endif
}

void Application::renderFrame()
{
    // Start a new frame
    platformNewFrame();
    ImGui::NewFrame();
    
    // Render application frame
    renderImGui();
    
    // Render and present
    ImGui::Render();
    platformRender();
}

void Application::renderImGui()
{
    // Create a simple window
    ImGui::Begin("Hello, ImGui!");
    
    ImGui::Text("Welcome to Dear ImGui!");
    ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "This is a cross-platform application.");
    
    // Add an input text field
    static char inputBuffer[256] = "";
    ImGui::Text("Enter some text (tap to show keyboard):");
    
    // Force ImGui to want text input for this frame
    ImGui::GetIO().WantTextInput = true;
    
    // Store the current active state before the InputText widget
    bool wasActive = ImGui::IsItemActive();
    
    // Use ImGuiInputTextFlags_CallbackAlways to ensure we get callbacks
    if (ImGui::InputText("##input", inputBuffer, IM_ARRAYSIZE(inputBuffer), 
                         ImGuiInputTextFlags_EnterReturnsTrue)) {
        // This code runs when Enter is pressed
        // You can handle the input submission here
    }
    
    // Let ImGui handle WantTextInput naturally
    #ifdef __ANDROID__
    static bool keyboardVisible = false;
    bool wantsTextInput = ImGui::GetIO().WantTextInput;
    
    if (wantsTextInput) {
        // ImGui wants text input - show keyboard
        if (!keyboardVisible) {
            // Show keyboard when ImGui wants text input
            extern void showKeyboard(); // Forward declaration
            showKeyboard();
            keyboardVisible = true;
            
            // Log that we're trying to show the keyboard
            ImGui::LogText("Showing keyboard - ImGui wants text input");
        }
    } else if (!wantsTextInput && keyboardVisible) {
        // ImGui no longer wants text input - hide keyboard
        extern void hideKeyboard(); // Forward declaration
        hideKeyboard();
        keyboardVisible = false;
        
        // Log that we're hiding the keyboard
        ImGui::LogText("Hiding keyboard - ImGui no longer wants text input");
    }
    #endif
    
    ImGui::SameLine();
    if (ImGui::Button("Clear")) {
        inputBuffer[0] = '\0'; // Clear the input buffer
    }
    
    // Display the entered text
    ImGui::Text("You entered: %s", inputBuffer);
    
    static int clickCount = 0;
    if (ImGui::Button("Click me!")) {
        clickCount++;
    }
    
    ImGui::Text("Button clicked %d times", clickCount);
    
    ImGui::End();
}
