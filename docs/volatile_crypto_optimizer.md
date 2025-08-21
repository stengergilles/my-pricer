# Volatile Crypto Optimizer

Batch optimization system that automatically discovers volatile cryptocurrencies and runs Bayesian optimization on each to find the most profitable trading opportunities.

## Overview

The volatile crypto optimizer is the core discovery engine of the trading system. It combines market scanning with automated optimization to identify and capitalize on high-volatility trading opportunities that can overcome high trading spreads.

## Why Focus on Volatile Cryptos?

### The High-Spread Challenge
With 1% trading spreads, traditional strategies fail because:
- **Round-trip cost**: 2% minimum (1% buy + 1% sell)
- **Break-even requirement**: Strategies need >2% profit per trade
- **Most cryptos**: Daily moves of 1-5% aren't sufficient

### The Volatility Solution
Volatile cryptos with >20% daily moves:
- **Overcome spreads easily**: 20-50% moves make 2% costs negligible
- **Trend momentum**: Large moves often continue intraday
- **Profit potential**: Single trades can generate 10-100%+ returns

### Real Example: OKB Success
- **Daily move**: +49% (high volatility detected)
- **Position sizing**: Fixed 95% (aggressive)
- **Strategy result**: +122% profit in 6 trades
- **Key insight**: Volatility >> spread costs

## How It Works

### 1. Market Scanning
```python
# Fetch top cryptocurrencies by market cap
url = "https://api.coingecko.com/api/v3/coins/markets"
params = {
    'vs_currency': 'usd',
    'order': 'market_cap_desc',
    'per_page': 250,  # Scan top 250 cryptos
    'price_change_percentage': '24h'
}
```

### 2. Volatility Filtering
```python
# Filter for significant market cap and price change
valid_coins = [
    coin for coin in data 
    if coin.get('price_change_percentage_24h') is not None 
    and coin.get('market_cap', 0) > 1000000  # At least $1M market cap
    and coin.get('current_price', 0) > 0.000001  # Avoid dust coins
]
```

### 3. Selection Algorithm
```python
# Separate gainers and losers
gainers = [coin for coin in valid_coins if coin['price_change_percentage_24h'] > 0]
losers = [coin for coin in valid_coins if coin['price_change_percentage_24h'] < 0]

# Sort by absolute change
gainers.sort(key=lambda x: x['price_change_percentage_24h'], reverse=True)
losers.sort(key=lambda x: x['price_change_percentage_24h'])

# Select mix: top 3 gainers + top 2 losers
selected = gainers[:3] + losers[:2]
```

### 4. Batch Optimization
```python
for crypto in selected_cryptos:
    # Run Bayesian optimization on each
    result = run_bayesian_optimization(crypto['id'], strategy, n_trials)
    results.append(result)

# Rank by performance
results.sort(key=lambda x: x['best_value'], reverse=True)
```

## Selection Criteria

### Market Cap Filter
- **Minimum**: $1M market cap
- **Rationale**: Ensures sufficient liquidity and reduces manipulation risk
- **Avoids**: Micro-cap coins with extreme volatility but poor execution

### Price Filter
- **Minimum**: $0.000001 per coin
- **Rationale**: Eliminates dust tokens and calculation errors
- **Focus**: Tradeable assets with reasonable price precision

### Volatility Balance
- **Gainers**: Top 3 by percentage gain
- **Losers**: Top 2 by percentage loss
- **Rationale**: Captures both bullish momentum and oversold bounces
- **Diversity**: Avoids bias toward only one market direction

## Optimization Process

### Parameter Constraints
Each crypto gets optimized with data-appropriate constraints:
```python
# Adjust constraints based on available data
max_data_points = calculate_available_data(crypto_id)

# EMA periods bounded by data availability
long_ema_max = min(100, max_data_points // 3)

# MACD periods ensure sufficient calculation history
macd_slow_max = min(50, max_data_points // 6)
```

### Trial Allocation
- **Default**: 30 trials per crypto (good balance of speed vs accuracy)
- **Configurable**: Can adjust based on time constraints
- **Parallel**: Processes cryptos sequentially but trials can be parallelized

### Performance Tracking
```python
# Track execution time and results quality
result = {
    'crypto_id': crypto_id,
    'strategy': strategy,
    'best_value': best_profit_loss,
    'best_params': best_parameters,
    'execution_time': optimization_duration,
    'market_change_24h': daily_volatility_percentage
}
```

## Usage

### Basic Batch Optimization
```bash
python volatile_crypto_optimizer.py --strategy EMA_Only --n-trials 30
```

