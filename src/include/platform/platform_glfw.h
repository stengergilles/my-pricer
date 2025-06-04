#pragma once

#include "platform_base.h"

// Forward declarations
struct GLFWwindow;

// GLFW implementation (works on Windows, Linux, macOS)
class PlatformGLFW : public PlatformBase {
public:
    PlatformGLFW(int width = 1280, int height = 720, const std::string& appName = "ImGui Hello World");
    virtual ~PlatformGLFW();

protected:
    // Platform-specific implementations
    virtual bool platformInit() override;
    virtual void platformShutdown() override;
    virtual void platformNewFrame() override;
    virtual void platformRender() override;
    virtual bool platformHandleEvents() override;

private:
    GLFWwindow* m_window;
    int m_width;
    int m_height;
};
