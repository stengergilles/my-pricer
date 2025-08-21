# Backtester Engine

The core backtesting engine that simulates trading strategies with realistic market conditions and hybrid position sizing.

## Overview

The backtester is implemented in Cython for high performance and includes sophisticated position sizing logic that adapts to market volatility. It's designed specifically for high-spread trading environments where traditional strategies often fail.

## Key Features

### Hybrid Position Sizing
- **High Volatility (>20% daily)**: Fixed 95% position sizing
- **Low Volatility (<20% daily)**: Dynamic position sizing based on recent performance
- **Automatic Detection**: Calculates daily volatility and switches modes automatically

### Realistic Trading Costs
- **Spread**: 1% (configurable, based on your trading platform)
- **Slippage**: 0.05% (realistic market impact)
- **Proper Cost Application**: Spread and slippage applied correctly without double-counting

### Risk Management
- **Fixed Stop Loss**: Percentage-based stop loss
- **Take Profit**: Multiple-based take profit (e.g., 3x risk)
- **ATR Trailing Stops**: Dynamic stops based on Average True Range
- **Position Limits**: Minimum 5%, maximum 95% position sizes

## How It Works

### 1. Data Processing
```python
# Convert price data to numpy arrays for Cython processing
prices = self.data['close'].to_numpy(dtype=np.float64)
long_entry, short_entry, long_exit, short_exit = self.strategy.generate_signals(self.data, params)
```

### 2. Volatility Detection
```python
# Calculate daily volatility for position sizing decision
daily_volatility = abs((prices[-1] - prices[0]) / prices[0])

if daily_volatility > 0.20:  # 20% threshold
    use_fixed_sizing = True  # 95% position size
else:
    use_dynamic_sizing = True  # Performance-based sizing
```

### 3. Position Sizing Logic

#### Fixed Sizing (High Volatility)
```python
position_size = current_capital * 0.95  # Aggressive 95% sizing
```

#### Dynamic Sizing (Low Volatility)
```python
# Base: 20% of capital
# Adjustments based on recent 3 trades:
# - Strong performance (avg >5 profit): 2.0x multiplier (40%)
# - 2+ wins in last 3: 1.8x multiplier (36%)
# - 1 win in last 3: 1.0x multiplier (20%)
# - 0 wins in last 3: 0.3x multiplier (6%)
```

### 4. Trade Execution
```python
# Entry with proper cost application
entry_price = current_price * (1 + spread_percentage + slippage_percentage)

# Exit with proper cost application  
exit_price = current_price * (1 - spread_percentage - slippage_percentage)

# Profit calculation
profit_loss = (exit_price - entry_price) / entry_price * position_size
```

## Why This Design?

### Problem: High Trading Spreads
Traditional backtesting assumes low spreads (0.1-0.2%). Your platform has 1% spreads, making most strategies unprofitable.

### Solution: Volatility-Based Position Sizing
- **High volatility cryptos**: Large price moves (20-50%) can easily overcome 1% spreads
- **Low volatility cryptos**: Conservative sizing protects capital when moves are small

### Example: OKB Success Case
- **Daily Move**: +49% (high volatility)
- **Position Sizing**: Fixed 95% (aggressive)
- **Result**: +122% profit (spread becomes negligible)
- **Logic**: 49% price move >> 2% round-trip cost

## Usage

### Single Backtest
```bash
python backtester.py --crypto okb --strategy EMA_Only --single-run \
  --short-ema-period 10 --long-ema-period 47 \
  --fixed-stop-loss-percentage 0.042 --take-profit-multiple 3.98
```

### Parameters
- `--crypto`: Cryptocurrency ID from CoinGecko
- `--strategy`: Trading strategy name
- `--single-run`: Run single backtest with specified parameters
- Strategy-specific parameters (EMA periods, RSI levels, etc.)

### Output Metrics
- **Final Capital**: Ending account value
- **Total Profit/Loss**: Absolute and percentage returns
- **Trade Statistics**: Win rate, number of trades, long/short breakdown
- **Risk Metrics**: Sharpe ratio (when applicable)

## Performance Optimization

### Cython Implementation
- Core trading loop implemented in Cython for speed
- Handles large datasets (thousands of price points) efficiently
- Memory-efficient array operations

### Vectorized Operations
- Signal generation uses pandas vectorized operations
- Indicator calculations optimized for performance
- Minimal Python loops in critical paths

## Configuration

### Position Sizing Parameters
```python
base_position_percentage = 0.20      # 20% base for dynamic sizing
fixed_position_percentage = 0.95     # 95% for high volatility
volatility_threshold = 0.20          # 20% daily move threshold
min_position_percentage = 0.05       # 5% minimum position
max_position_percentage = 0.95       # 95% maximum position
```

### Trading Costs
```python
DEFAULT_SPREAD_PERCENTAGE = 0.01     # 1% spread (platform-specific)
DEFAULT_SLIPPAGE_PERCENTAGE = 0.0005 # 0.05% slippage (realistic)
```

## Integration

The backtester integrates with:
- **Strategy Engine**: Receives buy/sell signals
- **Indicator Library**: Uses technical indicators for signal generation
- **Optimization Engines**: Provides performance metrics for parameter tuning
- **Results Management**: Outputs standardized performance data

## Best Practices

1. **Test with Sufficient Data**: Use at least 30 days of data for reliable indicator calculations
2. **Validate Parameters**: Ensure indicator periods don't exceed available data points
3. **Monitor Position Sizing**: Check that volatility detection is working correctly
4. **Realistic Expectations**: Remember that 1% spreads require significant price movements for profitability

## Limitations

- **Historical Data Only**: Cannot account for future market regime changes
- **Simplified Market Model**: Assumes perfect order execution at calculated prices
- **No Liquidity Constraints**: Doesn't model market depth or large order impact
- **Static Spread**: Uses fixed spread percentage (real spreads may vary)

The backtester is the foundation of the trading system, providing reliable performance measurement in high-spread environments through intelligent position sizing and realistic cost modeling.
