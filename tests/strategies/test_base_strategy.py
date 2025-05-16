import pytest
import pandas as pd
from stock_monitoring_app.strategies import BaseStrategy
from stock_monitoring_app.indicators import (
    Indicator, # For type checking and dummy class
    RSIIndicator,
    MACDIndicator,
    BreakoutIndicator # Example of an indicator with boolean signals
)
from stock_monitoring_app.strategies.base_strategy import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD

# Uses sample_ohlcv_data fixture from conftest.py

class MockIndicator(Indicator):
    """A simple mock indicator for testing purposes."""
    def __init__(self, df: pd.DataFrame, signal_col_name: str = "Mock_Signal", signal_orientation: str = "buy", signal_value: bool = True, signal_at_index: int = -1):
        super().__init__(df.copy()) # Ensure base class validation
        self.signal_col_name = signal_col_name
        self.signal_orientation = signal_orientation
        self.signal_value = signal_value
        self.signal_at_index = signal_at_index
        self.signal_orientations[self.signal_col_name] = self.signal_orientation

    def calculate(self) -> pd.DataFrame:
        self.df[self.signal_col_name] = False # Default to False
        if self.signal_at_index >= 0 and self.signal_at_index < len(self.df):
            self.df.loc[self.df.index[self.signal_at_index], self.signal_col_name] = self.signal_value
        elif self.signal_at_index == -1: # Apply to all for simplicity in some tests
             self.df[self.signal_col_name] = self.signal_value
        return self.df

class NonIndicator:
    """A class that does not inherit from Indicator, for testing type checks."""
    def __init__(self, df:pd.DataFrame):
        self.df = df
    def calculate(self):
        return self.df


