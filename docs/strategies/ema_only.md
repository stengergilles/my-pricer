# EMA Only Strategy

A pure momentum-based trading strategy using Exponential Moving Average (EMA) crossovers for both entry and exit signals. This strategy is optimized for high-volatility environments and trending markets.

## Overview

The EMA Only strategy is the most successful strategy in the system, particularly effective on volatile cryptocurrencies. It uses EMA crossovers to capture momentum moves while providing clear exit signals to lock in profits.

## Strategy Logic

### Entry Signals
- **Long Entry**: Short EMA crosses above Long EMA (bullish crossover)
- **Short Entry**: Short EMA crosses below Long EMA (bearish crossover)

### Exit Signals  
- **Long Exit**: Short EMA crosses below Long EMA (momentum reversal)
- **Short Exit**: Short EMA crosses above Long EMA (momentum reversal)

### Configuration
```python
"EMA_Only": {
    "long_entry": ["ema_crossover"],
    "short_entry": ["ema_crossunder"], 
    "long_exit": ["ema_crossunder"],
    "short_exit": ["ema_crossover"],
}
```

## Why This Strategy Works

### Momentum Capture
- **Trend Following**: Enters positions when momentum is established
- **Early Detection**: EMAs respond faster than SMAs to price changes
- **Sustained Moves**: Stays in position while trend continues

### High Volatility Optimization
- **Large Moves**: Designed to capture significant price movements (>20%)
- **Spread Tolerance**: Large moves easily overcome 1% trading spreads
- **Momentum Persistence**: Volatile assets often show sustained directional moves

### Simplicity Advantage
- **Clear Signals**: Unambiguous entry and exit conditions
- **No Conflicting Indicators**: Single indicator reduces false signals
- **Fast Execution**: Quick signal generation and processing

## Mathematical Foundation

### EMA Calculation
```python
# Exponential Moving Average formula
EMA_today = (Price_today × α) + (EMA_yesterday × (1 - α))

# Where α (smoothing factor) = 2 / (period + 1)
α = 2 / (ema_period + 1)
```

### Crossover Detection
```python
# Bullish crossover (long entry)
ema_crossover = (short_ema.shift(1) < long_ema.shift(1)) & (short_ema > long_ema)

# Bearish crossover (short entry) 
ema_crossunder = (short_ema.shift(1) > long_ema.shift(1)) & (short_ema < long_ema)
```

## Parameter Optimization

### Key Parameters
- **Short EMA Period**: Typically 5-30 periods
- **Long EMA Period**: Typically 20-100 periods
- **Period Relationship**: Long EMA must be > Short EMA

### Optimal Ranges (from backtesting)
```python
# Successful OKB parameters
short_ema_period = 10    # Fast response to price changes
long_ema_period = 47     # Trend confirmation
```

### Parameter Sensitivity
- **Short EMA**: Lower values = more signals, higher noise
- **Long EMA**: Higher values = fewer signals, stronger trends
- **Spread**: Wider spreads favor longer-term trends

## Performance Characteristics

### Best Known Results
- **Asset**: OKB (+49% daily volatility)
- **Performance**: +122.42% profit
- **Trades**: 6 total (3 long, 3 short)
- **Win Rate**: 33.33% (2 wins, 4 losses)
- **Key**: Large winners (127.58 profit) overcame small losers (-5.16 loss)

### Risk-Reward Profile
- **High Risk-Reward Ratio**: Winners significantly larger than losers
- **Low Win Rate Acceptable**: 33% win rate still profitable
- **Momentum Dependent**: Performance tied to trending market conditions

## Market Conditions

### Optimal Conditions
- **Trending Markets**: Strong directional moves up or down
- **High Volatility**: Daily moves >10-20%
- **Clear Momentum**: Sustained price movements in one direction

### Challenging Conditions
- **Sideways Markets**: Frequent whipsaws and false signals
- **Low Volatility**: Small moves insufficient to overcome spreads
- **Choppy Price Action**: Rapid reversals trigger frequent exits

## Integration with Position Sizing

### High Volatility Assets (>20% daily)
- **Position Size**: Fixed 95% of capital
- **Rationale**: Large moves can overcome any trading costs
- **Example**: OKB (+49% daily) → Aggressive sizing → +122% profit

### Low Volatility Assets (<20% daily)
- **Position Size**: Dynamic 20% base with performance adjustments
- **Rationale**: Conservative approach for smaller moves
- **Risk Management**: Reduces exposure when strategy underperforms

## Usage Examples

### Manual Testing
```bash
python backtester.py --crypto okb --strategy EMA_Only --single-run \
  --short-ema-period 10 --long-ema-period 47 \
  --fixed-stop-loss-percentage 0.042 --take-profit-multiple 3.98
```

### Optimization
```bash
python optimize_bayesian.py --crypto okb --strategy EMA_Only --n-trials 50
```

### Batch Testing
```bash
python volatile_crypto_optimizer.py --strategy EMA_Only --n-trials 30
```

## Advantages

### Simplicity
- **Single Indicator**: Reduces complexity and conflicting signals
- **Clear Rules**: Unambiguous entry and exit conditions
- **Fast Processing**: Quick signal generation and backtesting

### Momentum Capture
- **Trend Following**: Naturally aligns with market momentum
- **Early Entry**: Catches moves near the beginning of trends
- **Sustained Positions**: Stays in profitable trades while trend continues

### Volatility Tolerance
- **Spread Resilience**: Works well with high trading costs
- **Large Move Capture**: Designed for significant price movements
- **Risk Management**: Clear exit signals limit downside

## Disadvantages

### Whipsaw Risk
- **False Signals**: Crossovers in sideways markets generate losses
- **Frequent Reversals**: Choppy markets cause rapid entry/exit cycles
- **Spread Erosion**: Multiple small losses can accumulate

### Lagging Nature
- **Trend Confirmation**: Requires price movement before signal generation
- **Late Entry**: May miss early part of strong moves
- **Exit Delays**: Trend reversal confirmation can reduce profits

### Market Dependency
- **Trending Required**: Poor performance in non-trending markets
- **Volatility Dependent**: Needs significant price movements to be profitable
- **Regime Sensitivity**: Performance varies with market conditions

## Optimization Tips

### Parameter Selection
- **Shorter EMAs**: More responsive but more false signals
- **Longer EMAs**: Fewer signals but stronger trend confirmation
- **Ratio Consideration**: Long/Short EMA ratio affects signal frequency

### Risk Management
- **Stop Losses**: Use ATR-based or percentage-based stops
- **Take Profits**: High multiples (3-4x) let winners run
- **Position Sizing**: Adjust based on asset volatility

### Market Timing
- **Volatility Screening**: Focus on high-volatility assets
- **Trend Identification**: Use on assets showing clear directional bias
- **Avoid Ranges**: Skip sideways-moving markets

The EMA Only strategy represents the core momentum-capture approach of the trading system, optimized for high-volatility environments where large price movements can overcome significant trading spreads and generate substantial profits.
