#pragma once

#include <string>

// C++ interface for Python bridge
namespace PythonBridge {

// Initialize the Python bridge
bool initialize();

// Clean up resources
void cleanup();

// Create a new TickerMonitor
int createTickerMonitor(const std::string& ticker, float entryPrice, 
                        const std::string& scope, float leverage, float stopLoss);

// Stop a TickerMonitor
bool stopTickerMonitor(int monitorId);

// Get the next message (non-blocking)
std::string getNextMessage();

// Wait for a message with timeout
std::string waitForMessage(int timeoutMs);

} // namespace PythonBridge
