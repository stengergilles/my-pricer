# Crypto Trading System with Hybrid Position Sizing

A sophisticated cryptocurrency trading system designed for high-spread environments, featuring adaptive position sizing, volatile crypto discovery, and Bayesian parameter optimization.

## 🎯 Key Features

- **Hybrid Position Sizing**: Automatically switches between aggressive (95%) and conservative (20% base) position sizing based on market volatility
- **Volatile Crypto Discovery**: Daily identification of top gainers/losers for optimal trading opportunities
- **Bayesian Optimization**: Advanced parameter tuning using Optuna for strategy optimization
- **Multiple Trading Strategies**: EMA crossovers, Bollinger Band breakouts, combined indicators
- **High-Spread Optimization**: Specifically designed to overcome 1%+ trading spreads
- **Comprehensive Backtesting**: Cython-optimized backtesting engine with realistic trading costs

## 🚀 Quick Start

### 1. Find Volatile Cryptocurrencies
```bash
python get_volatile_cryptos.py
```

### 2. Optimize Strategies on Volatile Cryptos
```bash
python volatile_crypto_optimizer.py --strategy EMA_Only --n-trials 30
```

### 3. View Results
```bash
python manage_results.py --top
```

### 4. Test Specific Crypto
```bash
python optimize_bayesian.py --crypto okb --strategy EMA_Only --n-trials 50
```

### 5. Run Web Application (Optional)
```bash
# See WEB_APP_README.md for detailed setup instructions
./start_dev_servers.sh
```

### 6. Run Tests
```bash
# See TESTING.md for comprehensive testing documentation
python run_tests.py --all
```

## 📊 System Performance

**Best Known Result:**
- **Crypto**: OKB (+49% daily volatility)
- **Strategy**: EMA_Only with hybrid position sizing
- **Performance**: +122.42% profit (6 trades, 33% win rate)
- **Key**: High volatility triggered fixed 95% position sizing

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Main project overview and quick start guide |
| [TESTING.md](TESTING.md) | Comprehensive testing framework documentation |
| [WEB_APP_README.md](WEB_APP_README.md) | Web application setup and usage guide |
| [Frontend Refactoring & Auth0 Integration](docs/session_summary_auth0_mui.md) | Summary of frontend refactoring to MUI and Auth0 setup |
| [docs/](docs/) | Detailed technical documentation for all components |

## 🏗️ Architecture

### Core Components

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| `backtester.py` | Core backtesting engine with hybrid position sizing | [docs/backtester.md](docs/backtester.md) |
| `optimize_bayesian.py` | Single-crypto Bayesian parameter optimization | [docs/bayesian_optimization.md](docs/bayesian_optimization.md) |
| `volatile_crypto_optimizer.py` | Batch optimization of volatile cryptocurrencies | [docs/volatile_crypto_optimizer.md](docs/volatile_crypto_optimizer.md) |
| `get_volatile_cryptos.py` | Daily volatile crypto discovery | [docs/volatile_crypto_discovery.md](docs/volatile_crypto_discovery.md) |

### Trading Strategies

| Strategy | Description | Documentation |
|----------|-------------|---------------|
| `EMA_Only` | EMA crossover with exits | [docs/strategies/ema_only.md](docs/strategies/ema_only.md) |
| `Strict` | Multi-indicator confirmation | [docs/strategies/strict.md](docs/strategies/strict.md) |
| `BB_Breakout` | Bollinger Band breakout | [docs/strategies/bb_breakout.md](docs/strategies/bb_breakout.md) |
| `BB_RSI` | Bollinger Bands with RSI filter | [docs/strategies/bb_rsi.md](docs/strategies/bb_rsi.md) |
| `Combined_Trigger_Verifier` | Advanced multi-signal strategy | [docs/strategies/combined_trigger_verifier.md](docs/strategies/combined_trigger_verifier.md) |

## 💡 Hybrid Position Sizing Logic

The system automatically adjusts position sizing based on market volatility:

### High Volatility (>20% daily move)
- **Position Size**: Fixed 95% of capital
- **Rationale**: Large price movements can overcome high spreads
- **Example**: OKB (+49% daily) → +122% profit

### Low Volatility (<20% daily move)
- **Base Position Size**: 20% of capital
- **Dynamic Adjustments**:
  - Strong performance (avg >5 profit): 40% position size
  - 2+ wins in last 3 trades: 36% position size
  - 1 win in last 3 trades: 20% position size (base)
  - 0 wins in last 3 trades: 6% position size

