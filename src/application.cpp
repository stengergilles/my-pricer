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
        
        // Start a new frame
        platformNewFrame();
        ImGui::NewFrame();
        
        // Render application frame
        renderFrame();
        
        // Render and present
        ImGui::Render();
        platformRender();
    }

    // Cleanup
    platformShutdown();
}

void Application::renderFrame()
{
    // Render ImGui components
    renderImGui();
}

void Application::renderImGui()
{
    // Create a simple window
    ImGui::Begin("Hello, ImGui!");
    
    ImGui::Text("Welcome to Dear ImGui!");
    ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "This is a cross-platform application.");
    
    if (ImGui::Button("Click me!")) {
        // Button action
    }
    
    ImGui::End();
}
