#include <Python.h>
#include <string>
#include <vector>
#include <iostream>
#include <mutex>
#include <thread>
#include <condition_variable>
#include <queue>
#include <memory>

// Python bridge class for integrating Python code with C++
class PythonBridge {
private:
    bool initialized = false;
    std::mutex mtx;
    std::condition_variable cv;
    std::queue<std::string> messageQueue;
    std::thread messageThread;
    bool running = false;
    PyObject* pTickerMonitorClass = nullptr;
    std::vector<PyObject*> activeMonitors;

    // Singleton instance
    static PythonBridge* instance;

    // Private constructor for singleton pattern
    PythonBridge() {}
    
    // Check if a Python module is available
    bool isPythonModuleAvailable(const char* moduleName) {
        PyObject* pName = PyUnicode_DecodeFSDefault(moduleName);
        PyObject* pModule = PyImport_Import(pName);
        Py_DECREF(pName);
        
        if (pModule == nullptr) {
            PyErr_Clear(); // Clear the error
            return false;
        }
        
        Py_DECREF(pModule);
        return true;
    }
    
    // Check if all required dependencies are available
    bool checkDependencies() {
        const char* requiredModules[] = {
            "pandas", "numpy", "requests", "multiprocessing"
        };
        
        bool allAvailable = true;
        std::string missingModules;
        
        for (const char* module : requiredModules) {
            if (!isPythonModuleAvailable(module)) {
                if (!missingModules.empty()) {
                    missingModules += ", ";
                }
                missingModules += module;
                allAvailable = false;
            }
        }
        
        if (!allAvailable) {
            std::cerr << "Missing required Python modules: " << missingModules << std::endl;
            std::cerr << "Please ensure these modules are included in the Chaquopy configuration." << std::endl;
        }
        
        return allAvailable;
    }

public:
    // Get singleton instance
    static PythonBridge* getInstance() {
        if (instance == nullptr) {
            instance = new PythonBridge();
        }
        return instance;
    }

    // Initialize Python interpreter and import required modules
    bool initialize() {
        std::lock_guard<std::mutex> lock(mtx);
        if (initialized) return true;

        // Initialize Python interpreter
        Py_Initialize();
        if (!Py_IsInitialized()) {
            std::cerr << "Failed to initialize Python interpreter" << std::endl;
            return false;
        }

        // Add current directory to Python path
        PyRun_SimpleString("import sys\n"
                          "import os\n"
                          "sys.path.append(os.getcwd())\n");
                          
        // Check if required dependencies are available
        if (!checkDependencies()) {
            std::cerr << "Missing required Python dependencies" << std::endl;
            return false;
        }

        // Import the TickerMonitor class
        PyObject* pName = PyUnicode_DecodeFSDefault("stock_monitoring_app.monitoring.ticker_monitor");
        PyObject* pModule = PyImport_Import(pName);
        Py_DECREF(pName);

        if (pModule == nullptr) {
            PyErr_Print();
            std::cerr << "Failed to import ticker_monitor module" << std::endl;
            return false;
        }

        // Get the TickerMonitor class
        pTickerMonitorClass = PyObject_GetAttrString(pModule, "TickerMonitor");
        Py_DECREF(pModule);

        if (pTickerMonitorClass == nullptr || !PyCallable_Check(pTickerMonitorClass)) {
            PyErr_Print();
            std::cerr << "Failed to get TickerMonitor class" << std::endl;
            return false;
        }

        // Start message processing thread
        running = true;
        messageThread = std::thread(&PythonBridge::processMessages, this);

        initialized = true;
        return true;
    }

