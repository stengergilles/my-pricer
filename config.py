# config.py

strategy_configs = {
    "Debug_Single_Long_Entry": {
        "long_entry": ["ema_crossover"],
        "short_entry": [],
        "long_exit": [],
        "short_exit": [],
    },
    "Debug_EMA_Only": {
        "long_entry": ["ema_crossover"],
        "short_entry": ["ema_crossunder"],
        "long_exit": [],
        "short_exit": [],
    },
    "EMA_Only": {
        "long_entry": ["ema_crossover"],
        "short_entry": ["ema_crossunder"],
        "long_exit": ["ema_crossunder"],
        "short_exit": ["ema_crossover"],
    },
    "Strict": {
        "long_entry": ["adx_uptrend_confirmed", "sma_crossover", "macd_is_bullish", "rsi_is_not_overbought"],
        "short_entry": ["adx_downtrend_confirmed", "sma_crossunder", "macd_is_bearish", "rsi_is_not_oversold"],
        "long_exit": ["sma_crossunder"],
        "short_exit": ["sma_crossover"],
    },
    "BB_Breakout": {
        "long_entry": ["price_breaks_upper_band"],
        "short_entry": ["price_breaks_lower_band"],
        "long_exit": ["price_crosses_middle_band_from_top"],
        "short_exit": ["price_crosses_middle_band_from_bottom"],
    },
    "BB_RSI": {
        "long_entry": ["price_breaks_upper_band", "rsi_is_not_overbought"],
        "short_entry": ["price_breaks_lower_band", "rsi_is_not_oversold"],
        "long_exit": ["price_crosses_middle_band_from_top"],
        "short_exit": ["price_crosses_middle_band_from_bottom"],
    },
    "Combined_Trigger_Verifier": {
        "long_entry": ["all_triggers_long_or", "all_verificators_long_or"],
        "short_entry": ["all_triggers_short_or", "all_verificators_short_or"],
        "long_exit": ["all_exits_long_or"],
        "short_exit": ["all_exits_short_or"],
    }
}

ATR_PERIOD = 14
ATR_MULTIPLE = 2.0

DEFAULT_TIMEFRAME = "1"
DEFAULT_INTERVAL = "30m"
DEFAULT_SPREAD_PERCENTAGE = 0.01  # 1% - from your platform
DEFAULT_SLIPPAGE_PERCENTAGE = 0.0005  # 0.05% - realistic slippage
DATA_FETCH_DELAY_SECONDS = 10 # Delay between crypto data fetches to avoid rate limits

indicator_defaults = {
    "short_sma_period": 10,
    "long_sma_period": 51,
    "short_ema": 10,
    "long_ema": 30,
    "volume_sma": 20,
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "macd_fast_period": 12,
    "macd_slow_period": 26,
    "macd_signal_period": 9,
    "bb_period": 20,
    "bb_std_dev": 2,
    "atr_period": 14,
    "atr_multiple": 2.0,
    "adx_period": 14,
    "adx_threshold": 20,
    "atr_stop_loss_multiple": 3.0,
    "fixed_stop_loss_percentage": 0.01,
    "trailing_stop_loss_percentage": 0.02,
    "take_profit_multiple": 1.5,
}

backtest_configs = {
    "1d/30m": {"duration": "1", "freq": "30m"},
}

