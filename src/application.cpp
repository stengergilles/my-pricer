#include "../include/application.h"
#include "imgui.h"
#include <iostream>

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
    // Set ImGui style
    ImGui::StyleColorsDark();
    ImGui::GetStyle().ScaleAllSizes(2.0f); // Scale up UI for better touch interaction
    
    // Create a window with a title bar
    ImGui::SetNextWindowPos(ImVec2(0, 0));
    ImGui::SetNextWindowSize(ImGui::GetIO().DisplaySize);
    ImGui::Begin("My Android App", nullptr, 
        ImGuiWindowFlags_NoResize | 
        ImGuiWindowFlags_NoMove | 
        ImGuiWindowFlags_NoCollapse);
    
    // Add a label (text)
    ImGui::Text("Hello from ImGui on Android!");
    
    // Add some colored text
    ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "This is a yellow text.");
    
    // Add some spacing
    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();
    
    // Add a button
    static int clickCount = 0;
    if (ImGui::Button("Click Me!", ImVec2(200, 60))) {
        clickCount++;
    }
    
    // Display the click count
    ImGui::SameLine();
    ImGui::Text("Button clicked %d times", clickCount);
    
    // Add a slider
    static float value = 0.5f;
    ImGui::SliderFloat("Slider", &value, 0.0f, 1.0f);
    
    // End the window
    ImGui::End();
}
