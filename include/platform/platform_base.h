#pragma once

#include "../application.h"

// Base class for platform-specific implementations
class PlatformBase : public Application {
public:
    PlatformBase(const std::string& appName = "ImGui Hello World");
    virtual ~PlatformBase();

protected:
    // Common platform functionality can be implemented here
};
