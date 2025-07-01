#include "app/coingecko_fetcher.hpp"
#include "platform_http_client.hpp"      // The platform-abstracted HTTP client
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <limits>

CoinGeckoFetcher::CoinGeckoFetcher(const std::string& api_key)
    : api_key_(api_key)
{}

std::string CoinGeckoFetcher::fetch_raw_response(
    const std::string& identifier,
    const std::string& period,
    const std::string& interval)
{
    static const std::unordered_map<std::string, std::string> period_map_cg = {
        {"1d", "1"}, {"5d", "7"}, {"1w", "7"}, {"1mo", "30"}, {"3mo", "90"},
        {"6mo", "180"}, {"1y", "365"}, {"2y", "max"}, {"5y", "max"}, {"max", "max"}
    };
    std::string period_lc = to_lower(period);
    if (period_map_cg.find(period_lc) == period_map_cg.end())
        throw std::invalid_argument("Unsupported period for CoinGecko: " + period);

    std::string cg_days = period_map_cg.at(period_lc);
    const std::string coin_id = to_lower(identifier);
    const std::string vs_currency = "usd";
    std::string api_url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart";

    // Build query parameters
    std::map<std::string, std::string> params = {
        {"vs_currency", vs_currency},
        {"days", cg_days}
    };
    if (cg_days == "max" || (is_number(cg_days) && std::stoi(cg_days) > 90)) {
        params["interval"] = "daily";
    }

    // Set up headers
    std::map<std::string, std::string> headers;
    if (!api_key_.empty())
        headers["X-CG-DEMO-API-KEY"] = api_key_;

    // Retry logic
    constexpr int MAX_RETRIES = 5;
    constexpr int INITIAL_BACKOFF_SECONDS = 1;
    constexpr int BACKOFF_FACTOR = 2;
    int retries = 0;
    std::string last_error;

    PlatformHttpClient http_client;

    while (retries < MAX_RETRIES) {
        try {
            auto response = http_client.get(api_url, params, headers);
            if (response.status_code >= 400) {
                if (response.status_code == 429) {
                    if (retries < MAX_RETRIES - 1) {
                        double backoff = INITIAL_BACKOFF_SECONDS * std::pow(BACKOFF_FACTOR, retries) + random_uniform();
                        std::cerr << "WARN [" << get_service_name() << "]: Request for "
                                  << coin_id << " failed with " << response.status_code
                                  << ". Retrying in " << backoff << "s..." << std::endl;
                        std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(backoff * 1000)));
                    } else {
                        throw std::runtime_error("Max retries reached for " + coin_id + " due to 429 errors.");
                    }
                } else {
                    throw std::runtime_error("HTTP error " + std::to_string(response.status_code) + " for " + coin_id);
                }
            }
            if (response.text.empty()) {
                throw std::runtime_error("Empty response body from CoinGecko API.");
            }
            return response.text;
        } catch (const std::exception& e) {
            last_error = e.what();
            if (++retries >= MAX_RETRIES)
                throw std::runtime_error("Failed to fetch data: " + last_error);
        }
    }
    throw std::runtime_error("Failed to fetch data: " + last_error); // Should not reach here
}

DataFrame CoinGeckoFetcher::fetch_data(const std::string& identifier,
                                       const std::string& period,
                                       const std::string& interval)
{
    // Step 1: Fetch raw JSON string from CoinGecko
    std::string raw_json = fetch_raw_response(identifier, period, interval);

    // Step 2: Parse JSON
    nlohmann::json data;
    try {
        data = nlohmann::json::parse(raw_json);
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse JSON from CoinGecko: " + std::string(e.what()));
    }

    // Step 3: Process as before
    if (!data.contains("prices") || !data.contains("total_volumes"))
        throw std::runtime_error("CoinGecko API response is malformed or missing data.");

    auto& prices_data = data["prices"];
    auto& volumes_data = data["total_volumes"];

    if (prices_data.empty())
        return DataFrame{};

    DataFrame df;
    for (const auto& entry : prices_data) {
        df.datetime_index.push_back(timestamp_to_iso8601(entry[0].get<int64_t>()));
        df.close.push_back(entry[1].get<double>());
    }
    if (!volumes_data.empty()) {
        for (size_t i = 0; i < volumes_data.size(); ++i) {
            df.volume.push_back(volumes_data[i][1].get<double>());
        }
    } else {
        df.volume.resize(df.close.size(), std::numeric_limits<double>::quiet_NaN());
    }
    // Open/High/Low not provided by API; set to Close
    df.open = df.close;
    df.high = df.close;
    df.low = df.close;

    return df;
}

std::string CoinGeckoFetcher::get_service_name() const {
    return "CoinGecko";
}

std::string CoinGeckoFetcher::to_lower(const std::string& s) {
    std::string out = s;
    std::transform(out.begin(), out.end(), out.begin(), ::tolower);
    return out;
}

bool CoinGeckoFetcher::is_number(const std::string& s) {
    return !s.empty() && std::all_of(s.begin(), s.end(), ::isdigit);
}

double CoinGeckoFetcher::random_uniform() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<> dist(0.0, 1.0);
    return dist(gen);
}

std::string CoinGeckoFetcher::timestamp_to_iso8601(int64_t ms_since_epoch) {
    std::time_t t = ms_since_epoch / 1000;
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", std::gmtime(&t));
    return std::string(buf);
}
