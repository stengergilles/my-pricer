#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Initialize the Python bridge
bool pythonBridgeInitialize();

// Create a new TickerMonitor
int pythonBridgeCreateTickerMonitor(const char* ticker, float entryPrice, 
                                   const char* scope, float leverage, float stopLoss);

// Stop a TickerMonitor
bool pythonBridgeStopTickerMonitor(int monitorId);

// Get the next message (non-blocking)
const char* pythonBridgeGetNextMessage();

// Wait for a message with timeout
const char* pythonBridgeWaitForMessage(int timeoutMs);

// Clean up resources
void pythonBridgeCleanup();

#ifdef __cplusplus
}
#endif
