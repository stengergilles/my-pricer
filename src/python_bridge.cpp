#include "python_bridge.h"
#include <string>

// Stub implementation since we've removed Chaquopy
namespace PythonBridge {

bool initialize() {
    return false;
}

void cleanup() {
    // Nothing to do
}

int createTickerMonitor(const std::string& ticker, float entryPrice, 
                        const std::string& scope, float leverage, float stopLoss) {
    return -1;
}

bool stopTickerMonitor(int monitorId) {
    return false;
}

std::string getNextMessage() {
    return "Python support is disabled";
}

std::string waitForMessage(int timeoutMs) {
    return "Python support is disabled";
}

} // namespace PythonBridge