    // Create a new TickerMonitor instance
    int createTickerMonitor(const std::string& ticker, float entryPrice, 
                           const std::string& scope = "intraday", 
                           float leverage = 1.0f, 
                           float stopLoss = 0.05f) {
        std::lock_guard<std::mutex> lock(mtx);
        if (!initialized) {
            std::cerr << "Python bridge not initialized" << std::endl;
            return -1;
        }

        // Create a custom queue for the monitor
        PyObject* pQueue = PyObject_CallObject(
            PyObject_GetAttrString(PyImport_ImportModule("queue"), "Queue"), 
            PyTuple_New(0)
        );

        // Create args tuple for the TickerMonitor constructor
        PyObject* pArgs = PyTuple_New(5);
        PyTuple_SetItem(pArgs, 0, PyUnicode_DecodeFSDefault(ticker.c_str()));
        PyTuple_SetItem(pArgs, 1, pQueue);
        PyTuple_SetItem(pArgs, 2, PyFloat_FromDouble(entryPrice));
        PyTuple_SetItem(pArgs, 3, PyUnicode_DecodeFSDefault(scope.c_str()));
        PyTuple_SetItem(pArgs, 4, PyFloat_FromDouble(leverage));

        // Create kwargs dict for optional parameters
        PyObject* pKwargs = PyDict_New();
        PyDict_SetItemString(pKwargs, "stop_loss", PyFloat_FromDouble(stopLoss));

        // Create the TickerMonitor instance
        PyObject* pMonitor = PyObject_Call(pTickerMonitorClass, pArgs, pKwargs);
        Py_DECREF(pArgs);
        Py_DECREF(pKwargs);

        if (pMonitor == nullptr) {
            PyErr_Print();
            std::cerr << "Failed to create TickerMonitor instance" << std::endl;
            return -1;
        }

        // Start the monitor in a separate thread
        PyObject* pThread = PyObject_CallMethod(
            PyImport_ImportModule("threading"), 
            "Thread", 
            "(O)", 
            PyObject_GetAttrString(pMonitor, "run")
        );

        if (pThread == nullptr) {
            PyErr_Print();
            std::cerr << "Failed to create thread for TickerMonitor" << std::endl;
            Py_DECREF(pMonitor);
            return -1;
        }

        PyObject_CallMethod(pThread, "start", "()");

        // Store the monitor and its queue
        int monitorId = activeMonitors.size();
        activeMonitors.push_back(pMonitor);

        // Start a thread to process messages from this monitor
        std::thread([this, pQueue, monitorId, ticker]() {
            while (running) {
                PyObject* pMethod = PyObject_GetAttrString(pQueue, "get");
                PyObject* pTimeout = PyFloat_FromDouble(0.5); // 0.5 second timeout
                PyObject* pArgs = PyTuple_Pack(1, pTimeout);
                PyObject* pResult = PyObject_CallObject(pMethod, pArgs);
                Py_DECREF(pMethod);
                Py_DECREF(pArgs);

                if (pResult != nullptr && pResult != Py_None) {
                    // Process the message
                    PyObject* pStr = PyObject_Str(pResult);
                    const char* message = PyUnicode_AsUTF8(pStr);
                    
                    // Add to message queue
                    {
                        std::lock_guard<std::mutex> lock(mtx);
                        messageQueue.push(std::string(message));
                    }
                    cv.notify_one();
                    
                    Py_DECREF(pStr);
                    Py_DECREF(pResult);
                } else {
                    PyErr_Clear(); // Clear any exception from queue.get timeout
                }

                // Check if monitor is still running
                PyObject* pRunning = PyObject_GetAttrString(activeMonitors[monitorId], "_running");
                bool isRunning = PyObject_IsTrue(pRunning);
                Py_DECREF(pRunning);

                if (!isRunning) {
                    std::cout << "Monitor for " << ticker << " has stopped" << std::endl;
                    break;
                }
            }
        }).detach();

        return monitorId;
    }

    // Stop a specific TickerMonitor
    bool stopTickerMonitor(int monitorId) {
        std::lock_guard<std::mutex> lock(mtx);
        if (!initialized || monitorId < 0 || monitorId >= activeMonitors.size()) {
            return false;
        }

        PyObject* pMonitor = activeMonitors[monitorId];
        PyObject_CallMethod(pMonitor, "stop", "()");
        return true;
    }

    // Get the next message from the queue (non-blocking)
    std::string getNextMessage() {
        std::lock_guard<std::mutex> lock(mtx);
        if (messageQueue.empty()) {
            return "";
        }
        
        std::string message = messageQueue.front();
        messageQueue.pop();
        return message;
    }

    // Wait for a message with timeout (in milliseconds)
    std::string waitForMessage(int timeoutMs) {
        std::unique_lock<std::mutex> lock(mtx);
        if (cv.wait_for(lock, std::chrono::milliseconds(timeoutMs), 
                        [this] { return !messageQueue.empty(); })) {
            std::string message = messageQueue.front();
            messageQueue.pop();
            return message;
        }
        return "";
    }

    // Process messages in a separate thread
    void processMessages() {
        while (running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            // This thread can be used for background processing if needed
        }
    }

    // Clean up resources
    void cleanup() {
        std::lock_guard<std::mutex> lock(mtx);
        if (!initialized) return;

        running = false;
        if (messageThread.joinable()) {
            messageThread.join();
        }

        // Stop all active monitors
        for (PyObject* pMonitor : activeMonitors) {
            PyObject_CallMethod(pMonitor, "stop", "()");
            Py_DECREF(pMonitor);
        }
        activeMonitors.clear();

        Py_XDECREF(pTickerMonitorClass);
        Py_Finalize();
        initialized = false;
    }

    // Destructor
    ~PythonBridge() {
        cleanup();
    }
};

// Initialize static instance
PythonBridge* PythonBridge::instance = nullptr;

// C-style interface for JNI
extern "C" {
    // Initialize the Python bridge
    bool pythonBridgeInitialize() {
        return PythonBridge::getInstance()->initialize();
    }

    // Create a new TickerMonitor
    int pythonBridgeCreateTickerMonitor(const char* ticker, float entryPrice, 
                                       const char* scope, float leverage, float stopLoss) {
        return PythonBridge::getInstance()->createTickerMonitor(
            std::string(ticker), entryPrice, std::string(scope), leverage, stopLoss);
    }

    // Stop a TickerMonitor
    bool pythonBridgeStopTickerMonitor(int monitorId) {
        return PythonBridge::getInstance()->stopTickerMonitor(monitorId);
    }

    // Get the next message (non-blocking)
    const char* pythonBridgeGetNextMessage() {
        static std::string message;
        message = PythonBridge::getInstance()->getNextMessage();
        return message.c_str();
    }

    // Wait for a message with timeout
    const char* pythonBridgeWaitForMessage(int timeoutMs) {
        static std::string message;
        message = PythonBridge::getInstance()->waitForMessage(timeoutMs);
        return message.c_str();
    }

    // Clean up resources
    void pythonBridgeCleanup() {
        PythonBridge::getInstance()->cleanup();
    }
}
