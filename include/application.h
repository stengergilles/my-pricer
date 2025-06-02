#pragma once

#include <string>

// Forward declarations
struct ImGuiContext;
class PlatformBase;

class Application {
public:
    Application(const std::string& appName = "ImGui Hello World");
    virtual ~Application();

    // Initialize ImGui (platform-independent)
    bool initImGui();
    
    // Main application loop
    void run();
    
    // Render a frame
    void renderFrame();

    // Getters
    const std::string& getAppName() const { return m_appName; }
    
    // Get platform instance - commented out to fix circular dependency
    // PlatformBase* getPlatform() { return dynamic_cast<PlatformBase*>(this); }
    
    // Singleton access
    static Application* getInstance() { return s_instance; }

protected:
    // Platform-specific implementations (to be overridden by platform classes)
    virtual bool platformInit() = 0;
    virtual void platformShutdown() = 0;
    virtual void platformNewFrame() = 0;
    virtual void platformRender() = 0;
    virtual bool platformHandleEvents() = 0;

private:
    // ImGui rendering code (platform-independent)
    void renderImGui();

    std::string m_appName;
    ImGuiContext* m_imguiContext;
    bool m_running;
    
    // Singleton instance
    static Application* s_instance;
};
