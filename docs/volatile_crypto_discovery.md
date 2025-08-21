# Volatile Crypto Discovery

Daily market scanning system that identifies the most volatile cryptocurrencies for optimal trading opportunities in high-spread environments.

## Overview

The volatile crypto discovery system is the first step in the daily trading workflow. It scans the cryptocurrency market to identify assets with significant price movements that can overcome high trading spreads and generate profitable trading opportunities.

## Why Volatile Crypto Discovery Matters

### The Spread Problem
With 1% trading spreads, most cryptocurrencies are unprofitable to trade:
- **Bitcoin/Ethereum**: Typical 1-5% daily moves
- **Round-trip cost**: 2% minimum (1% buy + 1% sell)
- **Net result**: Barely break-even or losses

### The Volatility Solution
Cryptocurrencies with >10% daily moves:
- **Overcome spreads**: Large moves make 2% costs negligible
- **Momentum opportunities**: Big moves often continue intraday
- **Profit potential**: Single trades can capture significant returns

### Market Efficiency
- **Daily scanning**: Markets change rapidly, yesterday's movers may not be today's
- **Automated discovery**: Removes human bias and emotion from selection
- **Systematic approach**: Consistent criteria for opportunity identification

## How It Works

### 1. Market Data Retrieval
```python
# Fetch comprehensive market data from CoinGecko
url = "https://api.coingecko.com/api/v3/coins/markets"
params = {
    'vs_currency': 'usd',
    'order': 'market_cap_desc',
    'per_page': 250,  # Scan top 250 cryptocurrencies
    'page': 1,
    'sparkline': False,
    'price_change_percentage': '24h'
}
```

### 2. Quality Filtering
```python
# Filter for tradeable, liquid assets
valid_coins = [
    coin for coin in data 
    if coin.get('price_change_percentage_24h') is not None  # Has price data
    and coin.get('market_cap', 0) > 1000000  # At least $1M market cap
    and coin.get('current_price', 0) > 0.000001  # Avoid dust coins
]
```

### 3. Volatility Analysis
```python
# Separate gainers and losers for balanced selection
gainers = [coin for coin in valid_coins if coin['price_change_percentage_24h'] > 0]
losers = [coin for coin in valid_coins if coin['price_change_percentage_24h'] < 0]

# Sort by absolute percentage change
gainers.sort(key=lambda x: x['price_change_percentage_24h'], reverse=True)
losers.sort(key=lambda x: x['price_change_percentage_24h'])
```

### 4. Selection Algorithm
```python
# Balanced selection: top gainers + top losers
top_volatile = []

# Add top 3 gainers
if len(gainers) >= 3:
    top_volatile.extend(gainers[:3])

# Add top 2 losers  
if len(losers) >= 2:
    top_volatile.extend(losers[:2])

# Fill remaining slots with most volatile overall
if len(top_volatile) < 5:
    all_volatile = sorted(valid_coins, 
                         key=lambda x: abs(x['price_change_percentage_24h']), 
                         reverse=True)
    for coin in all_volatile:
        if coin not in top_volatile and len(top_volatile) < 5:
            top_volatile.append(coin)
```

## Selection Criteria

### Market Cap Requirements
- **Minimum**: $1M market capitalization
- **Purpose**: Ensures sufficient liquidity for trading
- **Benefit**: Reduces risk of manipulation and poor execution
- **Trade-off**: May miss some extreme micro-cap opportunities

### Price Filtering
- **Minimum**: $0.000001 per token
- **Purpose**: Eliminates dust tokens and calculation errors
- **Benefit**: Focuses on assets with meaningful price precision
- **Implementation**: Prevents division by zero and extreme percentage calculations

### Volatility Thresholds
- **No minimum**: Captures all available volatility
- **Ranking based**: Selects top movers regardless of absolute threshold
- **Adaptive**: Adjusts to current market conditions automatically

## Output Format

### Console Display
```
🚀 TOP 10 GAINERS (24h):
------------------------------------------------------------
 1. okb                   +49.42% | $189.280000 | $3985.5M
 2. morpho                +12.88% | $  2.380000 | $ 778.5M
 3. neo                   +11.21% | $  6.680000 | $ 471.1M

📉 TOP 10 LOSERS (24h):
------------------------------------------------------------
 1. keeta                  -8.22% | $  1.100000 | $ 448.4M
 2. mantle                 -8.18% | $  1.260000 | $4260.1M
 3. lido-dao               -4.77% | $  1.280000 | $1144.7M

🎯 SELECTED FOR OPTIMIZATION:
------------------------------------------------------------
1. okb                   +49.42%
2. morpho                +12.88%
3. neo                   +11.21%
4. keeta                  -8.22%
5. mantle                 -8.18%
```

