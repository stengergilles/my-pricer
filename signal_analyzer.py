import pandas as pd
import logging
from config import DEFAULT_TIMEFRAME, indicator_defaults, strategy_configs
from data import get_crypto_data_merged
from indicators import calculate_sma, calculate_ema, calculate_rsi, calculate_macd, calculate_bbands, calculate_atr
from functools import reduce
import operator

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler()
                    ])

def analyze_signals(crypto_id, strategy_name, params):
    logging.info(f"Fetching data for {crypto_id}...")
    df = get_crypto_data_merged(crypto_id, DEFAULT_TIMEFRAME)
    if df is None:
        logging.error(f"Could not fetch data for {crypto_id}. Exiting.")
        return

    logging.info(f"Analyzing signals for strategy: {strategy_name}")
    df_copy = df.copy()

    base_signals = {}

    # Moving Averages
    short_sma = calculate_sma(df_copy, params.get('short_sma_period', indicator_defaults['short_sma']))
    long_sma = calculate_sma(df_copy, params.get('long_sma_period', indicator_defaults['long_sma']))
    short_ema = calculate_ema(df_copy, params.get('short_ema_period', indicator_defaults['short_ema']))
    long_ema = calculate_ema(df_copy, params.get('long_ema_period', indicator_defaults['long_ema']))

    base_signals['sma_crossover'] = (short_sma.shift(1) < long_sma.shift(1)) & (short_sma > long_sma)
    base_signals['sma_crossunder'] = (short_sma.shift(1) > long_sma.shift(1)) & (short_sma < long_sma)
    
    ema_crossover_raw = (short_ema.shift(1) < long_ema.shift(1)) & (short_ema > long_ema)
    base_signals['ema_crossover'] = ema_crossover_raw
    base_signals['ema_crossunder'] = (short_ema.shift(1) > long_ema.shift(1)) & (short_ema < long_ema)

    # RSI
    rsi = calculate_rsi(df_copy, params.get('rsi_period', indicator_defaults['rsi_period']))
    base_signals['rsi_is_not_overbought'] = rsi < params.get('rsi_overbought', indicator_defaults['rsi_overbought'])
    base_signals['rsi_is_not_oversold'] = rsi > params.get('rsi_oversold', indicator_defaults['rsi_oversold'])
    base_signals['rsi_is_overbought'] = rsi > params.get('rsi_overbought', indicator_defaults['rsi_overbought'])
    base_signals['rsi_is_oversold'] = rsi < params.get('rsi_oversold', indicator_defaults['rsi_oversold'])

    # MACD
    macd_data = calculate_macd(df_copy, 
                               params.get('macd_slow_period', indicator_defaults['macd_slow_period']),
                               params.get('macd_fast_period', indicator_defaults['macd_fast_period']),
                               params.get('macd_signal_period', indicator_defaults['macd_signal_period']))
    base_signals['macd_is_bullish'] = macd_data['MACD'] > macd_data['Signal']
    base_signals['macd_is_bearish'] = macd_data['MACD'] < macd_data['Signal']

    # Volume
    # Removed as CoinGecko OHLC API does not provide volume data.

    # Bollinger Bands
    bbands = calculate_bbands(df_copy, 
                              params.get('bb_period', indicator_defaults['bb_period']),
                              params.get('bb_std_dev', indicator_defaults['bb_std_dev']))
    base_signals['price_breaks_upper_band'] = df_copy['high'] > bbands['bb_hband']
    base_signals['price_breaks_lower_band'] = df_copy['low'] < bbands['bb_lband']
    base_signals['price_crosses_middle_band_from_top'] = (df_copy['close'].shift(1) > bbands['bb_mavg'].shift(1)) & (df_copy['close'] <= bbands['bb_mavg'])
    base_signals['price_crosses_middle_band_from_bottom'] = (df_copy['close'].shift(1) < bbands['bb_mavg'].shift(1)) & (df_copy['close'] >= bbands['bb_mavg'])

    # Combined OR signals (from strategy.py)
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

    # Combine base signals based on the selected strategy
    def combine_signals(signal_names):
        signals_to_combine = [base_signals[name] for name in signal_names if name in base_signals]
        if not signals_to_combine:
            return pd.Series(False, index=df_copy.index)
        return reduce(operator.and_, signals_to_combine)

    strategy_config = strategy_configs.get(strategy_name, {})
    
    long_entry_final = combine_signals(strategy_config.get('long_entry', []))
    short_entry_final = combine_signals(strategy_config.get('short_entry', []))
    long_exit_final = combine_signals(strategy_config.get('long_exit', []))
    short_exit_final = combine_signals(strategy_config.get('short_exit', []))

    logging.info("\n--- Base Signal Frequencies (True counts) ---")
    for signal_name, series in base_signals.items():
        if isinstance(series, pd.Series):
            logging.info(f"{signal_name}: {series.sum()} (out of {len(series)} data points)")
        else:
            logging.info(f"{signal_name}: Not a Series (e.g., MACD DataFrame)")

    logging.info("\n--- Strategy Signal Frequencies (True counts) ---")
    logging.info(f"Long Entry: {long_entry_final.sum()} (out of {len(long_entry_final)} data points)")
    logging.info(f"Short Entry: {short_entry_final.sum()} (out of {len(short_entry_final)} data points)")
    logging.info(f"Long Exit: {long_exit_final.sum()} (out of {len(long_exit_final)} data points)")
    logging.info(f"Short Exit: {short_exit_final.sum()} (out of {len(short_exit_final)} data points)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze signal frequencies for a given strategy.')
    parser.add_argument('--crypto', required=True, help='Cryptocurrency ID (e.g., ethereum)')
    parser.add_argument('--strategy', required=True, help='The trading strategy to analyze (e.g., EMA_Only, SMA_Volume)')
    
    # Add arguments for all possible parameters, with defaults from indicator_defaults
    parser.add_argument('--short-sma-period', type=int, default=indicator_defaults['short_sma'])
    parser.add_argument('--long-sma-period', type=int, default=indicator_defaults['long_sma'])
    parser.add_argument('--short-ema-period', type=int, default=indicator_defaults['short_ema'])
    parser.add_argument('--long-ema-period', type=int, default=indicator_defaults['long_ema'])
    parser.add_argument('--rsi-period', type=int, default=indicator_defaults['rsi_period'])
    parser.add_argument('--rsi-oversold', type=int, default=indicator_defaults['rsi_oversold'])
    parser.add_argument('--rsi-overbought', type=int, default=indicator_defaults['rsi_overbought'])
    parser.add_argument('--macd-fast-period', type=int, default=indicator_defaults['macd_fast_period'])
    parser.add_argument('--macd-slow-period', type=int, default=indicator_defaults['macd_slow_period'])
    parser.add_argument('--macd-signal-period', type=int, default=indicator_defaults['macd_signal_period'])
    parser.add_argument('--volume-sma', type=int, default=indicator_defaults['volume_sma'])
    parser.add_argument('--bb-period', type=int, default=indicator_defaults['bb_period'])
    parser.add_argument('--bb-std-dev', type=int, default=indicator_defaults['bb_std_dev'])
    parser.add_argument('--atr-period', type=int, default=indicator_defaults['atr_period'])
    parser.add_argument('--atr-multiple', type=float, default=indicator_defaults['atr_multiple'])
    parser.add_argument('--fixed-stop_loss_percentage', type=float, default=indicator_defaults['fixed_stop_loss_percentage'])
    parser.add_argument('--take-profit_multiple', type=float, default=indicator_defaults['take_profit_multiple'])

    args = parser.parse_args()

    # Convert args to a dictionary for params
    params = {k: v for k, v in vars(args).items() if k not in ['crypto', 'strategy']}

    analyze_signals(args.crypto, args.strategy, params)
