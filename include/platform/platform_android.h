#pragma once

#include "platform/platform.h"
#include <string>

class PlatformAndroid : public Platform {
public:
    PlatformAndroid(const std::string& title);
    virtual ~PlatformAndroid();
    
    virtual bool platformInit() override;
    virtual void platformNewFrame() override;
    virtual void platformRender() override;
    virtual bool platformHandleEvents() override;
    
    // Add a public setter method for m_androidApp
    void setAndroidApp(void* app);

protected:
    // Changed from private to protected to allow access in derived classes
    void* m_androidApp;  // android_app* in actual implementation
};