### Saved Data
Results saved to `backtest_results/volatile_cryptos.json`:
```json
{
  "timestamp": "2025-08-21 11:05:56.408462",
  "crypto_ids": ["okb", "morpho", "neo", "keeta", "mantle"]
}
```

## Usage

### Basic Discovery
```bash
python get_volatile_cryptos.py
```

### Integration with Optimization
```bash
# Discover volatile cryptos, then optimize them
python get_volatile_cryptos.py
python volatile_crypto_optimizer.py --strategy EMA_Only --n-trials 30
```

### Automated Daily Workflow
```bash
#!/bin/bash
# Daily trading discovery script
python get_volatile_cryptos.py
python volatile_crypto_optimizer.py --strategy EMA_Only --n-trials 30 --top-count 5
python manage_results.py --top
```

## Market Analysis Features

### Balanced Selection
- **Gainers**: Capture bullish momentum and breakout opportunities
- **Losers**: Identify oversold conditions and potential reversals
- **Diversification**: Reduces directional bias in strategy testing

### Market Cap Weighting
- **Large Cap**: More stable, lower manipulation risk
- **Mid Cap**: Balance of volatility and liquidity
- **Small Cap**: Higher volatility but execution risk

### Real-Time Adaptation
- **Market Conditions**: Automatically adapts to bull/bear markets
- **Volatility Regimes**: Captures both high and low volatility periods
- **News Events**: Responds to market-moving events automatically

## Integration Points

### With Volatile Crypto Optimizer
```python
# Load discovered cryptos
with open('backtest_results/volatile_cryptos.json', 'r') as f:
    data = json.load(f)
    crypto_ids = data['crypto_ids']

# Optimize each discovered crypto
for crypto_id in crypto_ids:
    optimize_crypto(crypto_id, strategy, n_trials)
```

### With Backtester
```python
# Test specific discovered crypto
python backtester.py --crypto okb --strategy EMA_Only --single-run
```

### With Results Management
```python
# Track discovery history
python manage_results.py --list  # Shows historical volatile crypto lists
```

## Performance Characteristics

### API Efficiency
- **Single Request**: Fetches all needed data in one API call
- **Rate Limiting**: Respects CoinGecko API limits
- **Error Handling**: Graceful degradation on API failures
- **Caching**: Could be extended with caching for repeated runs

### Processing Speed
- **Fast Filtering**: Efficient list comprehensions and sorting
- **Memory Efficient**: Processes data in-place without large copies
- **Scalable**: Can handle scanning 1000+ cryptocurrencies

### Data Quality
- **Validation**: Checks for None values and data completeness
- **Sanitization**: Filters out invalid or problematic assets
- **Consistency**: Standardized output format for downstream processing

## Best Practices

### Timing
- **Daily Execution**: Run once per day to capture fresh opportunities
- **Morning Preferred**: Execute before major trading sessions
- **Consistent Schedule**: Same time daily for comparable results

### Market Awareness
- **Weekend Effects**: Crypto markets trade 24/7, but patterns may differ
- **News Events**: Major announcements can create temporary volatility spikes
- **Market Cycles**: Bull/bear markets affect volatility patterns

### Risk Management
- **Diversification**: Don't rely on single volatile crypto
- **Position Sizing**: Use appropriate sizing for volatility level
- **Stop Losses**: Volatile assets require careful risk management

## Limitations

### Data Dependencies
- **API Reliability**: Dependent on CoinGecko API availability
- **Data Accuracy**: Relies on exchange-reported price data
- **Timing Delays**: 24h change may not reflect current conditions

### Market Assumptions
- **Liquidity**: Assumes sufficient liquidity for trading
- **Execution**: Doesn't account for slippage on large orders
- **Persistence**: High volatility may not continue

### Selection Bias
- **Historical Focus**: Based on past 24h performance
- **Survivorship**: Only includes currently listed cryptocurrencies
- **Size Bias**: Favors larger market cap assets

The volatile crypto discovery system provides the foundation for profitable trading in high-spread environments by systematically identifying assets whose price movements can overcome trading costs and generate significant returns.
