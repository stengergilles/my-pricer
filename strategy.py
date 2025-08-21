import pandas as pd
from functools import reduce
import operator
import logging
from indicators import calculate_sma, calculate_ema, calculate_rsi, calculate_macd, calculate_bbands, calculate_atr

def get_trade_signal(df: pd.DataFrame, strategy_config: dict, params: dict):
    """
    Determines the trade signal for the latest data point.
    """
    df_copy = df.copy()
    

    # --- 1. Calculate all possible indicators and base signals ---
    base_signals = {}
    
    # Moving Averages
    short_sma = calculate_sma(df_copy, params['short_sma_period'])
    long_sma = calculate_sma(df_copy, params['long_sma_period'])
    short_ema = calculate_ema(df_copy, params.get('short_ema_period', params['short_sma_period']))
    long_ema = calculate_ema(df_copy, params.get('long_ema_period', params['long_sma_period']))

    
    

    base_signals['sma_crossover'] = (short_sma.shift(1) < long_sma.shift(1)) & (short_sma > long_sma)
    base_signals['sma_crossunder'] = (short_sma.shift(1) > long_sma.shift(1)) & (short_sma < long_sma)
    
    ema_crossover_raw = (short_ema.shift(1) < long_ema.shift(1)) & (short_ema > long_ema)
    
    base_signals['ema_crossover'] = ema_crossover_raw
    base_signals['ema_crossunder'] = (short_ema.shift(1) > long_ema.shift(1)) & (short_ema < long_ema)

    # RSI
    rsi = calculate_rsi(df_copy)
    # Validate RSI values
    if (rsi < 0).any() or (rsi > 100).any():
        logging.warning(f"RSI values out of expected 0-100 range. Min: {rsi.min()}, Max: {rsi.max()}")

    base_signals['rsi_is_not_overbought'] = rsi < params['rsi_overbought']
    base_signals['rsi_is_not_oversold'] = rsi > params['rsi_oversold']
    base_signals['rsi_is_overbought'] = rsi > params['rsi_overbought']
    base_signals['rsi_is_oversold'] = rsi < params['rsi_oversold']

    # MACD
    macd_data = calculate_macd(df_copy, params['macd_fast_period'], params['macd_slow_period'], params['macd_signal_period'])
    # Validate MACD values (typically centered around 0, but can vary widely)
    # We'll just log if they are extremely large, which might indicate data issues
    if (macd_data['MACD'].abs() > 1000).any() or (macd_data['Signal'].abs() > 1000).any():
        logging.warning(f"MACD values are unusually large. MACD Max: {macd_data['MACD'].max()}, MACD Min: {macd_data['MACD'].min()}, Signal Max: {macd_data['Signal'].max()}, Signal Min: {macd_data['Signal'].min()}")

    base_signals['macd_is_bullish'] = macd_data['MACD'] > macd_data['Signal']
    base_signals['macd_is_bearish'] = macd_data['MACD'] < macd_data['Signal']

    # Volume
    # Removed as CoinGecko OHLC API does not provide volume data.

    # Bollinger Bands
    bbands = calculate_bbands(df_copy)
    base_signals['price_breaks_upper_band'] = df_copy['high'] > bbands['bb_hband']
    base_signals['price_breaks_lower_band'] = df_copy['low'] < bbands['bb_lband']
    base_signals['price_crosses_middle_band_from_top'] = (df_copy['close'].shift(1) > bbands['bb_mavg'].shift(1)) & (df_copy['close'] <= bbands['bb_mavg'])
    base_signals['price_crosses_middle_band_from_bottom'] = (df_copy['close'].shift(1) < bbands['bb_mavg'].shift(1)) & (df_copy['close'] >= bbands['bb_mavg'])


    # Combined OR signals for new strategy
    base_signals['all_triggers_long_or'] = (
        base_signals['sma_crossover'] |
        base_signals['ema_crossover'] |
        base_signals['price_breaks_upper_band'] |
        base_signals['price_crosses_middle_band_from_bottom']
    )
    base_signals['all_triggers_short_or'] = (
        base_signals['sma_crossunder'] |
        base_signals['ema_crossunder'] |
        base_signals['price_breaks_lower_band'] |
        base_signals['price_crosses_middle_band_from_top']
    )
    base_signals['all_verificators_long_or'] = (
        base_signals['rsi_is_not_overbought']
    )
    base_signals['all_verificators_short_or'] = (
        base_signals['rsi_is_not_oversold']
    )

    # Combined OR signals for exit strategy
    base_signals['all_exits_long_or'] = (
        base_signals['sma_crossunder'] |
        base_signals['ema_crossunder'] |
        base_signals['price_crosses_middle_band_from_top'] |
        base_signals['rsi_is_overbought']
    )
    base_signals['all_exits_short_or'] = (
        base_signals['sma_crossover'] |
        base_signals['ema_crossover'] |
        base_signals['price_crosses_middle_band_from_bottom'] |
        base_signals['rsi_is_oversold']
    )

    # --- 2. Combine base signals based on the selected strategy ---
    def combine_signals(signal_names):
        signals_to_combine = [base_signals[name] for name in signal_names if name in base_signals]
        if not signals_to_combine:
            return pd.Series(False, index=df_copy.index)
        return reduce(operator.and_, signals_to_combine)

    long_entry_final = combine_signals(strategy_config['long_entry'])
    short_entry_final = combine_signals(strategy_config['short_entry'])
    long_exit_final = combine_signals(strategy_config['long_exit'])
    short_exit_final = combine_signals(strategy_config['short_exit'])

    return long_entry_final, short_entry_final, long_exit_final, short_exit_final


class Strategy:
    def __init__(self, indicators, config):
        self.indicators = indicators
        self.config = config

    def generate_signals(self, data, params):
        return get_trade_signal(data, self.config, params)
