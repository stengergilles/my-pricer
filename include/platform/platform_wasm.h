#pragma once

#include "platform_base.h"

// WebAssembly implementation
class PlatformWasm : public PlatformBase {
public:
    PlatformWasm(int width = 1280, int height = 720, const std::string& appName = "ImGui Hello World");
    virtual ~PlatformWasm();

protected:
    // Platform-specific implementations
    virtual bool platformInit() override;
    virtual void platformShutdown() override;
    virtual void platformNewFrame() override;
    virtual void platformRender() override;
    virtual bool platformHandleEvents() override;

private:
    int m_width;
    int m_height;
};
