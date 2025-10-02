import pandas as pd
from functools import reduce
import operator
import logging
from indicators import calculate_sma, calculate_ema, calculate_rsi, calculate_macd, calculate_bbands, calculate_atr, calculate_adx
from config import indicator_defaults # Added this import



def _get_required_indicators(strategy_config):
    """
    Determines which indicators are required based on the strategy configuration.
    """
    required_indicators = set()
    all_signals = []
    for key in ['long_entry', 'short_entry', 'long_exit', 'short_exit']:
        all_signals.extend(strategy_config.get(key, []))

    meta_signal_map = {
        "all_triggers_long_or": ["sma", "ema", "bbands"],
        "all_triggers_short_or": ["sma", "ema", "bbands"],
        "all_verificators_long_or": ["rsi"],
        "all_verificators_short_or": ["rsi"],
        "all_exits_long_or": ["sma", "ema", "bbands", "rsi"],
        "all_exits_short_or": ["sma", "ema", "bbands", "rsi"],
    }

    for signal_name in all_signals:
        if signal_name in meta_signal_map:
            for indicator in meta_signal_map[signal_name]:
                required_indicators.add(indicator)
        elif 'sma' in signal_name:
            required_indicators.add('sma')
        elif 'ema' in signal_name:
            required_indicators.add('ema')
        elif 'rsi' in signal_name:
            required_indicators.add('rsi')
        elif 'macd' in signal_name:
            required_indicators.add('macd')
        elif 'band' in signal_name: # For Bollinger Bands
            required_indicators.add('bbands')
        elif 'adx' in signal_name: # For ADX
            required_indicators.add('adx')
        # Add other indicators as needed
    return required_indicators

