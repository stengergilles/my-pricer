# Strategy and Indicators Architecture

This document provides a detailed overview of the architecture for defining and using trading strategies and technical indicators.

## Components

The strategy and indicator system is composed of several components that work together to generate trading signals:

1.  **API Layer (`web/backend/api/strategies.py`)**:
    *   This is the entry point for the frontend to interact with the strategy management system.
    *   It provides API endpoints for listing available strategies, getting detailed information about a specific strategy, validating parameters, and retrieving default parameters.
    *   It delegates the actual logic to the `TradingEngine`.

2.  **Trading Engine (`core/trading_engine.py`)**:
    *   The `TradingEngine` acts as a central orchestrator, providing a unified interface to the strategy and indicator components.
    *   It's responsible for loading the strategy configurations and making them available to the rest of the application.

3.  **Strategy Definition (`strategy.py`)**:
    *   The `Strategy` class is a simple container that holds the configuration and parameters for a specific trading strategy.
    *   The `get_trade_signal` function is the core of the signal generation logic. It's a highly flexible function that can generate signals for any strategy defined in the `strategy_configs` dictionary.
    *   It dynamically determines which indicators are needed for a given strategy, calculates them, and then combines them to generate the final entry and exit signals.

4.  **Strategy Configuration (`config.py`)**:
    *   The actual trading strategies are defined in a declarative way in the `strategy_configs` dictionary within the `config.py` file.
    *   Each entry in this dictionary defines a strategy by specifying the "base signals" that are required for long/short entry and exit.
    *   This design is extremely flexible and extensible. New strategies can be created simply by adding a new entry to this dictionary, without needing to modify any of the core application code.

5.  **Indicator Calculation (`indicators.py`)**:
    *   This file contains the functions for calculating the various technical indicators used by the strategies (e.g., SMA, EMA, RSI, MACD, Bollinger Bands, ATR).
    *   It leverages the `ta` library for the more complex indicator calculations, which is a good practice that ensures accuracy and reliability.

## Workflow

The process of generating trading signals follows this general workflow:

1.  **Strategy Selection**: A strategy is selected, either by the user for a backtest or by the paper trading engine for live simulation.

2.  **Signal Generation Request**: The `generate_signals` method of the `Strategy` class is called.

3.  **Dynamic Indicator Calculation**: The `get_trade_signal` function first determines which technical indicators are required for the selected strategy. It then calculates only those indicators, which is an important optimization.

4.  **Base Signal Generation**: The function then generates a set of "base signals" from the calculated indicators. These are simple, reusable boolean signals (e.g., `sma_crossover`, `rsi_is_overbought`).

5.  **Signal Combination**: Finally, the function combines these base signals according to the logic defined in the `strategy_configs` dictionary for the selected strategy. This produces the final long/short entry and exit signals.

This architecture for defining and using trading strategies is modular, flexible, and highly extensible. The declarative approach to strategy definition is a key strength, as it allows for the rapid development and testing of new trading ideas without requiring changes to the core codebase.
