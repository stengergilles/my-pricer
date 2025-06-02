#pragma once

#include "platform_base.h"

// Android implementation
class PlatformAndroid : public PlatformBase {
public:
    PlatformAndroid(const std::string& appName = "ImGui Hello World");
    virtual ~PlatformAndroid();

protected:
    // Platform-specific implementations
    virtual bool platformInit() override;
    virtual void platformShutdown() override;
    virtual void platformNewFrame() override;
    virtual void platformRender() override;
    virtual bool platformHandleEvents() override;

private:
    // Android-specific members
    void* m_androidApp;  // android_app* in actual implementation
};
