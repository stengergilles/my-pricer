# Bollinger Band RSI Strategy

A refined breakout strategy that combines Bollinger Band breakouts with RSI filtering to improve signal quality and reduce false breakouts. Designed to capture high-probability volatility expansions while avoiding overbought/oversold extremes.

## Overview

The BB RSI strategy enhances the basic Bollinger Band breakout approach by adding RSI (Relative Strength Index) filters. This combination aims to catch breakouts that have momentum support while avoiding entries at price extremes that are likely to reverse quickly.

## Strategy Logic

### Entry Signals
- **Long Entry**: BOTH conditions must be met:
  - Price breaks above the upper Bollinger Band
  - RSI is not overbought (RSI < overbought threshold)

- **Short Entry**: BOTH conditions must be met:
  - Price breaks below the lower Bollinger Band  
  - RSI is not oversold (RSI > oversold threshold)

### Exit Signals
- **Long Exit**: Price crosses back below the middle Bollinger Band
- **Short Exit**: Price crosses back above the middle Bollinger Band

### Configuration
```python
"BB_RSI": {
    "long_entry": ["price_breaks_upper_band", "rsi_is_not_overbought"],
    "short_entry": ["price_breaks_lower_band", "rsi_is_not_oversold"],
    "long_exit": ["price_crosses_middle_band_from_top"],
    "short_exit": ["price_crosses_middle_band_from_bottom"],
}
```

## Why Add RSI Filtering?

### Problem with Pure BB Breakouts
- **False Breakouts**: Price may break bands but quickly reverse
- **Exhaustion Moves**: Breakouts at extreme RSI levels often fail
- **Momentum Gaps**: Breakouts without momentum support are weak

### RSI Solution
- **Momentum Confirmation**: RSI ensures momentum supports the breakout
- **Extreme Avoidance**: Filters out breakouts at overbought/oversold levels
- **Quality Improvement**: Reduces false signals at the cost of some opportunities

### Market Psychology
- **Sustainable Breakouts**: Breakouts with momentum are more likely to continue
- **Exhaustion Recognition**: Extreme RSI levels suggest potential reversal
- **Timing Optimization**: Better entry timing improves risk-reward ratio

## Technical Foundation

### Bollinger Bands Component
```python
# Standard Bollinger Bands (same as BB_Breakout)
middle_band = SMA(close, bb_period)
std_dev = STDEV(close, bb_period)
upper_band = middle_band + (std_dev * bb_multiplier)
lower_band = middle_band - (std_dev * bb_multiplier)
```

### RSI Component
```python
# Relative Strength Index
rsi = calculate_rsi(close, rsi_period)

# RSI filters
rsi_is_not_overbought = rsi < rsi_overbought_threshold  # e.g., < 70
rsi_is_not_oversold = rsi > rsi_oversold_threshold      # e.g., > 30
```

### Combined Signal Logic
```python
# Long entry: BB breakout + RSI not overbought
long_entry = (high > upper_band) & (rsi < rsi_overbought)

# Short entry: BB breakout + RSI not oversold  
short_entry = (low < lower_band) & (rsi > rsi_oversold)
```

## Parameter Optimization

### Bollinger Band Parameters
- **BB Period**: 15-25 periods (standard: 20)
- **BB Multiplier**: 1.8-2.5 (standard: 2.0)

### RSI Parameters
- **RSI Period**: 10-20 periods (standard: 14)
- **Overbought Level**: 65-85 (standard: 70)
- **Oversold Level**: 15-35 (standard: 30)

### Typical Settings
```python
# Balanced configuration
bb_period = 20              # Standard BB period
bb_std_dev = 2.0           # Standard deviation multiplier
rsi_period = 14            # Standard RSI period
rsi_overbought = 70        # Standard overbought level
rsi_oversold = 30          # Standard oversold level
```

## Performance Characteristics

### Expected Improvements over BB Breakout
- **Higher Win Rate**: RSI filtering reduces false breakouts
- **Better Risk-Reward**: Avoids entries at price extremes
- **Reduced Whipsaws**: Momentum confirmation improves signal quality
- **Lower Frequency**: Fewer but higher-quality signals

### Trade-offs
- **Missed Opportunities**: Some profitable breakouts filtered out
- **Complexity**: Additional parameter to optimize and monitor
- **Lag**: RSI calculation adds slight delay to signal generation

## Market Conditions

### Optimal Conditions
- **Consolidation with Momentum**: Sideways markets with building pressure
- **Moderate RSI Levels**: RSI in 40-60 range during consolidation
- **Clear Breakout Direction**: Decisive moves beyond bands
- **Volume Confirmation**: High volume supporting the breakout

### Challenging Conditions
- **Extreme RSI Markets**: Persistent overbought/oversold conditions
- **Low Volatility**: Insufficient band compression/expansion cycles
- **Trending Markets**: Already expanded bands reduce opportunities
- **Whipsaw Conditions**: Rapid RSI oscillations create conflicting signals

