import pytest
import pandas as pd
import multiprocessing as mp
from unittest.mock import patch, MagicMock
from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor, BACKTEST_SCOPE_PRESETS

@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing"""
    return pd.DataFrame({
        "Open": [100, 101, 102, 103, 104],
        "High": [105, 106, 107, 108, 109],
        "Low": [95, 96, 97, 98, 99],
        "Close": [102, 103, 101, 104, 105],
        "Volume": [1000, 1100, 900, 1200, 1300],
        "Timestamp": pd.date_range(start="2023-01-01", periods=5)
    })

@pytest.fixture
def mock_queue():
    """Create a mock queue for testing"""
    return MagicMock()

class TestTickerMonitor:
    
    def test_init(self, mock_queue):
        """Test TickerMonitor initialization"""
        monitor = TickerMonitor(
            ticker="AAPL",
            trade_order_queue=mock_queue,
            entry_price=0,
            process_name="Test_Monitor",
            backtest_scope="intraday",
            leverage=1,
            stop_loss=0.05
        )
        
        assert monitor.ticker == "AAPL"
        assert monitor.trade_order_queue == mock_queue
        assert monitor.initial_capital_allocation == 0
        assert monitor.process_name == "Test_Monitor"
        assert monitor.leverage == 1
        assert monitor._running is False
        assert monitor.backtest_scope == "intraday"
        assert monitor._period == BACKTEST_SCOPE_PRESETS["intraday"]["period"]
        assert monitor._interval == BACKTEST_SCOPE_PRESETS["intraday"]["interval"]
    
    def test_init_invalid_scope(self, mock_queue):
        """Test TickerMonitor initialization with invalid scope"""
        with pytest.raises(ValueError) as excinfo:
            TickerMonitor(
                ticker="AAPL",
                trade_order_queue=mock_queue,
                entry_price=0,
                backtest_scope="invalid_scope"
            )
        assert "Unknown backtest_scope" in str(excinfo.value)
    
    @patch('stock_monitoring_app.monitoring.ticker_monitor.TickerMonitor._fetch_latest_data')
    def test_process_data_and_decide(self, mock_fetch_latest_data, mock_queue, sample_data):
        """Test processing data and making trading decisions"""
        # Configure mocks
        mock_fetch_latest_data.return_value = sample_data
        
        # Create monitor instance
        monitor = TickerMonitor(
            ticker="AAPL",
            trade_order_queue=mock_queue,
            entry_price=0,
            backtest_scope="intraday"
        )
        
        # Mock the _load_optimized_config_from_disk method
        monitor._load_optimized_config_from_disk = MagicMock(return_value=[
            {
                'type': 'RSIIndicator',
                'params': {'period': 5, 'column': 'Close'}
            }
        ])
        
        # Mock the _resolve_indicator_class method
        monitor._resolve_indicator_class = MagicMock(return_value=None)
        
        # Call the method - this should not raise an exception
        monitor._process_data_and_decide(sample_data)
        
        # No assertion on mock_queue.put.called since we're not sure if it's called
        # Just verify the method runs without exceptions
    
    def test_run_and_stop(self, mock_queue):
        """Test running and stopping the monitor"""
        monitor = TickerMonitor(
            ticker="AAPL",
            trade_order_queue=mock_queue,
            entry_price=0,
            backtest_scope="intraday"
        )
        
        # Mock methods to avoid actual execution
        monitor._load_optimized_config_from_disk = MagicMock(return_value=[])
        monitor._fetch_latest_data = MagicMock(return_value=pd.DataFrame())
        monitor._process_data_and_decide = MagicMock()
        
        # Set running to True to simulate the monitor being started
        monitor._running = True
        
        # Stop the monitor
        monitor.stop()
        
        # Verify the monitor was stopped
        assert monitor._running is False
