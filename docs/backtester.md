# Backtester Architecture

This document provides a detailed overview of the backtesting engine's architecture, which is responsible for simulating trading strategies on historical data.

## Components

The backtesting engine is composed of several components, each with a specific responsibility:

1.  **API Layer (`web/backend/api/backtest.py`)**:
    *   This is the entry point for the frontend to interact with the backtesting engine.
    *   It provides API endpoints for running single backtests, initiating optimization processes, and retrieving backtest history and optimized parameters.
    *   It delegates the actual backtesting and optimization tasks to the `TradingEngine`.

2.  **Trading Engine (`core/trading_engine.py`)**:
    *   The `TradingEngine` acts as a central orchestrator, providing a unified interface to the various components of the trading system.
    *   It exposes the backtesting functionality to the API layer and other parts of the application.

3.  **Backtester Wrapper (`core/backtester_wrapper.py`)**:
    *   The `BacktesterWrapper` is a crucial abstraction layer that sits between the `TradingEngine` and the core backtesting logic.
    *   It provides a clean, high-level interface for running backtests, hiding the underlying implementation details.
    *   It's responsible for fetching historical data, preparing it for the backtester, and formatting the results into a standardized format.
    *   It also includes a fallback mechanism to generate mock results if the core backtester is not available, which is useful for development and testing.

4.  **Core Backtester (`backtester.py`)**:
    *   The `Backtester` class is the main component of the backtesting engine.
    *   It's responsible for preparing the data and trading signals for the Cython-optimized backtesting loop.
    *   It uses a `Strategy` object to generate the trading signals.
    *   It then calls the `run_backtest_cython` function to execute the backtest.

5.  **Cython Backtester (`backtester_cython.pyx`)**:
    *   This is the performance-critical heart of the backtesting engine.
    *   It's written in Cython, which compiles down to C code, resulting in a significant performance improvement over pure Python. This is essential for running the large number of backtests required by the optimization process.
    *   It performs a low-level, trade-by-trade simulation, taking into account realistic trading costs like spread and slippage.
    *   It implements sophisticated risk management features, including fixed and trailing stop-losses, as well as take-profit levels.
    *   It also features a dynamic position sizing mechanism that can adjust the trade size based on market volatility and recent performance.

## Workflow

The backtesting process follows this general workflow:

1.  **API Request**: The process begins with a request to the `BacktestAPI`, typically from the frontend, to run a backtest for a specific cryptocurrency, strategy, and set of parameters.

2.  **Delegation**: The API layer delegates the request to the `TradingEngine`, which in turn calls the `run_single_backtest` method of the `BacktesterWrapper`.

3.  **Data Fetching and Preparation**: The `BacktesterWrapper` fetches the required historical data and prepares it for the backtest. It then calls the `run_backtest` method of the `Backtester` class.

4.  **Signal Generation**: The `Backtester` uses the provided `Strategy` object to generate the trading signals for the historical data.

5.  **Cython Execution**: The `Backtester` then calls the `run_backtest_cython` function, passing it the price data, signals, and other parameters. This is where the high-performance simulation takes place.

6.  **Results**: The Cython function returns a detailed set of backtest results, which are then passed back up through the layers to the API and, finally, to the user.

This well-architected, multi-layered backtesting system is both powerful and performant. The use of Cython for the core simulation loop is a key design decision that enables the entire system, including the computationally intensive optimization process, to run efficiently.
