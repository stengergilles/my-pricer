#!/usr/bin/env python3

import pandas as pd
import numpy as np
from data import get_crypto_data_merged
from config import strategy_configs, DEFAULT_TIMEFRAME, indicator_defaults
from indicators import Indicators
from strategy import Strategy

def debug_signals():
    # Get data
    data = get_crypto_data_merged('bitcoin', DEFAULT_TIMEFRAME)
    print(f"Data shape: {data.shape}")
    
    # Simple parameters
    params = {
        'short_sma_period': 10,
        'long_sma_period': 30,
        'short_ema_period': 10,
        'long_ema_period': 30,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'atr_period': 14,
        'atr_multiple': 2.0,
        'fixed_stop_loss_percentage': 0.02,
        'take_profit_multiple': 2.0,
        'macd_fast_period': 12,
        'macd_slow_period': 26,
        'macd_signal_period': 9,
        'spread_percentage': 0.01,
        'slippage_percentage': 0.0005,
    }
    
    # Fill missing params with defaults
    for p in indicator_defaults:
        if p not in params:
            params[p] = indicator_defaults[p]
    
    # Create strategy
    indicators = Indicators()
    strategy_config = strategy_configs['EMA_Only']
    strategy = Strategy(indicators, strategy_config)
    
    print(f"Strategy config: {strategy_config}")
    
    # Generate signals
    long_entry, short_entry, long_exit, short_exit = strategy.generate_signals(data, params)
    
    # Print signal statistics
    print(f"\nSignal Statistics:")
    print(f"Long entry signals: {long_entry.sum()}")
    print(f"Short entry signals: {short_entry.sum()}")
    print(f"Long exit signals: {long_exit.sum()}")
    print(f"Short exit signals: {short_exit.sum()}")
    
    # Show where signals occur
    signal_dates = data.index[long_entry | short_entry | long_exit | short_exit]
    print(f"\nSignal dates (first 10):")
    for i, date in enumerate(signal_dates[:10]):
        idx = data.index.get_loc(date)
        print(f"{date}: Long_entry={long_entry.iloc[idx]}, Short_entry={short_entry.iloc[idx]}, "
              f"Long_exit={long_exit.iloc[idx]}, Short_exit={short_exit.iloc[idx]}, "
              f"Price={data['close'].iloc[idx]:.2f}")
    
    # Check for NaN values in signals
    print(f"\nNaN check:")
    print(f"Long entry NaNs: {long_entry.isna().sum()}")
    print(f"Short entry NaNs: {short_entry.isna().sum()}")
    print(f"Long exit NaNs: {long_exit.isna().sum()}")
    print(f"Short exit NaNs: {short_exit.isna().sum()}")
    
    # Show price statistics
    print(f"\nPrice statistics:")
    print(f"Price range: {data['close'].min():.2f} - {data['close'].max():.2f}")
    print(f"Price change: {((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100:.2f}%")
    
    # Calculate and show EMAs for debugging
    from indicators import calculate_ema
    short_ema = calculate_ema(data, params['short_ema_period'])
    long_ema = calculate_ema(data, params['long_ema_period'])
    
    print(f"\nEMA crossover analysis:")
    crossovers = (short_ema.shift(1) < long_ema.shift(1)) & (short_ema > long_ema)
    crossunders = (short_ema.shift(1) > long_ema.shift(1)) & (short_ema < long_ema)
    
    print(f"EMA crossovers: {crossovers.sum()}")
    print(f"EMA crossunders: {crossunders.sum()}")
    
    # Show first few crossover points
    if crossovers.sum() > 0:
        crossover_dates = data.index[crossovers]
        print(f"First crossover dates:")
        for date in crossover_dates[:3]:
            idx = data.index.get_loc(date)
            print(f"  {date}: Short EMA={short_ema.iloc[idx]:.2f}, Long EMA={long_ema.iloc[idx]:.2f}, Price={data['close'].iloc[idx]:.2f}")

if __name__ == "__main__":
    debug_signals()
