import pandas as pd
import ta

class Indicators:
    def get_indicator(self, name, df, params):
        if name == 'sma':
            window = params.get('short_sma_period', params.get('long_sma_period', 20))
            return calculate_sma(df, window)
        elif name == 'ema':
            window = params.get('short_ema_period', params.get('long_ema_period', 20))
            return calculate_ema(df, window)
        elif name == 'rsi':
            return calculate_rsi(df)
        elif name == 'macd':
            return calculate_macd(df, params['macd_fast_period'], params['macd_slow_period'], params['macd_signal_period'])
        elif name == 'bbands':
            return calculate_bbands(df)
        elif name == 'atr':
            return calculate_atr(df)
        else:
            return None

def calculate_sma(df, window):
    """Calculates the Simple Moving Average (SMA) manually."""
    if window >= len(df):
        return pd.Series([float('nan')] * len(df), index=df.index)
    
    sma = df['close'].rolling(window=window).mean()
    return sma

def calculate_ema(df, window):
    """Calculates the Exponential Moving Average (EMA) manually."""
    ema = df['close'].ewm(span=window, adjust=False).mean()
    return ema


def calculate_rsi(df, window=14):
    """Calculates the Relative Strength Index (RSI)"""
    return ta.momentum.rsi(df['close'], window=window)

def calculate_macd(df, window_slow=26, window_fast=12, window_sign=9):
    """Calculates the Moving Average Convergence Divergence (MACD)"""
    macd_line = ta.trend.macd(df['close'], window_slow=window_slow, window_fast=window_fast)
    macd_signal = ta.trend.macd_signal(df['close'], window_slow=window_slow, window_fast=window_fast, window_sign=window_sign)
    
    macd_df = pd.DataFrame({'MACD': macd_line, 'Signal': macd_signal})
    return macd_df

def calculate_bbands(df, window=20, window_dev=2):
    """Calculates the Bollinger Bands"""
    indicator_bb = ta.volatility.BollingerBands(close=df['close'], window=window, window_dev=window_dev)
    bb_df = pd.DataFrame({
        'bb_mavg': indicator_bb.bollinger_mavg(),
        'bb_hband': indicator_bb.bollinger_hband(),
        'bb_lband': indicator_bb.bollinger_lband()
    })
    return bb_df

def calculate_atr(df, window=14):
    """Calculates the Average True Range (ATR)"""
    if window >= len(df):
        window = len(df) - 1
    return ta.volatility.average_true_range(high=df['high'], low=df['low'], close=df['close'], window=window)