@pytest.fixture
def sample_indicator_configs():
    """Provides sample indicator configurations for strategy testing."""
    return [
        {
            'type': RSIIndicator,
            'params': {'period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70, 'column': 'Close'}
        },
        {
            'type': MACDIndicator,
            'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'column': 'Close'}        }
    ]

def test_strategy_initialization(sample_indicator_configs):
    """Tests if the strategy initializes correctly."""
    strategy = BaseStrategy(indicator_configs=sample_indicator_configs)    
    assert strategy.indicator_configs == sample_indicator_configs
    assert len(strategy.active_indicators) == 0

def test_calculate_indicators(sample_ohlcv_data, sample_indicator_configs):
    """Tests the calculation of indicators."""
    strategy = BaseStrategy(indicator_configs=sample_indicator_configs)
    df_with_indicators = strategy.calculate_indicators(sample_ohlcv_data.copy())

    assert len(strategy.active_indicators) == 2
    assert isinstance(strategy.active_indicators[0], RSIIndicator)
    assert isinstance(strategy.active_indicators[1], MACDIndicator)

    # Check if indicator columns are added (names depend on indicator implementation)
    assert f'RSI_{sample_indicator_configs[0]["params"]["period"]}' in df_with_indicators.columns
    assert f'MACD_{sample_indicator_configs[1]["params"]["fast_period"]}_{sample_indicator_configs[1]["params"]["slow_period"]}_{sample_indicator_configs[1]["params"]["signal_period"]}' in df_with_indicators.columns    
    assert f'MACD_Cross_Bullish_{sample_indicator_configs[1]["params"]["fast_period"]}_{sample_indicator_configs[1]["params"]["slow_period"]}_{sample_indicator_configs[1]["params"]["signal_period"]}' in df_with_indicators.columns

def test_calculate_indicators_no_configs(sample_ohlcv_data):
    """Tests indicator calculation with no configurations."""
    strategy = BaseStrategy(indicator_configs=[])
    df_with_indicators = strategy.calculate_indicators(sample_ohlcv_data.copy())
    assert len(strategy.active_indicators) == 0
    assert 'Strategy_Signal' not in df_with_indicators.columns # Signal generation is separate
    assert len(df_with_indicators.columns) == len(sample_ohlcv_data.columns) # No new columns

def test_calculate_indicators_invalid_type(sample_ohlcv_data):
    """Tests that a TypeError is raised for non-Indicator types."""
    invalid_config = [{'type': NonIndicator, 'params': {}}]
    strategy = BaseStrategy(indicator_configs=invalid_config)
    with pytest.raises(TypeError, match="Configured type <class '.+.NonIndicator'> is not a subclass of Indicator."):
        strategy.calculate_indicators(sample_ohlcv_data.copy())

def test_generate_signals_buy_condition(sample_ohlcv_data):
    """Tests BUY signal generation."""
    # Configure a mock indicator that always gives a buy signal
    buy_config = [{
        'type': MockIndicator,
        'params': {'signal_col_name': 'Mock_Buy_Signal', 'signal_orientation': 'buy', 'signal_value': True, 'signal_at_index': 0}
    }]
    strategy = BaseStrategy(indicator_configs=buy_config)
    df_with_indicators = strategy.calculate_indicators(sample_ohlcv_data.copy())
    df_with_signals = strategy.generate_signals(df_with_indicators)

    assert 'Strategy_Signal' in df_with_signals.columns
    assert df_with_signals['Strategy_Signal'].iloc[0] == SIGNAL_BUY
    if len(sample_ohlcv_data) > 1:
        assert df_with_signals['Strategy_Signal'].iloc[1] == SIGNAL_HOLD # Only index 0 should be BUY

def test_generate_signals_sell_condition(sample_ohlcv_data):
    """Tests SELL signal generation."""
    sell_config = [{
        'type': MockIndicator,
        'params': {'signal_col_name': 'Mock_Sell_Signal', 'signal_orientation': 'sell', 'signal_value': True, 'signal_at_index': 1}
    }]
    strategy = BaseStrategy(indicator_configs=sell_config)
    df_with_indicators = strategy.calculate_indicators(sample_ohlcv_data.copy())    
    df_with_signals = strategy.generate_signals(df_with_indicators)

    assert 'Strategy_Signal' in df_with_signals.columns
    assert df_with_signals['Strategy_Signal'].iloc[1] == SIGNAL_SELL
    assert df_with_signals['Strategy_Signal'].iloc[0] == SIGNAL_HOLD

def test_generate_signals_hold_condition_no_signals(sample_ohlcv_data):
    """Tests HOLD signal when no indicator signals are true."""
    hold_config = [{
        'type': MockIndicator,
        'params': {'signal_col_name': 'Mock_Neutral_Signal', 'signal_orientation': 'buy', 'signal_value': False, 'signal_at_index': -1} # Always False
    }]
    strategy = BaseStrategy(indicator_configs=hold_config)    
    df_with_indicators = strategy.calculate_indicators(sample_ohlcv_data.copy())
    df_with_signals = strategy.generate_signals(df_with_indicators)

    assert 'Strategy_Signal' in df_with_signals.columns
    assert (df_with_signals['Strategy_Signal'] == SIGNAL_HOLD).all()

def test_generate_signals_hold_condition_conflicting_signals(sample_ohlcv_data):
    """Tests HOLD signal when buy and sell signals conflict."""
    conflict_config = [
        {            'type': MockIndicator,
            'params': {'signal_col_name': 'Mock_Buy_Signal_Conflict', 'signal_orientation': 'buy', 'signal_value': True, 'signal_at_index': 0}
        },
        {
            'type': MockIndicator,
            'params': {'signal_col_name': 'Mock_Sell_Signal_Conflict', 'signal_orientation': 'sell', 'signal_value': True, 'signal_at_index': 0}
        }
    ]
    strategy = BaseStrategy(indicator_configs=conflict_config)
    df_with_indicators = strategy.calculate_indicators(sample_ohlcv_data.copy())
    df_with_signals = strategy.generate_signals(df_with_indicators)
    
    assert 'Strategy_Signal' in df_with_signals.columns
    assert df_with_signals['Strategy_Signal'].iloc[0] == SIGNAL_HOLD

def test_generate_signals_no_active_indicators(sample_ohlcv_data, capsys):
    """Tests signal generation when no indicators were successfully activated/calculated."""
    strategy = BaseStrategy(indicator_configs=[]) # No configs
    # Manually ensure active_indicators is empty, though calculate_indicators would do this
    strategy.active_indicators.clear() 
    
    df_with_signals = strategy.generate_signals(sample_ohlcv_data.copy())
    captured = capsys.readouterr()

    assert "Warning: No active indicators to generate signals from." in captured.out
    assert 'Strategy_Signal' in df_with_signals.columns
    assert (df_with_signals['Strategy_Signal'] == SIGNAL_HOLD).all()


def test_run_strategy_end_to_end(sample_ohlcv_data, sample_indicator_configs):
    """Tests the full run method of the strategy."""
    strategy = BaseStrategy(indicator_configs=sample_indicator_configs)
    results_df = strategy.run(sample_ohlcv_data.copy())

    assert 'Strategy_Signal' in results_df.columns
    # Check if indicator columns are present (as in test_calculate_indicators)
    assert f'RSI_{sample_indicator_configs[0]["params"]["period"]}' in results_df.columns
    # More specific assertions on signals would depend on actual data and indicator logic
    # For now, just check the column exists and has expected values
    assert results_df['Strategy_Signal'].isin([SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD]).all()

def test_run_strategy_empty_df(capsys):
    """Tests the run method with an empty DataFrame."""
    strategy = BaseStrategy(indicator_configs=[])    
    empty_df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    results_df = strategy.run(empty_df)
    
    captured = capsys.readouterr()
    assert "Warning: Input DataFrame for strategy is empty." in captured.out
    assert 'Strategy_Signal' in results_df.columns
    assert results_df.empty

def test_strategy_with_breakout_indicator(sample_ohlcv_data):
    """Tests strategy with an indicator producing boolean signals (BreakoutIndicator)."""
    # Make one row have a clear bullish breakout
    modified_data = sample_ohlcv_data.copy()
    # For index 10, recent high (window=5) for Highs[5:10] is 112 (High at index 9)
    # Set Close[10] to 113 to trigger bullish breakout
    modified_data.loc[modified_data.index[10], 'Close'] = 113 

    breakout_config = [{
        'type': BreakoutIndicator,
        'params': {'window': 5} # Uses default High, Low, Close columns
    }]
    strategy = BaseStrategy(indicator_configs=breakout_config)
    results_df = strategy.run(modified_data)

    assert results_df['Strategy_Signal'].iloc[10] == SIGNAL_BUY
    # Check other rows are likely HOLD (unless other breakouts occur in sample data)
    # For example, check index 5, which shouldn't have this specific breakout
    assert results_df['Strategy_Signal'].iloc[5] == SIGNAL_HOLD


# Example of testing more complex interactions if needed:
# def test_strategy_rsi_and_macd_combination(sample_ohlcv_data):
#     # 1. Create specific data that would trigger RSI buy and MACD buy
#     # This requires more intricate data setup.
#     # For instance, make last row RSI oversold and MACD bullish crossover
#     custom_data = sample_ohlcv_data.copy()
#     # ... (modify custom_data for specific indicator signals) ...

#     configs = [
#         {'type': RSIIndicator, 'params': {'period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70}},
#         {'type': MACDIndicator, 'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}}
#     ]
#     strategy = BaseStrategy(indicator_configs=configs)
#     results_df = strategy.run(custom_data)
#     assert results_df['Strategy_Signal'].iloc[-1] == SIGNAL_BUY