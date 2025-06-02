#pragma once

#include "platform_base.h"
#include <string>

class PlatformAndroid : public PlatformBase {
public:
    PlatformAndroid(const std::string& title);
    virtual ~PlatformAndroid();
    
    virtual bool platformInit() override;
    virtual void platformNewFrame() override;
    virtual void platformRender() override;
    virtual bool platformHandleEvents() override;
    virtual void platformShutdown() override;  // Implement the pure virtual method
    
    // Add a public setter method for m_androidApp
    void setAndroidApp(void* app);

protected:
    // Changed from private to protected to allow access in derived classes
    void* m_androidApp;  // android_app* in actual implementation
};
