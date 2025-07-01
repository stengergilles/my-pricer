#include "polygon_fetcher.hpp"
#include <stdexcept>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <algorithm>
#include <thread>
#include <random>
#include <iostream>
#include <cmath>

// Include nlohmann/json and PlatformHttpClient implementation headers
#include <nlohmann/json.hpp>

// Helper function for random number generation
static double random_uniform() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<> dist(0.0, 1.0);
    return dist(gen);
}

PolygonFetcher::PolygonFetcher(const std::string& api_key)
    : api_key_(api_key)
{
    if (api_key_.empty()) {
        throw std::invalid_argument("Polygon.io API key not found in application settings.");
    }
}

DataFrame PolygonFetcher::fetch_data(const std::string& identifier,
                                     const std::string& period,
                                     const std::string& interval)
{
    // Resolve period to date range and interval mapping
    auto [from_date, to_date] = resolve_dates(period);
    auto [multiplier, timespan] = map_interval(interval);

    // Convert ticker to uppercase
    std::string ticker = identifier;
    std::transform(ticker.begin(), ticker.end(), ticker.begin(), ::toupper);

    std::string url = "https://api.polygon.io/v2/aggs/ticker/" + ticker +
                      "/range/" + std::to_string(multiplier) + "/" + timespan + "/" +
                      from_date + "/" + to_date;

    std::map<std::string, std::string> params{
        {"apiKey", api_key_},
        {"adjusted", "true"},
        {"sort", "asc"},
        {"limit", "50000"}
    };

    PlatformHttpClient client;
    HttpResponse resp;

    constexpr int MAX_RETRIES = 5;
    constexpr int INITIAL_BACKOFF_SECONDS = 1;
    constexpr int BACKOFF_FACTOR = 2;
    int retries = 0;

    while (retries < MAX_RETRIES) {
        resp = client.get(url, params, {});

        if (resp.status_code == 429) {
            if (retries < MAX_RETRIES - 1) {
                double backoff = INITIAL_BACKOFF_SECONDS * std::pow(BACKOFF_FACTOR, retries) + random_uniform();
                std::cerr << "WARN [" << get_service_name() << "]: Request for "
                          << ticker << " failed with " << resp.status_code
                          << ". Retrying in " << backoff << "s..." << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(backoff * 1000)));
                retries++;
            } else {
                throw std::runtime_error("Max retries reached for " + ticker + " due to 429 errors.");
            }
        } else if (resp.status_code != 200) {
            throw std::runtime_error("Polygon.io HTTP error: " + std::to_string(resp.status_code));
        } else {
            // Success
            break;
        }
    }

    nlohmann::json data = nlohmann::json::parse(resp.text);

    if (data.contains("status") && data["status"] == "ERROR") {
        throw std::runtime_error("Polygon.io API error: " + data.value("message", "Unknown error"));
    }

    DataFrame df;
    if (data.contains("results") && data["results"].is_array()) {
        for (const auto& row : data["results"]) {
            df.open.push_back(row.value("o", 0.0));
            df.high.push_back(row.value("h", 0.0));
            df.low.push_back(row.value("l", 0.0));
            df.close.push_back(row.value("c", 0.0));
            df.volume.push_back(row.value("v", 0.0));
            // Convert ms timestamp to ISO 8601 string
            auto ms = row.value("t", 0LL);
            std::time_t sec = ms / 1000;
            std::tm tm = *std::gmtime(&sec);
            char buf[32];
            std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tm);
            df.datetime_index.push_back(std::string(buf));
        }
    }
    return df;
}

std::string PolygonFetcher::get_service_name() const {
    return "Polygon.io";
}

std::pair<std::string, std::string> PolygonFetcher::resolve_dates(const std::string& period) {
    using namespace std::chrono;

    // Get today as UTC tm struct
    auto now = system_clock::now();
    std::time_t now_tt = system_clock::to_time_t(now);
    std::tm tm_today = *std::gmtime(&now_tt);
    std::tm tm_from = tm_today;

    if (period == "1d") {
        tm_from.tm_mday -= 1;
    } else if (period == "5d") {
        tm_from.tm_mday -= 5;
    } else if (period == "1w") {
        tm_from.tm_mday -= 7;
    } else if (period == "1mo") {
        tm_from.tm_mon -= 1;
    } else if (period == "3mo") {
        tm_from.tm_mon -= 3;
    } else if (period == "6mo") {
        tm_from.tm_mon -= 6;
    } else if (period == "1y") {
        tm_from.tm_year -= 1;
    } else if (period == "2y") {
        tm_from.tm_year -= 2;
    } else if (period == "5y") {
        tm_from.tm_year -= 5;
    } else if (period == "max") {
        return {"2000-01-01", strftime_date(tm_today)};
    } else {
        throw std::invalid_argument("Unsupported period: " + period);
    }
    // Normalize to handle month/year underflow/overflow
    std::mktime(&tm_from);
    return {strftime_date(tm_from), strftime_date(tm_today)};
}

std::pair<int, std::string> PolygonFetcher::map_interval(const std::string& interval) {
    static const std::map<std::string, std::pair<int, std::string>> interval_map = {
        {"1m", {1, "minute"}}, {"5m", {5, "minute"}}, {"15m", {15, "minute"}}, {"30m", {30, "minute"}},
        {"1h", {1, "hour"}}, {"2h", {2, "hour"}},
        {"1d", {1, "day"}}, {"1w", {7, "day"}}
    };
    auto it = interval_map.find(interval);
    if (it == interval_map.end()) throw std::invalid_argument("Unsupported interval: " + interval);
    return it->second;
}

std::string PolygonFetcher::strftime_date(const std::tm& tm) {
    char buf[16];
    std::strftime(buf, sizeof(buf), "%Y-%m-%d", &tm);
    return std::string(buf);
}
