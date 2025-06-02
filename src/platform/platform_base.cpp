#include "../../include/platform/platform_base.h"

PlatformBase::PlatformBase(const std::string& appName)
    : Application(appName)
{
}

PlatformBase::~PlatformBase()
{
    // Base platform cleanup
}
