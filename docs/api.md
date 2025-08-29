# Backend API Documentation

This document provides a comprehensive overview of the backend API endpoints, their functionalities, request/response formats, and authentication mechanisms.

## Authentication

The backend API uses Auth0 for authentication in a production environment. For testing and development, authentication can be bypassed by setting the `SKIP_AUTH` environment variable to `true` or `FLASK_ENV` to `testing`.

API endpoints that require authentication are decorated with `@auth_required`.

## API Endpoints

### 1. `/api/config` (GET)

*   **Description:** Returns public configuration settings.
*   **Authentication:** None required.
*   **Response:**
    ```json
    {
        "some_config_key": "some_value",
        "another_config_key": "another_value"
    }
    ```

### 2. `/api/health` (GET)

*   **Description:** System health check endpoint.
*   **Authentication:** None required.
*   **Response:**
    ```json
    {
        "status": "healthy", // or "error"
        "message": "Health check successful", // or error message
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 3. `/api/auth/test` (GET)

*   **Description:** Test Auth0 authentication.
*   **Authentication:** `auth_required` (Auth0 in production).
*   **Response:**
    ```json
    {
        "message": "Authentication successful",
        "user": {
            "sub": "auth0|...",
            "name": "user@example.com"
        },
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 4. `/api/log` (POST)

*   **Description:** Receives frontend log messages.
*   **Authentication:** None required.
*   **Request Body:**
    ```json
    {
        "level": "info", // "error", "warn", "info"
        "message": "Log message from frontend"
    }
    ```
*   **Response:**
    ```json
    {
        "status": "success" // or "error"
    }
    ```

### 5. `/api/cryptos` (GET)

*   **Description:** Get cryptocurrency data.
*   **Authentication:** `auth_required` (currently commented out in `CryptoAPI`).
*   **Query Parameters:**
    *   `limit` (int, default: 100): Maximum number of cryptos to return.
    *   `volatile` (boolean, default: `false`): If `true`, returns only volatile cryptos.
    *   `min_volatility` (float, default: 20.0): Minimum volatility threshold (used when `volatile` is `true`).
    *   `force_refresh` (boolean, default: `false`): If `true`, forces a refresh of data.
*   **Response:**
    ```json
    {
        "cryptos": [
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "BTC",
                "current_price": 35000,
                "daily_volatility": 5.2
            }
        ],
        "count": 1,
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 6. `/api/cryptos/<string:crypto_id>` (GET)

*   **Description:** Get specific cryptocurrency information.
*   **Authentication:** `auth_required` (currently commented out in `CryptoAPI`).
*   **Path Parameters:**
    *   `crypto_id` (string, required): The ID of the cryptocurrency (e.g., `bitcoin`).
*   **Response:**
    ```json
    {
        "crypto": {
            "id": "bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "current_price": 35000,
            "daily_volatility": 5.2
        },
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 7. `/api/cryptos` (POST)

*   **Description:** Perform crypto operations like analysis, discovery, search, or top movers.
*   **Authentication:** `auth_required` (currently commented out in `CryptoAPI`).
*   **Request Body:** JSON object with an `action` field and action-specific parameters:

    *   **Action: `"analyze"`**
        *   **Description:** Run analysis on a cryptocurrency.
        *   **Parameters:**
            *   `crypto_id` (string, required): The ID of the cryptocurrency.
            *   `strategy` (string, optional): The name of the strategy to use for analysis.
            *   `parameters` (object, optional): Custom parameters for the strategy.
            *   `timeframe` (string, optional, default: `"7d"`): The timeframe for analysis (e.g., `"7d"`, `"30d"`).
        *   **Response:**
            ```json
            {
                "action": "analyze",
                "result": {
                    "crypto_id": "bitcoin",
                    "analysis_data": "..."
                },
                "timestamp": "2023-10-27T10:00:00.000000"
            }
            ```

    *   **Action: `"discover_volatile"`**
        *   **Description:** Discover volatile cryptocurrencies.
        *   **Parameters:**
            *   `min_volatility` (float, optional, default: 5.0): Minimum volatility threshold.
            *   `limit` (int, optional, default: 50): Maximum number of volatile cryptos to return.
        *   **Response:**
            ```json
            {
                "action": "discover_volatile",
                "cryptos": [
                    { "id": "crypto1", "daily_volatility": 10.5 },
                    { "id": "crypto2", "daily_volatility": 8.2 }
                ],
                "count": 2,
                "min_volatility": 5.0,
                "timestamp": "2023-10-27T10:00:00.000000"
            }
            ```

    *   **Action: `"top_movers"`**
        *   **Description:** Get top moving cryptocurrencies.
        *   **Parameters:**
            *   `count` (int, optional, default: 10): Number of top movers to return.
        *   **Response:**
            ```json
            {
                "action": "top_movers",
                "movers": [
                    { "id": "cryptoA", "change": 15.0 },
                    { "id": "cryptoB", "change": -12.0 }
                ],
                "count": 2,
                "timestamp": "2023-10-27T10:00:00.000000"
            }
            ```

    *   **Action: `"search"`**
        *   **Description:** Search for cryptocurrencies by query.
        *   **Parameters:**
            *   `query` (string, required): The search query (e.g., `"bit"`).
            *   `limit` (int, optional, default: 10): Maximum number of search results.
        *   **Response:**
            ```json
            {
                "action": "search",
                "query": "bit",
                "results": [
                    { "id": "bitcoin", "name": "Bitcoin" },
                    { "id": "bitcash", "name": "BitCash" }
                ],
                "count": 2,
                "timestamp": "2023-10-27T10:00:00.000000"
            }
            ```

### 8. `/api/crypto_status/<string:crypto_id>` (GET)

*   **Description:** Get status for a specific cryptocurrency (e.g., if it has optimization results).
*   **Authentication:** `auth_required` (currently commented out in `CryptoStatusAPI`).
*   **Path Parameters:**
    *   `crypto_id` (string, required): The ID of the cryptocurrency.
*   **Response:**
    ```json
    {
        "crypto_id": "bitcoin",
        "has_config_params": true,
        "has_optimization_results": false,
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 9. `/api/analysis` (POST)

*   **Description:** Run analysis on a cryptocurrency.
*   **Authentication:** `auth_required` (currently commented out in `AnalysisAPI`).
*   **Request Body:**
    ```json
    {
        "crypto_id": "bitcoin",
        "strategy": "EMA_Only", // optional
        "parameters": {
            "short_ema_period": 10,
            "long_ema_period": 30
        }, // optional
        "timeframe": "7d" // optional, default: "7d"
    }
    ```
*   **Response:**
    ```json
    {
        "action": "analysis",
        "result": {
            "crypto_id": "bitcoin",
            "analysis_output": "..."
        },
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 10. `/api/backtest` (POST)

*   **Description:** Run a backtest or optimization.
*   **Authentication:** `auth_required` (currently commented out in `BacktestAPI`).
*   **Request Body:** JSON object with an `action` field and action-specific parameters:

    *   **Action: `"backtest"`**
        *   **Description:** Run a backtest for a specific crypto and strategy.
        *   **Parameters:**
            *   `crypto_id` (string, required): The ID of the cryptocurrency.
            *   `strategy_name` (string, required): The name of the strategy.
            *   `parameters` (object, optional): Parameters for the strategy.
            *   `timeframe` (string, optional, default: `"7d"`): The timeframe for the backtest.
            *   `interval` (string, optional, default: `"30m"`): The data interval (e.g., `"1h"`, `"4h"`).
        *   **Response:**
            ```json
            {
                "action": "backtest",
                "result": {
                    "crypto_id": "bitcoin",
                    "strategy_name": "EMA_Only",
                    "profit_percentage": 15.2,
                    "trades": 10
                }
            }
            ```

    *   **Action: `"optimize"`**
        *   **Description:** Run Bayesian optimization for a specific crypto and strategy.
        *   **Parameters:**
            *   `crypto_id` (string, required): The ID of the cryptocurrency.
            *   `strategy_name` (string, required): The name of the strategy.
            *   `n_trials` (int, optional, default: 50): Number of optimization trials.
            *   `timeout` (int, optional): Timeout in seconds for the optimization.
        *   **Response:**
            ```json
            {
                "action": "optimize",
                "result": {
                    "crypto_id": "bitcoin",
                    "strategy_name": "EMA_Only",
                    "best_params": { "short_ema_period": 12, "long_ema_period": 26 },
                    "best_profit": 20.5
                }
            }
            ```

    *   **Action: `"optimize_volatile"`**
        *   **Description:** Run batch optimization on volatile cryptocurrencies.
        *   **Parameters:**
            *   `strategy_name` (string, required): The name of the strategy.
            *   `n_trials` (int, optional, default: 30): Number of optimization trials per crypto.
            *   `top_count` (int, optional, default: 10): Number of top volatile cryptos to optimize.
            *   `min_volatility` (float, optional, default: 5.0): Minimum volatility threshold for volatile cryptos.
        *   **Response:**
            ```json
            {
                "action": "optimize_volatile",
                "result": [
                    { "crypto_id": "crypto1", "best_profit": 18.0 },
                    { "crypto_id": "crypto2", "best_profit": 12.3 }
                ]
            }
            ```

### 11. `/api/results/<string:result_type>` (GET)

*   **Description:** Get optimization, backtest, or analysis results.
*   **Authentication:** `auth_required` (currently commented out in `ResultsAPI`).
*   **Path Parameters:**
    *   `result_type` (string, required): Type of results to retrieve (`optimization`, `backtest`, or `analysis`).
*   **Query Parameters:**
    *   `crypto_id` (string, optional): Filter results by cryptocurrency ID.
    *   `strategy_name` (string, optional): Filter results by strategy name.
    *   `limit` (int, optional, default: 50): Maximum number of results to return.
*   **Response:**
    ```json
    {
        "result_type": "optimization",
        "results": [
            {
                "crypto_id": "bitcoin",
                "strategy_name": "EMA_Only",
                "profit": 20.5,
                "params": { ... }
            }
        ],
        "timestamp": "2023-10-27T10:00:00.000000"
    }
    ```

### 12. `/api/strategies` (GET)

*   **Description:** Get available trading strategies.
*   **Authentication:** `auth_required` (currently commented out in `StrategiesAPI`).
*   **Response:**
    ```json
    {
        "strategies": [
            "EMA_Only",
            "Strict",
            "BB_Breakout"
        ],
        "count": 3
    }
    ```

### 13. `/api/strategies/<string:strategy_name>` (GET)

*   **Description:** Get details of a specific strategy.
*   **Authentication:** `auth_required` (currently commented out in `StrategiesAPI`).
*   **Path Parameters:**
    *   `strategy_name` (string, required): The name of the strategy (e.g., `EMA_Only`).
*   **Response:**
    ```json
    {
        "strategy": {
            "name": "EMA_Only",
            "description": "EMA crossover strategy",
            "parameters": [
                { "name": "short_ema_period", "type": "int", "default": 10 },
                { "name": "long_ema_period", "type": "int", "default": 30 }
            ]
        }
    }
    ```

### 14. `/api/strategies` (POST)

*   **Description:** Validate strategy parameters or get default parameters.
*   **Authentication:** `auth_required` (currently commented out in `StrategiesAPI`).
*   **Request Body:** JSON object with an `action` field and action-specific parameters:

    *   **Action: `"validate_params"`**
        *   **Description:** Validate parameters for a given strategy.
        *   **Parameters:**
            *   `strategy` (string, required): The name of the strategy.
            *   `parameters` (object, optional): The parameters to validate.
        *   **Response:**
            ```json
            {
                "valid": true, // or false
                "errors": [] // or ["Parameter X is invalid"]
            }
            ```

    *   **Action: `"get_defaults"`**
        *   **Description:** Get default parameters for a given strategy.
        *   **Parameters:**
            *   `strategy` (string, required): The name of the strategy.
        *   **Response:**
            ```json
            {
                "defaults": {
                    "short_ema_period": 10,
                    "long_ema_period": 30
                }
            }
            ```
