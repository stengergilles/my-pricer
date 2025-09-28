# Crypto Trading System

This is a comprehensive cryptocurrency trading bot that includes backtesting, optimization, and paper trading capabilities. It features a web-based user interface for interacting with the system.

## Documentation

For a detailed understanding of the system's architecture, please refer to the following documents:

*   **[Optimizer](docs/optimizer.md):** Describes the Bayesian optimization engine used to find the best parameters for trading strategies.
*   **[Paper Trader](docs/paper_trader.md):** Explains the paper trading engine that simulates live trading with the optimized strategies.
*   **[Backtester](docs/backtester.md):** Details the backtesting engine used to evaluate the performance of trading strategies on historical data.
*   **[Strategies and Indicators](docs/strategy.md):** Provides an overview of how trading strategies and technical indicators are defined and used.

## Getting Started

### Prerequisites

*   Python 3.10+
*   Node.js and npm (for the frontend)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd my-pricer
    ```

2.  **Set up the Python environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Compile the Cython modules:**

    ```bash
    python setup.py build_ext --inplace
    ```

4.  **Set up the frontend:**

    ```bash
    cd web/frontend
    npm install
    ```

5.  **Configure the environment:**

    *   Create a `.env` file in the `web/backend` directory.
    *   Add the following environment variables:

        ```
        # Auth0 Configuration
        AUTH0_DOMAIN=your-auth0-domain
        AUTH0_API_AUDIENCE=your-auth0-api-audience

        # Flask Configuration
        SECRET_KEY=a-strong-secret-key
        FLASK_DEBUG=True

        # Frontend URL
        CORS_ORIGINS=http://localhost:3000
        ```

### Running the Application

1.  **Start the backend server:**

    ```bash
    python web/backend/app.py
    ```

2.  **Start the frontend development server:**

    ```bash
    cd web/frontend
    npm start
    ```

The application should now be running and accessible at `http://localhost:3000`.
