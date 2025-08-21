# Strict Strategy

A conservative multi-indicator confirmation strategy that requires multiple technical signals to align before entering trades. Designed for risk-averse trading with higher win rates but potentially lower overall returns.

## Overview

The Strict strategy uses multiple technical indicators to confirm trade signals, reducing false positives at the cost of potentially missing some profitable opportunities. It's designed for traders who prefer higher win rates and more conservative risk management.

## Strategy Logic

### Entry Signals
- **Long Entry**: ALL conditions must be met:
  - SMA crossover (short SMA > long SMA)
  - MACD is bullish (MACD line > Signal line)
  - RSI is not overbought (RSI < overbought threshold)

- **Short Entry**: ALL conditions must be met:
  - SMA crossunder (short SMA < long SMA)
  - MACD is bearish (MACD line < Signal line)

### Exit Signals
- **Long Exit**: SMA crossunder (short SMA crosses below long SMA)
- **Short Exit**: SMA crossover (short SMA crosses above long SMA)

### Configuration
```python
"Strict": {
    "long_entry": ["sma_crossover", "macd_is_bullish", "rsi_is_not_overbought"],
    "short_entry": ["sma_crossunder", "macd_is_bearish"],
    "long_exit": ["sma_crossunder"],
    "short_exit": ["sma_crossover"],
}
```

## Why This Strategy Design?

### Multi-Indicator Confirmation
- **Reduces False Signals**: Multiple conditions filter out weak setups
- **Higher Confidence**: When all indicators align, signal strength is higher
- **Risk Management**: Conservative approach suitable for volatile markets

### Asymmetric Design
- **Long Bias Protection**: RSI filter prevents buying into overbought conditions
- **Short Simplicity**: Fewer conditions for short entries (momentum-based)
- **Market Reality**: Crypto markets tend to trend upward long-term

## Technical Indicators Used

### Simple Moving Averages (SMA)
```python
# Trend direction confirmation
short_sma = calculate_sma(data, short_sma_period)
long_sma = calculate_sma(data, long_sma_period)

sma_crossover = (short_sma.shift(1) < long_sma.shift(1)) & (short_sma > long_sma)
```

### MACD (Moving Average Convergence Divergence)
```python
# Momentum confirmation
macd_data = calculate_macd(data, fast_period, slow_period, signal_period)
macd_is_bullish = macd_data['MACD'] > macd_data['Signal']
```

### RSI (Relative Strength Index)
```python
# Overbought/oversold filter
rsi = calculate_rsi(data, rsi_period)
rsi_is_not_overbought = rsi < rsi_overbought_threshold
```

## Parameter Optimization

### Key Parameters
- **SMA Periods**: Short (5-50) and Long (20-200)
- **MACD Settings**: Fast (5-25), Slow (20-50), Signal (5-20)
- **RSI Levels**: Overbought (60-90), Period (10-20)

### Typical Ranges
```python
# Conservative settings
short_sma_period = 20      # Slower response, fewer false signals
long_sma_period = 50       # Trend confirmation
macd_fast_period = 12      # Standard MACD settings
macd_slow_period = 26
macd_signal_period = 9
rsi_overbought = 70        # Standard overbought level
```

## Performance Characteristics

### Expected Behavior
- **Higher Win Rate**: Multiple confirmations reduce false entries
- **Lower Trade Frequency**: Stricter conditions mean fewer signals
- **Smaller Drawdowns**: Conservative approach limits large losses
- **Trend Following**: Works best in clear trending markets

### Risk-Reward Profile
- **Lower Risk**: Multiple confirmations reduce bad entries
- **Moderate Reward**: May miss early parts of strong moves
- **Consistency**: More predictable performance patterns
- **Capital Preservation**: Focus on not losing money

## Market Conditions

### Optimal Conditions
- **Clear Trends**: Strong directional moves with momentum
- **Moderate Volatility**: Enough movement to generate profits without excessive noise
- **Trending Markets**: Sustained directional price action

