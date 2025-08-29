# Crypto Trading System with Hybrid Position Sizing

A sophisticated cryptocurrency trading system designed for high-spread environments, featuring adaptive position sizing, volatile crypto discovery, and Bayesian parameter optimization.

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

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Main project overview and daily workflow |
| [Backend API Documentation](docs/api.md) | Detailed documentation for the backend REST API |
| [TESTING.md](TESTING.md) | Comprehensive testing framework documentation |
| [docs/README.md](docs/README.md) | Detailed technical documentation for all components |

## 📁 File Organization

```
my-pricer/
├── README.md                          # This file
├── TESTING.md                         # Testing framework documentation
├── docs/                              # Detailed documentation
│   ├── api.md                         # Backend API documentation
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



**⚠️ DISCLAIMER: This is a toy/fun project for educational and research purposes only. This system is NOT intended for real trading or production use. Cryptocurrency trading involves substantial risk of loss. Always conduct thorough testing and risk assessment before any live trading.**

---