param_sets = {   'default_sets': {   'huge': {   'atr_multiple_range': (1.0, 3.0, 0.5),
                                    'atr_period_range': (10, 20, 5),
                                    'atr_stop_loss_multiple_range': (3.0, 4.0, 0.5),
                                    'fixed_stop_loss_percentage_range': (0.03, 0.07, 0.01),
                                    'trailing_stop_loss_percentage_range': (0.01, 0.05, 0.01),
                                    'long_sma_range': (80, 300, 20),
                                    'macd_fast_period_range': (5, 50, 5),
                                    'macd_signal_period_range': (5, 40, 5),
                                    'macd_slow_period_range': (50, 100, 10),
                                    'rsi_overbought_range': (40, 99, 5),
                                    'rsi_oversold_range': (1, 60, 5),
                                    'short_sma_range': (5, 100, 10),
                                    'take_profit_multiple_range': (2.0, 4.0, 0.5)},
                        'large': {   'atr_multiple_range': (1.0, 3.0, 0.5),
                                     'atr_period_range': (10, 20, 5),
                                     'atr_stop_loss_multiple_range': (3.0, 4.0, 0.5),
                                     'fixed_stop_loss_percentage_range': (0.03, 0.07, 0.01),
                                     'trailing_stop_loss_percentage_range': (0.01, 0.05, 0.01),
                                     'long_sma_range': (60, 200, 20),
                                     'macd_fast_period_range': (5, 30, 5),
                                     'macd_signal_period_range': (5, 25, 5),
                                     'macd_slow_period_range': (30, 60, 5),
                                     'rsi_overbought_range': (50, 95, 5),
                                     'rsi_oversold_range': (5, 50, 5),
                                     'short_sma_range': (5, 70, 10),
                                     'take_profit_multiple_range': (2.0, 4.0, 0.5)},
                        'small': {   'atr_multiple_range': (1.0, 3.0, 0.5),
                                     'atr_period_range': (10, 20, 5),
                                     'atr_stop_loss_multiple_range': (3.0, 4.0, 0.5),
                                     'fixed_stop_loss_percentage_range': (0.03, 0.07, 0.01),
                                     'trailing_stop_loss_percentage_range': (0.01, 0.05, 0.01),
                                     'long_sma_range': (35, 70, 5),
                                     'macd_fast_period_range': (5, 15, 5),
                                     'macd_signal_period_range': (5, 10, 1),
                                     'macd_slow_period_range': (20, 30, 5),
                                     'rsi_overbought_range': (60, 80, 5),
                                     'rsi_oversold_range': (20, 40, 5),
                                     'short_sma_range': (5, 30, 5),
                                     'take_profit_multiple_range': (2.0, 4.0, 0.5)},
                        'tiny': {   'atr_multiple_range': (1.0, 2.0, 0.5),
                                    'atr_period_range': (10, 20, 5),
                                    'atr_stop_loss_multiple_range': (3.0, 4.0, 0.5),
                                    'fixed_stop_loss_percentage_range': (0.03, 0.07, 0.01),
                                    'trailing_stop_loss_percentage_range': (0.01, 0.03, 0.01),
                                    'long_sma_range': (20, 40, 10),
                                    'macd_fast_period_range': (5, 15, 5),
                                    'macd_signal_period_range': (5, 10, 1),
                                    'macd_slow_period_range': (20, 30, 5),
                                    'rsi_overbought_range': (65, 75, 5),
                                    'rsi_oversold_range': (25, 35, 5),
                                    'short_sma_range': (5, 15, 5),
                                    'take_profit_multiple_range': (2.0, 4.0, 0.5)}},
    'ethereum': {   'default': {   'atr_multiple_range': (1.0, 2.0, 0.5),
                                   'atr_period_range': (10, 20, 5),
                                   'atr_stop_loss_multiple_range': (3.0, 3.0, 0.5),
                                   'fixed_stop_loss_percentage_range': (0.01, 0.03, 0.01),
                                   'trailing_stop_loss_percentage_range': (0.01, 0.03, 0.01),
                                   'long_sma_range': (20, 40, 10),
                                   'macd_fast_period_range': (5, 15, 5),
                                   'macd_signal_period_range': (5, 10, 1),
                                   'macd_slow_period_range': (20, 30, 5),
                                   'rsi_overbought_range': (65, 75, 5),
                                   'rsi_oversold_range': (25, 35, 5),
                                   'short_sma_range': (5, 15, 5),
                                   'take_profit_multiple_range': (1.0, 2.0, 0.5)}}}
