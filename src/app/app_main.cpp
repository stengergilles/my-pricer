
#include "application.h"
#include "imgui.h"
#include "app/coingecko_fetcher.hpp"
#include "app/polygon_fetcher.hpp"
#include "app/base_fetcher.hpp"
#include "worker.hpp"
#include <memory>
#include <vector>

// --- Application State ---
static std::vector<std::unique_ptr<Fetcher>> fetchers;
static int selected_fetcher_index = 0;
static char api_key_buffer[256] = "YOUR_API_KEY"; 
static char identifier_buffer[256] = "btcusd";
static const char* periods[] = { "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max" };
static int selected_period_index = 0;
static const char* intervals[] = { "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo" };
static int selected_interval_index = 8;
static DataFrame fetched_data;
static std::string error_message;
static bool data_fetched = false;
static Worker<DataFrame> fetch_worker;

// --- Helper Functions ---
void initialize_fetchers() {
    fetchers.clear();
    fetchers.push_back(std::make_unique<CoinGeckoFetcher>());
    fetchers.push_back(std::make_unique<PolygonFetcher>(api_key_buffer));
}

DataFrame fetch_data_task(Fetcher* fetcher, std::string identifier, std::string period, std::string interval) {
    return fetcher->fetch_data(identifier, period, interval);
}

// --- ImGui Rendering ---
void Application::renderImGui() {
    // Initialize fetchers on first frame
    if (fetchers.empty()) {
        initialize_fetchers();
    }

    ImGui::Begin("My Pricer");

    // --- Fetcher Selection ---
    if (ImGui::BeginCombo("Fetcher", fetchers[selected_fetcher_index]->get_service_name().c_str())) {
        for (int i = 0; i < fetchers.size(); ++i) {
            const bool is_selected = (selected_fetcher_index == i);
            if (ImGui::Selectable(fetchers[i]->get_service_name().c_str(), is_selected)) {
                selected_fetcher_index = i;
            }
            if (is_selected) {
                ImGui::SetItemDefaultFocus();
            }
        }
        ImGui::EndCombo();
    }

    // --- API Key Input (for Polygon) ---
    if (fetchers[selected_fetcher_index]->get_service_name() == "Polygon.io") {
        if (ImGui::InputText("API Key", api_key_buffer, IM_ARRAYSIZE(api_key_buffer))) {
            // Re-initialize fetchers if API key changes
            initialize_fetchers();
        }
    }

    // --- Data Fetching Controls ---
    ImGui::InputText("Identifier", identifier_buffer, IM_ARRAYSIZE(identifier_buffer));
    ImGui::Combo("Period", &selected_period_index, periods, IM_ARRAYSIZE(periods));
    ImGui::Combo("Interval", &selected_interval_index, intervals, IM_ARRAYSIZE(intervals));

    if (ImGui::Button("Fetch Data")) {
        if (!fetch_worker.is_running()) {
            fetch_worker.start(fetch_data_task, 
                               fetchers[selected_fetcher_index].get(), 
                               identifier_buffer, 
                               periods[selected_period_index], 
                               intervals[selected_interval_index]);
        }
    }

    // --- Worker Status ---
    if (fetch_worker.is_running()) {
        ImGui::Text("Work in progress...");
    } else {
        if (data_fetched) {
            // a fetch has been completed
            try {
                fetched_data = fetch_worker.get();
                error_message.clear();
            } catch (const std::exception& e) {
                error_message = e.what();
                data_fetched = false;
            }
        }
    }

    // --- Display Error Message ---
    if (!error_message.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "Error: %s", error_message.c_str());
    }

    // --- Display Fetched Data ---
    if (data_fetched) {
        ImGui::Separator();
        ImGui::Text("Fetched Data (%s)", fetchers[selected_fetcher_index]->get_service_name().c_str());

        if (ImGui::BeginTable("Data", 6)) {
            ImGui::TableSetupColumn("Timestamp");
            ImGui::TableSetupColumn("Open");
            ImGui::TableSetupColumn("High");
            ImGui::TableSetupColumn("Low");
            ImGui::TableSetupColumn("Close");
            ImGui::TableSetupColumn("Volume");
            ImGui::TableHeadersRow();

            for (size_t i = 0; i < fetched_data.size(); ++i) {
                ImGui::TableNextRow();
                ImGui::TableSetColumnIndex(0);
                ImGui::Text("%s", fetched_data.datetime_index[i].c_str());
                ImGui::TableSetColumnIndex(1);
                ImGui::Text("%.2f", fetched_data.open[i]);
                ImGui::TableSetColumnIndex(2);
                ImGui::Text("%.2f", fetched_data.high[i]);
                ImGui::TableSetColumnIndex(3);
                ImGui::Text("%.2f", fetched_data.low[i]);
                ImGui::TableSetColumnIndex(4);
                ImGui::Text("%.2f", fetched_data.close[i]);
                ImGui::TableSetColumnIndex(5);
                ImGui::Text("%.0f", fetched_data.volume[i]);
            }
            ImGui::EndTable();
        }
    }

    ImGui::End();
}