## 📁 File Organization

```
my-pricer/
├── README.md                          # This file
├── TESTING.md                         # Testing framework documentation
├── WEB_APP_README.md                  # Web application setup guide
├── docs/                              # Detailed documentation
│   ├── backtester.md
│   ├── bayesian_optimization.md
│   ├── volatile_crypto_optimizer.md
│   ├── volatile_crypto_discovery.md
│   └── strategies/
│       ├── ema_only.md
│       ├── strict.md
│       ├── bb_breakout.md
│       ├── bb_rsi.md
│       └── combined_trigger_verifier.md
├── tests/                             # Testing framework
│   ├── test_unit.py
│   ├── test_integration.py
│   ├── test_functional.py
│   └── test_performance.py
├── web/                               # Web application
│   ├── backend/                       # Flask API
│   └── frontend/                      # Next.js frontend
├── backtest_results/                  # All optimization results
│   ├── best_params_*.json
│   ├── volatile_optimization_results_*.json
│   └── volatile_cryptos.json
├── backtester.py                      # Core backtesting engine
├── optimize_bayesian.py               # Bayesian optimization
├── volatile_crypto_optimizer.py       # Batch volatile crypto optimization
├── get_volatile_cryptos.py           # Volatile crypto discovery
├── manage_results.py                 # Results management
├── run_tests.py                      # Main test runner
└── config.py                         # Strategy configurations
```

## 🔧 Installation & Setup

### Prerequisites
```bash
pip install numpy pandas optuna requests tqdm cython
```

### Compile Cython Backtester
```bash
python setup.py build_ext --inplace
```

### Verify Installation
```bash
python backtester.py --crypto bitcoin --strategy EMA_Only --single-run \
  --short-ema-period 10 --long-ema-period 30 \
  --rsi-oversold 30 --rsi-overbought 70 \
  --atr-period 14 --atr-multiple 2.0 \
  --fixed-stop-loss-percentage 0.02 --take-profit-multiple 2.0 \
  --macd-fast-period 12 --macd-slow-period 26 --macd-signal-period 9
```

## 📈 Daily Workflow

### 1. Morning Routine
```bash
# Find today's volatile cryptos
python get_volatile_cryptos.py

# Run batch optimization on top volatile cryptos
python volatile_crypto_optimizer.py --strategy EMA_Only --n-trials 30 --top-count 5
```

### 2. Analysis
```bash
# View best performing strategies
python manage_results.py --top

# Detailed results review
python manage_results.py --list
```

### 3. Focused Testing
```bash
# Deep dive on promising crypto
python optimize_bayesian.py --crypto <best_crypto> --strategy <best_strategy> --n-trials 100
```

## 🎯 Key Success Factors

1. **Target High Volatility**: Focus on cryptos with >20% daily moves
2. **Aggressive Sizing on Big Moves**: Use 95% position sizing when volatility is high
3. **Risk Management on Stable Assets**: Use dynamic sizing for <20% volatility
4. **High Take-Profit Ratios**: Let winners run with 3-4x take-profit multiples
5. **Momentum Strategies**: Focus on trend-following rather than mean-reversion
6. **Overcome Spread Costs**: Large price movements make 1% spreads negligible

## 📊 Performance Metrics

The system tracks comprehensive performance metrics:
- Total profit/loss and percentage returns
- Win rate and trade statistics
- Risk-adjusted returns (Sharpe ratio)
- Position sizing effectiveness
- Strategy-specific performance breakdown

## 🔄 Continuous Improvement

- **Daily Volatile Crypto Discovery**: Automatically finds new opportunities
- **Parameter Optimization**: Bayesian optimization finds optimal settings
- **Performance Tracking**: Historical results guide strategy selection
- **Adaptive Position Sizing**: Responds to changing market conditions

## 📞 Support & Contributing

For questions, issues, or contributions, please refer to the detailed documentation in the `docs/` folder.

## ⚠️ Risk Disclaimer

This system is designed for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Always conduct thorough testing and risk assessment before live trading.

---

**⚠️ DISCLAIMER: This is a toy/fun project for educational and research purposes only. This system is NOT intended for real trading or production use. Cryptocurrency trading involves substantial risk of loss. Always conduct thorough testing and risk assessment before any live trading.**

---
