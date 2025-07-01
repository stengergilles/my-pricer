
#pragma once

#include <future>
#include <functional>

template<typename R>
class Worker {
public:
    Worker() : m_running(false) {}

    template<typename F, typename... Args>
    void start(F&& f, Args&&... args) {
        if (m_running) {
            return; // Already running
        }
        m_running = true;
        auto task = std::bind(std::forward<F>(f), std::forward<Args>(args)...);
        m_future = std::async(std::launch::async, task);
    }

    bool is_running() {
        if (!m_running) {
            return false;
        }
        if (m_future.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            m_running = false;
        }
        return m_running;
    }

    R get() {
        return m_future.get();
    }

private:
    std::future<R> m_future;
    bool m_running;
};