### Challenging Conditions
- **Sideways Markets**: Multiple indicators may give conflicting signals
- **High Volatility**: Rapid changes may cause indicator lag
- **Whipsaw Markets**: Frequent reversals challenge confirmation approach

## Integration with Position Sizing

### High Volatility Assets (>20% daily)
- **Position Size**: Fixed 95% of capital
- **Benefit**: Conservative entry criteria with aggressive sizing
- **Risk**: May miss explosive moves due to confirmation delays

### Low Volatility Assets (<20% daily)
- **Position Size**: Dynamic sizing based on performance
- **Benefit**: Conservative approach matches conservative sizing
- **Advantage**: Reduced risk during uncertain market conditions

## Advantages

### Risk Management
- **Multiple Confirmations**: Reduces probability of false signals
- **Overbought Filter**: Prevents buying at market tops
- **Trend Alignment**: Ensures momentum supports the trade

### Consistency
- **Predictable Behavior**: Well-defined entry and exit rules
- **Lower Volatility**: More stable equity curve
- **Drawdown Control**: Conservative approach limits large losses

### Market Adaptability
- **Multiple Timeframes**: Works across different market cycles
- **Indicator Diversity**: Different indicators capture different market aspects
- **Robust Design**: Less likely to fail in changing market conditions

## Disadvantages

### Opportunity Cost
- **Missed Signals**: Strict requirements may filter out profitable trades
- **Late Entry**: Multiple confirmations can delay entry timing
- **Reduced Frequency**: Fewer trading opportunities overall

### Complexity
- **Multiple Parameters**: More indicators mean more parameters to optimize
- **Conflicting Signals**: Indicators may disagree, causing confusion
- **Computational Cost**: More calculations required per signal

### Market Lag
- **Confirmation Delays**: Waiting for multiple signals can miss fast moves
- **Trend Following**: Inherently lags market turns
- **Volatility Sensitivity**: High volatility can cause indicator whipsaws

## Usage Examples

### Manual Testing
```bash
python backtester.py --crypto bitcoin --strategy Strict --single-run \
  --short-sma-period 20 --long-sma-period 50 \
  --macd-fast-period 12 --macd-slow-period 26 --macd-signal-period 9 \
  --rsi-overbought 70
```

### Optimization
```bash
python optimize_bayesian.py --crypto ethereum --strategy Strict --n-trials 100
```

### Batch Testing
```bash
python volatile_crypto_optimizer.py --strategy Strict --n-trials 50
```

## Optimization Tips

### Parameter Balance
- **SMA Periods**: Balance responsiveness vs noise reduction
- **MACD Settings**: Standard settings often work well
- **RSI Levels**: Adjust based on asset volatility

### Market Selection
- **Trending Assets**: Focus on cryptocurrencies with clear directional bias
- **Moderate Volatility**: Avoid extremely volatile or stable assets
- **Liquid Markets**: Ensure sufficient volume for execution

### Risk Management
- **Stop Losses**: Use wider stops due to conservative entry
- **Take Profits**: Moderate multiples (2-3x) for consistent gains
- **Position Sizing**: Conservative sizing matches conservative strategy

## Comparison with EMA Only

### Trade-offs
- **Strict**: Higher win rate, lower frequency, more complex
- **EMA Only**: Lower win rate, higher frequency, simpler
- **Risk**: Strict is more conservative, EMA Only more aggressive
- **Returns**: EMA Only potentially higher returns, Strict more consistent

### Use Cases
- **Strict**: Risk-averse traders, uncertain market conditions
- **EMA Only**: Aggressive traders, clear trending markets
- **Portfolio**: Could use both strategies on different assets

The Strict strategy provides a conservative alternative to pure momentum strategies, using multiple indicator confirmation to improve trade quality at the cost of reduced frequency and potential opportunity cost.
