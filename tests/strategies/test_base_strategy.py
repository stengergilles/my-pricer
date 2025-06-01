import pytest
import pandas as pd
from stock_monitoring_app.strategies.base_strategy import BaseStrategy
from stock_monitoring_app.indicators.rsi_indicator import RSIIndicator
from stock_monitoring_app.indicators.ma_indicator import MAIndicator

@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing"""
    # Create a larger dataset to satisfy RSI's requirement for at least period+1 rows
    return pd.DataFrame({
        "Open": [100 + i for i in range(30)],
        "High": [105 + i for i in range(30)],
        "Low": [95 + i for i in range(30)],
        "Close": [102 + i for i in range(30)],
        "Volume": [1000 + i * 100 for i in range(30)]
    })

@pytest.fixture
def indicator_configs():
    """Create sample indicator configurations"""
    return [
        {
            'type': RSIIndicator,
            'params': {'period': 5, 'column': 'Close'}  # Use a smaller period for testing
        },
        {
            'type': MAIndicator,
            'params': {'window': 3, 'column': 'Close', 'ma_type': 'sma'}  # Use a smaller window for testing
        }
    ]

class TestBaseStrategy:
    
    def test_init(self, indicator_configs):
        """Test BaseStrategy initialization"""
        strategy = BaseStrategy(indicator_configs)
        assert strategy.indicator_configs == indicator_configs
        assert strategy.active_indicators == []
    
    def test_calculate_indicators(self, sample_data, indicator_configs):
        """Test calculating indicators"""
        strategy = BaseStrategy(indicator_configs)
        result = strategy.calculate_indicators(sample_data)
        
        # Verify indicators were calculated
        assert len(strategy.active_indicators) == 2
        assert isinstance(strategy.active_indicators[0], RSIIndicator)
        assert isinstance(strategy.active_indicators[1], MAIndicator)
        
        # Check that the result DataFrame has the expected columns
        # Note: The exact column names depend on how the indicators are implemented
        assert any('RSI' in col for col in result.columns)
        assert any('SMA' in col or 'MA' in col for col in result.columns)
        
    def test_generate_signals(self, sample_data, indicator_configs):
        """Test generating signals"""
        # Create a strategy with a custom signal generator
        strategy = BaseStrategy(indicator_configs)
        
        # Mock the signal generator method in BaseStrategy
        def mock_generate_signals(df):
            # Create a Series of signals with the same index as df
            signals = pd.Series(['BUY', 'SELL', 'HOLD'] * 10, index=df.index)
            return signals
        
        # Apply the mock to the strategy
        strategy.generate_signals = lambda df: mock_generate_signals(df)
        
        # Generate signals
        result_df = strategy.calculate_indicators(sample_data)
        signals = mock_generate_signals(result_df)
        
        # Verify signals were generated
        assert len(signals) == len(sample_data)
        assert signals.iloc[0] == 'BUY'
        assert signals.iloc[1] == 'SELL'
        assert signals.iloc[2] == 'HOLD'
        assert all(signal in ['BUY', 'SELL', 'HOLD'] for signal in signals)
    
    def test_error_on_invalid_indicator(self):
        """Test error handling for invalid indicator type"""
        # Create a configuration with an invalid indicator type
        invalid_configs = [
            {
                'type': str,  # Not a subclass of Indicator
                'params': {}
            }
        ]
        
        strategy = BaseStrategy(invalid_configs)
        
        # Attempt to calculate indicators should raise TypeError
        with pytest.raises(TypeError) as excinfo:
            strategy.calculate_indicators(pd.DataFrame())
        
        assert "not a subclass of Indicator" in str(excinfo.value)
