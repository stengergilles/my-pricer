# Ticker Monitor TUIA Textual-based TUI application to manage and display the state of `TickerMonitor` instances from the `stock_monitoring_app`.

## Prerequisites

- Python 3.8+
- The `stock_monitoring_app` (containing `TickerMonitor`) must be installed or accessible in your `PYTHONPATH`.

## Setup

1.  **Navigate to this directory (ticker_monitor_tui).**

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    Ensure that the dependencies for `stock_monitoring_app` (like `yfinance`, `pandas`, `numpy`, etc.) are also met, potentially by installing them in the same virtual environment or ensuring the TUI can find them.

## Running the Application

From the `my-pricer` project root directory (or ensuring `stock_monitoring_app` is in PYTHONPATH):

```bash
python ticker_monitor_tui/main_tui.py
```

Or, if you are inside the `ticker_monitor_tui` directory and your `PYTHONPATH` is set to include the parent `my-pricer` directory:```bash
python main_tui.py
```

## Features

- Add, Start, Stop, and Delete `TickerMonitor` configurations.
- View the status and key metrics of each monitor, updated based on trade orders.
