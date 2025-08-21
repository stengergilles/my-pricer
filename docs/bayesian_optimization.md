# Bayesian Optimization

Advanced parameter optimization using Optuna's Bayesian optimization algorithms to find optimal trading strategy parameters for individual cryptocurrencies.

## Overview

Bayesian optimization is a sophisticated approach to hyperparameter tuning that uses probabilistic models to efficiently explore the parameter space. Unlike grid search or random search, it learns from previous evaluations to make smarter choices about which parameters to test next.

## Why Bayesian Optimization?

### Problem: Massive Parameter Space
Trading strategies have many parameters:
- EMA periods (2 parameters)
- RSI levels (2 parameters) 
- MACD settings (3 parameters)
- Risk management (2 parameters)
- ATR settings (2 parameters)

**Total combinations**: Millions of possible parameter sets

### Traditional Approaches Fall Short
- **Grid Search**: Too slow (would take weeks)
- **Random Search**: Inefficient (wastes trials on poor areas)
- **Manual Tuning**: Biased and incomplete

### Bayesian Solution
- **Smart Exploration**: Focuses on promising parameter regions
- **Efficient**: Finds good parameters in 20-100 trials
- **Probabilistic**: Models uncertainty and balances exploration vs exploitation

## How It Works

### 1. Parameter Space Definition
```python
# Define search ranges based on available data
short_ema_period = trial.suggest_int('short_ema_period', 5, 30)
long_ema_period = trial.suggest_int('long_ema_period', short_ema_period + 1, 100)
take_profit_multiple = trial.suggest_float('take_profit_multiple', 2.0, 5.0)
```

### 2. Objective Function
```python
def objective(trial, crypto, strategy):
    # Get parameters from trial
    params = extract_trial_parameters(trial)
    
    # Run backtester with these parameters
    results = run_backtester(crypto, strategy, params)
    
    # Return metric to optimize (total profit/loss)
    return results['total_profit_loss']
```

### 3. Optimization Process
```python
# Create study and optimize
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)

# Get best parameters
best_params = study.best_trial.params
best_profit = study.best_trial.value
```

## Parameter Constraints

### Data-Bounded Constraints
Parameters are constrained by available data to prevent invalid configurations:

```python
# Maximum periods based on available data points
max_data_points = 300  # Conservative estimate for 7 days at 30min intervals

# EMA constraints
short_ema_period = trial.suggest_int('short_ema_period', 5, 30)
long_ema_period = trial.suggest_int('long_ema_period', short_ema_period + 1, 
                                   min(100, max_data_points // 3))

# MACD constraints (ensure fast < slow)
macd_fast_period = trial.suggest_int('macd_fast_period', 5, 25)
macd_slow_period = trial.suggest_int('macd_slow_period', macd_fast_period + 5, 
                                    min(50, max_data_points // 6))

# RSI constraints (ensure overbought > oversold)
rsi_oversold = trial.suggest_int('rsi_oversold', 5, 35)
rsi_overbought = trial.suggest_int('rsi_overbought', rsi_oversold + 20, 95)
```

### Why These Constraints Matter
- **Prevents Invalid Combinations**: Long EMA can't be shorter than short EMA
- **Ensures Sufficient Data**: Indicators need enough historical points to calculate
- **Logical Relationships**: RSI overbought must be higher than oversold

## Optimization Strategy

### Multi-Objective Considerations
While the primary objective is profit maximization, the system also considers:

```python
# Penalty for strategies with too few trades
total_trades = results.get('total_trades', 0)
if total_trades < 2:
    total_profit_loss -= 50.0  # Penalize strategies with insufficient data
elif total_trades < 5:
    total_profit_loss -= 10.0  # Small penalty for few trades
```

### Search Space Efficiency
- **Focused Ranges**: Parameters ranges based on market analysis
- **Hierarchical Constraints**: Dependent parameters properly constrained
- **Realistic Bounds**: Avoid extreme values that don't make trading sense

## Usage

### Basic Optimization
```bash
python optimize_bayesian.py --crypto bitcoin --strategy EMA_Only --n-trials 50
```

### Parameters
- `--crypto`: Cryptocurrency to optimize (e.g., bitcoin, ethereum, okb)
- `--strategy`: Trading strategy to use (EMA_Only, BB_Breakout, etc.)
- `--n-trials`: Number of optimization trials (default: 100)

### Output
```
--- Optimization Finished ---
Number of finished trials: 50
Best trial:
  Value (Total Profit/Loss): 122.42
  Params: 
    short_ema_period: 10
    long_ema_period: 47
    take_profit_multiple: 3.98
    fixed_stop_loss_percentage: 0.042
    ...

Best parameters saved to: backtest_results/best_params_okb_EMA_Only_bayesian.json
```

## Integration with Hybrid Position Sizing

The Bayesian optimizer works seamlessly with the hybrid position sizing system:

### High Volatility Cryptos
- **Automatic Detection**: System detects >20% daily moves
- **Fixed Sizing**: Uses 95% position sizing regardless of parameters
- **Focus on Strategy**: Optimization focuses on entry/exit timing and risk management

### Low Volatility Cryptos  
- **Dynamic Sizing**: Uses performance-based position sizing
- **Conservative Approach**: Optimization balances profit with risk management
- **Parameter Sensitivity**: Position sizing parameters become more important

## Advanced Features

### Pruning
Optuna can terminate unpromising trials early:
```python
# If intermediate results are poor, prune the trial
if intermediate_value < threshold:
    raise optuna.TrialPruned()
```

### Multi-Objective Optimization
Can optimize for multiple objectives simultaneously:
```python
# Optimize for both profit and Sharpe ratio
return [total_profit, sharpe_ratio]
```

### Parallel Optimization
Can run multiple trials in parallel for faster results:
```python
# Use multiple processes for optimization
study.optimize(objective, n_trials=100, n_jobs=4)
```

## Best Practices

### Trial Count Guidelines
- **Quick Test**: 10-20 trials for initial exploration
- **Standard Optimization**: 50-100 trials for good results
- **Deep Optimization**: 200+ trials for maximum performance

### Parameter Range Selection
- **Start Wide**: Begin with broad parameter ranges
- **Narrow Down**: Focus on promising regions in subsequent runs
- **Market-Aware**: Consider market characteristics when setting bounds

### Result Validation
- **Out-of-Sample Testing**: Test best parameters on different time periods
- **Multiple Runs**: Run optimization multiple times to check consistency
- **Cross-Validation**: Validate on different market conditions

## Common Issues and Solutions

### Issue: All Trials Return -1000000
**Cause**: Parameters generating no trades or invalid configurations
**Solution**: Check parameter constraints and data availability

### Issue: Optimization Stuck in Local Minimum
**Cause**: Search space too narrow or insufficient exploration
**Solution**: Increase trial count or widen parameter ranges

### Issue: Best Parameters Don't Generalize
**Cause**: Overfitting to specific market conditions
**Solution**: Use longer data periods and cross-validation

## Performance Tips

### Efficient Parameter Spaces
- **Log Scale**: Use log scale for parameters that vary by orders of magnitude
- **Categorical**: Use categorical suggestions for discrete choices
- **Conditional**: Make parameters conditional on others when appropriate

### Faster Evaluation
- **Cython Backtester**: Already optimized for speed
- **Parallel Trials**: Use multiple processes when possible
- **Early Stopping**: Implement pruning for obviously poor trials

The Bayesian optimization system provides an efficient way to find optimal parameters for individual cryptocurrencies, taking advantage of the hybrid position sizing system to maximize profits while managing risk appropriately for each asset's volatility profile.
