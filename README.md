# Stock Monitoring and Backtesting Application

This project provides a framework for fetching financial market data, applying technical indicators, defining trading strategies, backtesting these strategies against historical data, and monitoring assets in real-time.

## ImGui Hello World Application

The repository also includes a cross-platform Dear ImGui hello world application that demonstrates how to create a simple GUI application that can be built for multiple platforms including Android, Linux, Windows, macOS, and WebAssembly.

## Features

*   **Data Fetching:**
    *   Supports fetching stock data from [Polygon.io](https://polygon.io/).
    *   Supports fetching cryptocurrency data from [CoinGecko](https://www.coingecko.com/en/api).
*   **Technical Indicators:**
    *   Average True Range (ATR)
    *   Bollinger Bands
    *   Breakout Detection
    *   Moving Averages (SMA, EMA)
    *   Moving Average Convergence Divergence (MACD)
    *   Relative Strength Index (RSI)
    *   Volume Spike Detection
*   **Strategy Framework:**
    *   A `BaseStrategy` class that allows combining multiple indicators to generate trading signals (BUY, SELL, HOLD).
*   **Backtesting Engine:**
    *   Performs backtests using historical data and a defined strategy.
    *   Includes placeholder logic for indicator parameter optimization.
    *   Evaluates strategy performance with various metrics (e.g., P&L, win rate, max drawdown).
    *   Saves backtest results (data with signals) and performance metrics to CSV and JSON files respectively in the `backtest_outputs` directory.
*   **Real-time Monitoring:**
    *   `TickerMonitor` class for continuous monitoring of individual assets.
    *   `ProcessManager` for managing multiple monitoring processes simultaneously.
    *   Support for real-time trading signals and notifications.
    *   Configurable monitoring intervals and scopes (intraday, short-term, long-term).
    *   Automated position tracking and risk management with stop-loss functionality.

## Project Structure

A brief overview of the main directories:
```
my-pricer/
├── stock_monitoring_app/       # Core application logic
│   ├── backtest/               # Backtesting engine
│   ├── fetchers/               # Data fetching modules (Polygon, CoinGecko)
│   ├── indicators/             # Technical indicator implementations
│   ├── monitoring/             # Real-time monitoring components
│   │   └── ticker_monitor.py   # TickerMonitor implementation for real-time asset tracking
│   ├── strategies/             # Trading strategy logic
│   ├── utils/                  # Utility functions and classes
│   │   ├── process_manager.py  # Multi-process management for multiple monitors
│   │   └── notification.py     # Notification system for alerts
│   ├── cli/                    # Command-line interface components
│   ├── config.py               # Application configuration (API keys, etc.)
│   └── __init__.py
├── examples/                   # Example scripts demonstrating usage
│   ├── run_fetcher_example.py
│   ├── run_indicators_example.py
│   ├── run_strategy_example.py
│   ├── run_backtest_example.py
│   ├── run_ticker_monitor_example.py
│   ├── run_process_manager_example.py
│   └── __init__.py
├── tests/                      # Automated tests
│   ├── indicators/             # Tests for technical indicators
│   ├── fetchers/               # Tests for data fetchers
│   ├── monitoring/             # Tests for monitoring components
│   ├── strategies/             # Tests for trading strategies
│   ├── backtest/               # Tests for backtesting engine
│   ├── utils/                  # Tests for utility functions
│   ├── cli/                    # Tests for CLI components
│   ├── integrations/           # Integration tests
│   ├── test_utils.py           # General utility tests
│   └── conftest.py             # Pytest fixtures and hooks
├── backtest_outputs/           # (Generated) Directory for storing backtest results
├── LICENSE                     # Project license
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python package dependencies
└── README.md                   # This file
```

## Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd my-pricer
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment. This project has dependencies such as `pandas`, `pandas-ta`, `requests`, `numpy`, and others for multiprocessing and data handling:

    ```bash
    pip install -r requirements.txt
    ```
    The [requirements.txt](requirements.txt) file lists the necessary Python packages.

3.  **Environment Variables:**
    The application requires API keys for data fetchers. These are loaded from environment variables via `config.py`. You need to set:
    *   `POLYGON_API_KEY`: Your API key for Polygon.io.
    *   `COINGECKO_API_KEY`: Your API key for CoinGecko (optional, for higher rate limits or Pro features).

    Refer to `stock_monitoring_app/config.py` for how these are managed.

## Usage

### Backtesting

To run a backtest on historical data:

```python
from stock_monitoring_app.backtest.backtest import BackTest

# Example for a stock
stock_backtest = BackTest(ticker="AAPL", period="1y", interval="1d")
stock_results = stock_backtest.run_backtest()
if stock_results is not None:
    print("Stock Backtest Performance:", stock_backtest.get_performance_metrics())

# Example for crypto
crypto_backtest = BackTest(ticker="bitcoin", period="6mo", interval="1d")
crypto_results = crypto_backtest.run_backtest()
if crypto_results is not None:
    print("Crypto Backtest Performance:", crypto_backtest.get_performance_metrics())
```

The backtest results and performance metrics will be saved to the `backtest_outputs` directory.

### Real-time Monitoring

To monitor a single asset in real-time:

```python
from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
import multiprocessing as mp

# Create a queue for trade signals
trade_queue = mp.Queue()

# Create and start a monitor
monitor = TickerMonitor(
    ticker="AAPL",
    trade_order_queue=trade_queue,
    entry_price=0,  # Not in a position initially
    process_name="AAPL_Monitor",
    backtest_scope="intraday",  # Uses 1-minute intervals
    leverage=1,
    stop_loss=0.05  # 5% stop loss
)
monitor.start()

# Process trade signals
while True:
    if not trade_queue.empty():
        signal = trade_queue.get()
        print(f"Received signal: {signal}")
        # Handle the signal (e.g., execute trade, update position)
```

To monitor multiple assets simultaneously:

```python
from stock_monitoring_app.utils.process_manager import ProcessManager

# Create a process manager
manager = ProcessManager()

# Start monitors for multiple assets
manager.start_monitor(ticker="AAPL", scope="intraday", entry_price=0, leverage=1, stop_loss=0.05)
manager.start_monitor(ticker="MSFT", scope="short", entry_price=0, leverage=1, stop_loss=0.05)
manager.start_monitor(ticker="bitcoin", scope="long", entry_price=0, leverage=1, stop_loss=0.07)

# Process messages from all monitors
while True:
    messages = manager.collect_messages()
    for msg in messages:
        if msg.get("type") == "trade_signal":
            # Process trade signal
            print(f"Signal for {msg.get('ticker')}: {msg.get('action')} at ${msg.get('price')}")
```

The monitoring system supports different time scopes:
- **intraday**: 1-minute intervals for 1 day
- **short**: 15-minute intervals for 1 week
- **long**: Daily intervals for 1 month

## Testing

This project uses `pytest` for running automated tests. The tests are located in the `tests/` directory, with specific configurations managed in `pytest.ini`.

To run the tests:

1.  Ensure you have `pytest` installed:
    ```bash
    pip install pytest
    ```
2.  Navigate to the project root directory (`my-pricer/`).
3.  Run pytest:
    ```bash
    pytest
    ```

The `pytest.ini` file contains configurations for `pytest`, such as marker definitions (e.g., `integration` tests) and warning filters.

## Examples

The `examples/` directory contains scripts demonstrating the core functionalities:

*   **[run_fetcher_example.py](examples/run_fetcher_example.py)**: Shows how to use the `PolygonFetcher` and `CoinGeckoFetcher` to retrieve market data.
*   **[run_indicators_example.py](examples/run_indicators_example.py)**: Demonstrates applying various technical indicators (RSI, MACD, Bollinger Bands, etc.) to a DataFrame.
*   **[run_strategy_example.py](examples/run_strategy_example.py)**: Illustrates how to configure `BaseStrategy` with a set of indicators and generate trading signals.
*   **[run_backtest_example.py](examples/run_backtest_example.py)**: Provides a full example of running the `BackTest` engine for both a stock and a cryptocurrency.
*   **[run_ticker_monitor_example.py](examples/run_ticker_monitor_example.py)**: Demonstrates how to use the `TickerMonitor` class to continuously monitor a specific ticker and generate real-time trading signals.
*   **[run_process_manager_example.py](examples/run_process_manager_example.py)**: Shows how to use the `ProcessManager` class to manage multiple ticker monitoring processes simultaneously.

**To run the examples:**

1.  Ensure you have followed the "Setup" instructions above.
2.  Navigate to the project root directory (`my-pricer/`).
3.  Execute the desired example script:
    ```bash
    python examples/run_backtest_example.py
    ```
    Or, if your `PYTHONPATH` is set up correctly:
    ```bash
    python -m examples.run_backtest_example
    ```

**Note:** The example scripts require API keys (especially `POLYGON_API_KEY` for stock data) to be set in your environment or a `.env` file for full functionality with live data.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