## Integration with Position Sizing

### High Volatility Assets (>20% daily)
- **Position Size**: Fixed 95% of capital
- **Benefit**: High-quality breakouts in volatile assets often very profitable
- **Risk Management**: RSI filter reduces risk of exhaustion moves

### Low Volatility Assets (<20% daily)
- **Position Size**: Dynamic sizing based on performance
- **Conservative Approach**: Filtered signals match conservative sizing
- **Quality Focus**: Emphasis on signal quality over quantity

## Signal Quality Assessment

### High-Quality Signals
- **RSI in Neutral Zone**: RSI 40-60 during consolidation
- **Clean Band Break**: Decisive move beyond band with volume
- **Momentum Alignment**: RSI direction matches breakout direction
- **Follow-Through**: Continued movement after initial breakout

### Lower-Quality Signals
- **RSI Near Extremes**: RSI close to overbought/oversold levels
- **Marginal Breakouts**: Price barely touching bands
- **Divergent Momentum**: RSI not supporting breakout direction
- **Immediate Reversal**: Quick return inside bands after breakout

## Advantages

### Improved Signal Quality
- **False Signal Reduction**: RSI filter eliminates many whipsaws
- **Momentum Confirmation**: Ensures breakout has momentum support
- **Extreme Avoidance**: Prevents entries at likely reversal points

### Risk Management
- **Better Entry Timing**: Avoids exhaustion moves
- **Reduced Drawdowns**: Fewer false breakouts mean smaller losses
- **Consistent Performance**: More predictable signal behavior

### Adaptability
- **Market Responsive**: Works across different volatility regimes
- **Parameter Flexibility**: Can adjust RSI levels for different assets
- **Trend Neutral**: Works in both trending and ranging markets

## Disadvantages

### Opportunity Cost
- **Missed Breakouts**: Some profitable moves filtered out by RSI
- **Reduced Frequency**: Fewer trading opportunities overall
- **Late Entries**: Additional confirmation may delay entry

### Complexity
- **More Parameters**: Additional optimization complexity
- **Conflicting Signals**: BB and RSI may disagree
- **Computational Cost**: More calculations per signal

### Market Limitations
- **Trending Markets**: RSI may stay extreme during strong trends
- **Low Volatility**: May generate very few signals
- **Parameter Sensitivity**: Performance varies with RSI threshold settings

## Usage Examples

### Manual Testing
```bash
python backtester.py --crypto cardano --strategy BB_RSI --single-run \
  --bb-period 20 --bb-std-dev 2.0 \
  --rsi-period 14 --rsi-overbought 70 --rsi-oversold 30 \
  --fixed-stop-loss-percentage 0.025 --take-profit-multiple 3.0
```

### Optimization
```bash
python optimize_bayesian.py --crypto solana --strategy BB_RSI --n-trials 100
```

### Batch Testing
```bash
python volatile_crypto_optimizer.py --strategy BB_RSI --n-trials 50
```

## Enhancement Opportunities

### Dynamic RSI Thresholds
- **Volatility-Adjusted**: Adjust RSI levels based on market volatility
- **Adaptive Periods**: Change RSI period based on market conditions
- **Regime-Specific**: Different thresholds for bull/bear markets

### Additional Filters
- **Volume Confirmation**: Require volume spike on breakout
- **Trend Alignment**: Only trade breakouts in trend direction
- **Time Filters**: Avoid signals during low-liquidity periods

### Advanced Signal Processing
- **RSI Divergence**: Look for RSI divergence before breakouts
- **Multi-Timeframe**: Confirm signals across different timeframes
- **Correlation Analysis**: Avoid correlated breakouts across assets

## Comparison with Related Strategies

### vs BB Breakout
- **BB RSI**: Higher quality, lower frequency, more complex
- **BB Breakout**: Higher frequency, simpler, more false signals

### vs EMA Only
- **BB RSI**: Volatility-based, early entry, moderate complexity
- **EMA Only**: Momentum-based, trend following, simple

### vs Strict
- **BB RSI**: Two-indicator confirmation, breakout focus
- **Strict**: Three-indicator confirmation, trend focus

## Optimization Guidelines

### Parameter Relationships
- **Tighter RSI**: Fewer signals, higher quality
- **Looser RSI**: More signals, lower quality
- **BB Sensitivity**: Affects breakout frequency
- **Combined Effect**: Balance between BB and RSI sensitivity

### Market-Specific Tuning
- **Volatile Assets**: Tighter RSI thresholds (60/40 instead of 70/30)
- **Stable Assets**: Standard RSI thresholds (70/30)
- **Trending Markets**: Asymmetric thresholds (favor trend direction)

The BB RSI strategy represents a refined approach to breakout trading, combining volatility analysis with momentum confirmation to improve signal quality and reduce the risk of false breakouts in high-spread trading environments.
