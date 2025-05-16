# Stock Monitoring and Backtesting Application

This project provides a framework for fetching financial market data, applying technical indicators, defining trading strategies, and backtesting these strategies against historical data.

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
    *   Evaluates strategy performance with various metrics (e.g., P&L, win rate, max drawdown - metrics are indicative).
    *   Saves backtest results (data with signals) and performance metrics to CSV and JSON files respectively in the `backtest_outputs` directory.



## Project Structure

A brief overview of the main directories:```
my-pricer/
├── stock_monitoring_app/ # Core application logic
│   ├── backtest/         # Backtesting engine
│   ├── fetchers/         # Data fetching modules (Polygon, CoinGecko)
│   ├── indicators/       # Technical indicator implementations
│   ├── strategies/       # Trading strategy logic
│   ├── config.py         # Application configuration (API keys, etc.)
│   └── __init__.py
├── examples/             # Example scripts demonstrating usage
│   ├── run_fetcher_example.py
│   ├── run_indicators_example.py
│   ├── run_strategy_example.py
│   ├── run_backtest_example.py
│   └── __init__.py
├── tests/                # Automated tests
│   ├── indicators/       # Tests for technical indicators
│   ├── fetchers/         # Tests for data fetchers
│   ├── test_backtest.py  # Tests for the backtesting engine

│   └── conftest.py       # Pytest fixtures and hooks (if created)
├── backtest_outputs/     # (Generated) Directory for storing backtest results
├── LICENSE               # Project license
├── pytest.ini            # Pytest configuration
├── requirements.txt      # Python package dependencies
└── README.md             # This file
```

## Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd my-pricer
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment. This project likely has dependencies such as `pandas`, `pandas-ta`, `requests`, `numpy`. If a `requirements.txt` file is present or created, use:

    ```bash
    pip install -r requirements.txt
    ```
    The <<FILE:requirements.txt:requirements.txt:>> file lists the necessary Python packages.

3.  **Environment Variables:**
    The application requires API keys for data fetchers. These are typically loaded from environment variables via a `config.py` (not provided in context, but inferred). You would need to set:
    *   `POLYGON_API_KEY`: Your API key for Polygon.io.
    *   `COINGECKO_API_KEY`: Your API key for CoinGecko (optional, for higher rate limits or Pro features).

    Refer to `stock_monitoring_app/config.py` (or create one) for how these are managed.

## Usage

The primary way to use this application is likely by running the backtester. This typically involves:
1.  Configuring a `BackTest` instance with a ticker, period, and interval.
2.  Calling the `run_backtest()` method.

*Example (conceptual, based on `stock_monitoring_app/backtest/backtest.py`):*
```python
# main.py or a script
from stock_monitoring_app.backtest.backtest import BackTest

if __name__ == "__main__":
    # Example for a stock
    # stock_backtest = BackTest(ticker="AAPL", period="1y", interval="1d")
    # stock_results = stock_backtest.run_backtest()
    # if stock_results is not None:    #     print("Stock Backtest Performance:", stock_backtest.get_performance_metrics())

    # Example for crypto
    crypto_backtest = BackTest(ticker="bitcoin", period="6mo", interval="1d")
    crypto_results = crypto_backtest.run_backtest()
    if crypto_results is not None:
        print("\nCrypto Backtest Performance:", crypto_backtest.get_performance_metrics())

```


The backtest results and performance metrics will be saved to the `backtest_outputs` directory at the project root.

## Testing

This project uses `pytest` for running automated tests. The tests are located in the `tests/` directory, with specific configurations managed in `pytest.ini`.

To run the tests:

1.  Ensure you have `pytest` and any other testing-specific dependencies installed. If they are part of a `requirements.txt` or a `dev-requirements.txt` (not provided in context), install them. Otherwise, install `pytest`:    ```bash
    pip install pytest
    ```
2.  Navigate to the project root directory (`my-pricer/`).
3.  Run pytest:
    ```bash
    pytest
    ```


The `pytest.ini` file (<<FILE:pytest.ini:pytest.ini:>>) contains configurations for `pytest`, such as marker definitions (e.g., `integration` tests) and warning filters. Refer to this file for more details on test execution options.

## Examples

The `examples/` directory contains scripts to demonstrate the core functionalities of this application:

*   **<<FILE:examples/run_fetcher_example.py:run_fetcher_example.py:>>**: Shows how to use the `PolygonFetcher` and `CoinGeckoFetcher` to retrieve market data.
*   **<<FILE:examples/run_indicators_example.py:run_indicators_example.py:>>**: Demonstrates applying various technical indicators (RSI, MACD, Bollinger Bands, etc.) to a DataFrame.
*   **<<FILE:examples/run_strategy_example.py:run_strategy_example.py:>>**: Illustrates how to configure `BaseStrategy` with a set of indicators and generate trading signals.
*   **<<FILE:examples/run_backtest_example.py:run_backtest_example.py:>>**: Provides a full example of running the `BackTest` engine for both a stock and a cryptocurrency, including data fetching, (placeholder) optimization, strategy execution, performance evaluation, and saving results.

**To run the examples:**

1.  Ensure you have followed the "Setup" instructions above, especially installing dependencies and configuring API keys.
2.  Navigate to the project root directory (`my-pricer/`).
3.  Execute the desired example script using Python. For example:
    ```bash
    python examples/run_backtest_example.py
    ```
    Or, if your `PYTHONPATH` is set up correctly to include the project root:
    ```bash
    python -m examples.run_backtest_example
    ```

**Note:** The example scripts might require API keys (especially `POLYGON_API_KEY` for stock data) to be set in your environment or a `.env` file for full functionality. They are designed to fall back to placeholder data or skip parts if keys are missing, but live data fetching will provide a more complete demonstration. The backtesting example, in particular, can take a few moments to run as it involves fetching data and multiple processing steps.

## License

This project is licensed under the MIT License. See the <<FILE:LICENSE:LICENSE:>> file for details.
