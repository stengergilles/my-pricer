#include "../include/application.h"
#include "imgui.h"
#include <iostream>

#ifdef __ANDROID__
#include "platform/android/keyboard_helper.h"
#endif
#include "python_bridge.h"

// Initialize static instance
Application* Application::s_instance = nullptr;

Application::Application(const std::string& appName)
    : m_appName(appName)
    , m_imguiContext(nullptr)
    , m_running(false)
    , m_tickerMonitorId(-1)
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
    
    // Stop any active ticker monitor
    stopTickerMonitor();
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
        std::cerr << "Failed to initialize platform" << std::endl;
        return;
    }
    
    m_running = true;
    
    // Main loop
    while (m_running) {
        // Handle events (returns false if application should exit)
        if (!platformHandleEvents()) {
            m_running = false;
            break;
        }
        
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
    
    // Render application frame
    renderImGui();
    
    // Render and present
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
    
    // Add ticker monitor controls
    ImGui::Separator();
    ImGui::Text("Stock Monitoring");
    
    static char tickerBuffer[32] = "AAPL";
    ImGui::InputText("Ticker", tickerBuffer, IM_ARRAYSIZE(tickerBuffer));
    
    static float entryPrice = 100.0f;
    ImGui::InputFloat("Entry Price", &entryPrice, 1.0f, 10.0f, "%.2f");
    
    if (ImGui::Button("Start Monitoring")) {
        startTickerMonitor(tickerBuffer, entryPrice);
    }
    
    ImGui::SameLine();
    
    if (ImGui::Button("Stop Monitoring")) {
        stopTickerMonitor();
    }
    
    // Display messages from ticker monitor
    ImGui::Separator();
    ImGui::Text("Monitor Messages:");
    ImGui::BeginChild("Messages", ImVec2(0, 200), true);
    
    const char* message = getNextTickerMessage();
    if (message && message[0] != '\0') {
        ImGui::TextWrapped("%s", message);
    }
    
    ImGui::EndChild();
    
    ImGui::End();
}

// Python integration methods
void Application::startTickerMonitor(const char* ticker, float entryPrice)
{
#if defined(__ANDROID__) && defined(WITH_PYTHON)
    if (m_tickerMonitorId >= 0) {
        stopTickerMonitor();
    }
    
    m_tickerMonitorId = pythonBridgeCreateTickerMonitor(ticker, entryPrice, "intraday", 1.0f, 0.05f);
    std::cout << "Started ticker monitor with ID: " << m_tickerMonitorId << std::endl;
#else
    std::cout << "Ticker monitoring is only supported on Android with Python enabled" << std::endl;
#endif
}

void Application::stopTickerMonitor()
{
#if defined(__ANDROID__) && defined(WITH_PYTHON)
    if (m_tickerMonitorId >= 0) {
        pythonBridgeStopTickerMonitor(m_tickerMonitorId);
        m_tickerMonitorId = -1;
        std::cout << "Stopped ticker monitor" << std::endl;
    }
#endif
}

const char* Application::getNextTickerMessage()
{
#if defined(__ANDROID__) && defined(WITH_PYTHON)
    return pythonBridgeGetNextMessage();
#else
    static const char* msg = "Python support not enabled";
    return msg;
#endif
}