### Advanced Usage
```bash
# Optimize top 10 volatile cryptos with 50 trials each
python volatile_crypto_optimizer.py \
  --strategy EMA_Only \
  --n-trials 50 \
  --top-count 10 \
  --market-cap-limit 500
```

### Parameters
- `--strategy`: Trading strategy to optimize (default: EMA_Only)
- `--n-trials`: Bayesian trials per crypto (default: 30)
- `--top-count`: Number of volatile cryptos to test (default: 5)
- `--market-cap-limit`: How many top coins to scan (default: 100)

## Output and Results

### Console Output
```
=== Volatile Crypto Optimizer Started ===
Strategy: EMA_Only
Trials per crypto: 30
Top volatile count: 5

Fetching volatile cryptocurrencies from CoinGecko...
Selected volatile cryptocurrencies:
  okb: +49.42% ($189.2800)
  morpho: +12.88% ($2.3800)
  neo: +11.21% ($6.6800)

--- Optimizing 1/3: okb (+49.42%) ---
Optimization completed for okb in 20.6 seconds

============================================================
OPTIMIZATION RESULTS SUMMARY
============================================================
Top performing cryptocurrencies:
1. okb: 122.42 profit/loss
2. morpho: -15.23 profit/loss
3. neo: -45.67 profit/loss
```

### Saved Results
Results are automatically saved to:
```
backtest_results/volatile_optimization_results_YYYYMMDD_HHMMSS.json
```

Contains:
- **Timestamp**: When optimization was run
- **Configuration**: Strategy, trial count, parameters
- **Selected Coins**: Which cryptos were chosen and their volatility
- **Detailed Results**: Full optimization results for each crypto
- **Performance Metrics**: Execution times and success rates

## Integration with Position Sizing

### Automatic Volatility Detection
The optimizer works seamlessly with hybrid position sizing:

```python
# High volatility cryptos (>20% daily move)
if abs(daily_change) > 0.20:
    position_sizing = "Fixed 95%"  # Aggressive sizing
    rationale = "Large moves can overcome spread costs"

# Low volatility cryptos (<20% daily move)  
else:
    position_sizing = "Dynamic 20% base"  # Conservative sizing
    rationale = "Risk management for smaller moves"
```

### Strategy Adaptation
- **High Volatility**: Focus on momentum capture and trend following
- **Low Volatility**: Emphasize risk management and consistent small gains
- **Mixed Portfolio**: Automatically balances aggressive and conservative approaches

## Performance Analysis

### Success Metrics
The system tracks several key performance indicators:

```python
# Profitability metrics
profitable_cryptos = len([r for r in results if r['best_value'] > 0])
success_rate = profitable_cryptos / total_cryptos

# Volatility correlation
high_vol_performance = avg([r['best_value'] for r in results if r['volatility'] > 0.20])
low_vol_performance = avg([r['best_value'] for r in results if r['volatility'] < 0.20])
```

### Historical Patterns
- **High volatility cryptos**: Generally show better optimization results
- **Market direction**: Both gainers and losers can be profitable with right strategy
- **Time sensitivity**: Results are time-dependent due to changing market conditions

## Best Practices

### Timing
- **Run Daily**: Market volatility changes rapidly
- **Morning Execution**: Capture overnight moves and news events
- **Pre-Market**: Run before major trading sessions for best opportunities

### Parameter Selection
- **Trial Count**: 30 trials usually sufficient for initial discovery
- **Top Count**: 5-10 cryptos provides good coverage without overextension
- **Market Cap**: Focus on top 100-500 coins for liquidity

### Result Interpretation
- **Positive Results**: Immediate candidates for further testing
- **Negative Results**: May still be valuable in different market conditions
- **Volatility Correlation**: Higher volatility generally correlates with better results

## Limitations and Considerations

### Market Timing
- **Snapshot Dependency**: Based on current 24h volatility
- **Regime Changes**: High volatility may not persist
- **News Events**: Volatility may be event-driven and non-repeatable

### Execution Assumptions
- **Perfect Fills**: Assumes orders execute at calculated prices
- **Liquidity**: May not account for slippage on large orders
- **Market Hours**: Doesn't consider trading session differences

### Optimization Bias
- **Overfitting Risk**: Parameters optimized on recent data may not generalize
- **Selection Bias**: Only tests currently volatile cryptos
- **Survivorship Bias**: Doesn't account for delisted or failed projects

The volatile crypto optimizer is the discovery engine that identifies the most promising trading opportunities by combining market scanning with automated optimization, specifically designed to find assets whose volatility can overcome high trading spreads.
