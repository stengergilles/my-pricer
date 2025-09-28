# Optimizer Architecture

This document provides a detailed overview of the optimizer architecture, which is responsible for finding the best parameters for trading strategies.

## Components

The optimization engine is composed of three main components:

1.  **API Layer (`web/backend/api/`)**:
    *   `analysis.py`: Defines the API endpoints for running and retrieving analysis on cryptocurrencies.
    *   `crypto.py`: Provides endpoints for cryptocurrency-related operations, including discovery of volatile cryptos.
    *   These APIs serve as the primary interface for the frontend, delegating the core logic to the `TradingEngine`.

2.  **Core Optimizer (`core/optimizer.py`)**:
    *   This is the heart of the optimization engine, encapsulated in the `BayesianOptimizer` class.
    *   It uses the `optuna` library to perform Bayesian optimization, an intelligent search algorithm for finding optimal parameters.
    *   It integrates with the `BacktesterWrapper` to evaluate the performance of different parameter sets, using `total_profit_percentage` as the objective to maximize.
    *   It's designed to be strategy-agnostic, allowing it to optimize any trading strategy defined in the system.
    *   It can optimize a single cryptocurrency or a batch of volatile cryptocurrencies in parallel for efficiency.
    *   It includes robust error handling for things like API rate limits.

3.  **Trading Engine (`core/trading_engine.py`)**:
    *   The `TradingEngine` class acts as a central orchestrator, integrating all the different components of the trading system.
    *   It provides a unified facade for the API layer to access the functionality of the `BayesianOptimizer` and other components.
    *   The `analyze_crypto` method is a key feature that can use the results of the optimization to provide more insightful analysis.

## Workflow

The optimization process follows this general workflow:

1.  **Trigger**: The optimization process can be initiated in two ways:
    *   **Manual**: A user can trigger an optimization run through an API endpoint.
    *   **Scheduled**: A scheduled job can be configured to automatically run optimizations for a predefined set of cryptocurrencies on a regular basis.

2.  **Execution**: The `TradingEngine` receives the optimization request and delegates it to the `BayesianOptimizer`.

3.  **Optimization**: The `BayesianOptimizer` uses `optuna` to explore the parameter space of the selected trading strategy. For each set of parameters, it runs a backtest and evaluates the performance.

4.  **Saving Results**: The best-performing parameters and the overall optimization results are saved to JSON files in the `results` directory.

5.  **Analysis**: When a user requests an analysis for a cryptocurrency, the `TradingEngine` can load the pre-optimized parameters to run the analysis with the best-known configuration, providing a more accurate and reliable assessment of the crypto's potential.

This modular and robust architecture allows for efficient and effective optimization of trading strategies, which is a cornerstone of the trading system.
