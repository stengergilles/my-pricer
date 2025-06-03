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
    
    // Use ImGuiInputTextFlags_CallbackAlways to ensure we get callbacks
    if (ImGui::InputText("##input", inputBuffer, IM_ARRAYSIZE(inputBuffer), 
                         ImGuiInputTextFlags_EnterReturnsTrue)) {
        // This code runs when Enter is pressed
        // You can handle the input submission here
    }
    
    // Note: Keyboard handling is now managed in platform_android.cpp
    // ImGui's WantTextInput flag is used naturally without manual setting
    
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