def get_trade_signal(df: pd.DataFrame, strategy_config: dict, params: dict):
    """
    Determines the trade signal for the latest data point.
    """
    df_copy = df.copy()
    base_signals = {}
    required_indicators = _get_required_indicators(strategy_config)

    # --- 1. Conditionally calculate indicators and base signals ---

    # Moving Averages (SMA)
    if 'sma' in required_indicators:
        short_sma_period = params.get('short_sma_period', indicator_defaults['short_sma_period'])
        long_sma_period = params.get('long_sma_period', indicator_defaults['long_sma_period'])
        short_sma = calculate_sma(df_copy, short_sma_period)
        long_sma = calculate_sma(df_copy, long_sma_period)
        base_signals['sma_crossover'] = (short_sma.shift(1) < long_sma.shift(1)) & (short_sma > long_sma)
        base_signals['sma_crossunder'] = (short_sma.shift(1) > long_sma.shift(1)) & (short_sma < long_sma)

    # Moving Averages (EMA)
    if 'ema' in required_indicators:
        short_ema_period = params.get('short_ema_period', indicator_defaults['short_ema'])
        long_ema_period = params.get('long_ema_period', indicator_defaults['long_ema'])
        short_ema = calculate_ema(df_copy, short_ema_period)
        long_ema = calculate_ema(df_copy, long_ema_period)
        base_signals['ema_crossover'] = (short_ema.shift(1) < long_ema.shift(1)) & (short_ema > long_ema)
        base_signals['ema_crossunder'] = (short_ema.shift(1) > long_ema.shift(1)) & (short_ema < long_ema)

    # RSI
    if 'rsi' in required_indicators:
        rsi = calculate_rsi(df_copy, params.get('rsi_period', indicator_defaults['rsi_period']))
        if (rsi < 0).any() or (rsi > 100).any():
            logging.warning(f"RSI values out of expected 0-100 range. Min: {rsi.min()}, Max: {rsi.max()}")
        base_signals['rsi_is_not_overbought'] = rsi < params.get('rsi_overbought', indicator_defaults['rsi_overbought'])
        base_signals['rsi_is_not_oversold'] = rsi > params.get('rsi_oversold', indicator_defaults['rsi_oversold'])
        base_signals['rsi_is_overbought'] = rsi > params.get('rsi_overbought', indicator_defaults['rsi_overbought'])
        base_signals['rsi_is_oversold'] = rsi < params.get('rsi_oversold', indicator_defaults['rsi_oversold'])

    # MACD
    if 'macd' in required_indicators:
        macd_fast_period = params.get('macd_fast_period', indicator_defaults['macd_fast_period'])
        macd_slow_period = params.get('macd_slow_period', indicator_defaults['macd_slow_period'])
        macd_signal_period = params.get('macd_signal_period', indicator_defaults['macd_signal_period'])
        macd_data = calculate_macd(df_copy, macd_fast_period, macd_slow_period, macd_signal_period)
        if (macd_data['MACD'].abs() > 1000).any() or (macd_data['Signal'].abs() > 1000).any():
            logging.warning(f"MACD values are unusually large. MACD Max: {macd_data['MACD'].max()}, MACD Min: {macd_data['MACD'].min()}, Signal Max: {macd_data['Signal'].max()}, Signal Min: {macd_data['Signal'].min()}")
        base_signals['macd_is_bullish'] = macd_data['MACD'] > macd_data['Signal']
        base_signals['macd_is_bearish'] = macd_data['MACD'] < macd_data['Signal']

    # Bollinger Bands
    if 'bbands' in required_indicators:
        bbands = calculate_bbands(df_copy, params.get('bb_period', indicator_defaults['bb_period']), params.get('bb_std_dev', indicator_defaults['bb_std_dev']))
        base_signals['price_breaks_upper_band'] = df_copy['high'] > bbands['bb_hband']
        base_signals['price_breaks_lower_band'] = df_copy['low'] < bbands['bb_lband']
        base_signals['price_crosses_middle_band_from_top'] = (df_copy['close'].shift(1) > bbands['bb_mavg'].shift(1)) & (df_copy['close'] <= bbands['bb_mavg'])
        base_signals['price_crosses_middle_band_from_bottom'] = (df_copy['close'].shift(1) < bbands['bb_mavg'].shift(1)) & (df_copy['close'] >= bbands['bb_mavg'])
    
    # ADX
    if 'adx' in required_indicators:
        adx_period = params.get('adx_period', indicator_defaults.get('adx_period', 14))
        adx_threshold = params.get('adx_threshold', indicator_defaults.get('adx_threshold', 20))
        adx_data = calculate_adx(df_copy, window=adx_period)
        base_signals['adx_uptrend_confirmed'] = (adx_data['pdi'].shift(1) < adx_data['ndi'].shift(1)) & (adx_data['pdi'] > adx_data['ndi']) & (adx_data['adx'] > adx_threshold)
        base_signals['adx_downtrend_confirmed'] = (adx_data['ndi'].shift(1) < adx_data['pdi'].shift(1)) & (adx_data['ndi'] > adx_data['pdi']) & (adx_data['adx'] > adx_threshold)

    # Combined OR signals for new strategy (these are hardcoded and might need review based on actual strategy definitions)
    # For now, I'll keep them as is, assuming they are used by 'Combined_Trigger_Verifier'
    # and will only be evaluated if the relevant base signals are present.
    if 'sma' in required_indicators or 'ema' in required_indicators or 'bbands' in required_indicators:
        base_signals['all_triggers_long_or'] = (
            base_signals.get('sma_crossover', pd.Series(False, index=df_copy.index)) |
            base_signals.get('ema_crossover', pd.Series(False, index=df_copy.index)) |
            base_signals.get('price_breaks_upper_band', pd.Series(False, index=df_copy.index)) |
            base_signals.get('price_crosses_middle_band_from_bottom', pd.Series(False, index=df_copy.index))
        )
        base_signals['all_triggers_short_or'] = (
            base_signals.get('sma_crossunder', pd.Series(False, index=df_copy.index)) |
            base_signals.get('ema_crossunder', pd.Series(False, index=df_copy.index)) |
            base_signals.get('price_breaks_lower_band', pd.Series(False, index=df_copy.index)) |
            base_signals.get('price_crosses_middle_band_from_top', pd.Series(False, index=df_copy.index))
        )
    if 'rsi' in required_indicators:
        base_signals['all_verificators_long_or'] = (
            base_signals.get('rsi_is_not_overbought', pd.Series(False, index=df_copy.index))
        )
        base_signals['all_verificators_short_or'] = (
            base_signals.get('rsi_is_not_oversold', pd.Series(False, index=df_copy.index))
        )

    if 'sma' in required_indicators or 'ema' in required_indicators or 'bbands' in required_indicators or 'rsi' in required_indicators:
        base_signals['all_exits_long_or'] = (
            base_signals.get('sma_crossunder', pd.Series(False, index=df_copy.index)) |
            base_signals.get('ema_crossunder', pd.Series(False, index=df_copy.index)) |
            base_signals.get('price_crosses_middle_band_from_top', pd.Series(False, index=df_copy.index)) |
            base_signals.get('rsi_is_overbought', pd.Series(False, index=df_copy.index))
        )
        base_signals['all_exits_short_or'] = (
            base_signals.get('sma_crossover', pd.Series(False, index=df_copy.index)) |
            base_signals.get('ema_crossover', pd.Series(False, index=df_copy.index)) |
            base_signals.get('price_crosses_middle_band_from_bottom', pd.Series(False, index=df_copy.index)) |
            base_signals.get('rsi_is_oversold', pd.Series(False, index=df_copy.index))
        )

    # --- 2. Combine base signals based on the selected strategy ---
    def combine_signals(signal_names):
        signals_to_combine = []
        for name in signal_names:
            if name in base_signals:
                signals_to_combine.append(base_signals[name])
            elif name.startswith('all_'): # Handle combined signals that might not be directly in base_signals if their components are missing
                # This is a fallback for combined signals if their components are not calculated
                # due to required_indicators. It assumes these combined signals are only used
                # by the 'Combined_Trigger_Verifier' strategy.
                if name == 'all_triggers_long_or' and 'Combined_Trigger_Verifier' in strategy_config.values():
                    signals_to_combine.append(base_signals.get('all_triggers_long_or', pd.Series(False, index=df_copy.index)))
                elif name == 'all_triggers_short_or' and 'Combined_Trigger_Verifier' in strategy_config.values():
                    signals_to_combine.append(base_signals.get('all_triggers_short_or', pd.Series(False, index=df_copy.index)))
                elif name == 'all_verificators_long_or' and 'Combined_Trigger_Verifier' in strategy_config.values():
                    signals_to_combine.append(base_signals.get('all_verificators_long_or', pd.Series(False, index=df_copy.index)))
                elif name == 'all_verificators_short_or' and 'Combined_Trigger_Verifier' in strategy_config.values():
                    signals_to_combine.append(base_signals.get('all_verificators_short_or', pd.Series(False, index=df_copy.index)))
                elif name == 'all_exits_long_or' and 'Combined_Trigger_Verifier' in strategy_config.values():
                    signals_to_combine.append(base_signals.get('all_exits_long_or', pd.Series(False, index=df_copy.index)))
                elif name == 'all_exits_short_or' and 'Combined_Trigger_Verifier' in strategy_config.values():
                    signals_to_combine.append(base_signals.get('all_exits_short_or', pd.Series(False, index=df_copy.index)))
                else:
                    logging.warning(f"Signal '{name}' not found in base_signals and not handled as a combined signal for Combined_Trigger_Verifier.")
            else:
                logging.warning(f"Signal '{name}' not found in base_signals. This might indicate a misconfiguration in strategy_config or missing indicator calculation.")

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
        self.params = {}
        self.backtest_trend = None # Add backtest_trend attribute

    def set_params(self, params):
        self.params = params

    def generate_signals(self, data, params, override_config=None):
        config_to_use = override_config if override_config is not None else self.config
        return get_trade_signal(data, config_to_use, params)
