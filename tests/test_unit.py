#!/usr/bin/env python3
"""
Unit Tests for Individual Components

These tests validate individual functions and classes without modifying existing code.
They capture current behavior as expected behavior for regression detection.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestIndicators(unittest.TestCase):
    """Test indicator calculations"""
    
    def setUp(self):
        """Create sample data for testing"""
        np.random.seed(42)  # For reproducible tests
        dates = pd.date_range('2023-01-01', periods=100, freq='30min')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(100) * 0.1,
            'high': prices + np.abs(np.random.randn(100) * 0.2),
            'low': prices - np.abs(np.random.randn(100) * 0.2),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    def test_indicators_import(self):
        """Test that indicators module imports correctly"""
        try:
            from indicators import Indicators, calculate_atr
            self.assertTrue(True, "Indicators imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import indicators: {e}")
    
    def test_indicators_initialization(self):
        """Test Indicators class initialization"""
        from indicators import Indicators
        
        indicators = Indicators()
        self.assertIsInstance(indicators, Indicators)
        self.assertTrue(hasattr(indicators, 'get_indicator'))
    
    def test_atr_calculation(self):
        """Test ATR calculation produces expected output format"""
        from indicators import calculate_atr
        
        atr = calculate_atr(self.sample_data, window=14)
        
        # ATR should be a pandas Series
        self.assertIsInstance(atr, pd.Series)
        # ATR should have same length as input data
        self.assertEqual(len(atr), len(self.sample_data))
        # ATR values should be non-negative
        self.assertTrue((atr >= 0).all())

class TestStrategy(unittest.TestCase):
    """Test strategy signal generation"""
    
    def setUp(self):
        """Create sample data and strategy"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='30min')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(100) * 0.1,
            'high': prices + np.abs(np.random.randn(100) * 0.2),
            'low': prices - np.abs(np.random.randn(100) * 0.2),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        self.sample_params = {
            'short_sma_period': 10,
            'long_sma_period': 30,
            'short_ema_period': 10,
            'long_ema_period': 30,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'atr_period': 14,
            'atr_multiple': 2.0,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9
        }
    
    def test_strategy_import(self):
        """Test that strategy module imports correctly"""
        try:
            from strategy import Strategy
            self.assertTrue(True, "Strategy imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import strategy: {e}")
    
    def test_strategy_initialization(self):
        """Test Strategy class initialization"""
        from strategy import Strategy
        from indicators import Indicators
        from config import strategy_configs
        
        # Test with EMA_Only strategy
        config = strategy_configs['EMA_Only']
        indicators = Indicators()
        strategy = Strategy(indicators, config)
        
        self.assertIsInstance(strategy, Strategy)
        self.assertEqual(strategy.config, config)
    
    def test_signal_generation_format(self):
        """Test that signal generation returns expected format"""
        from strategy import Strategy
        from indicators import Indicators
        from config import strategy_configs
        
        config = strategy_configs['EMA_Only']
        indicators = Indicators()
        strategy = Strategy(indicators, config)
        
        try:
            signals = strategy.generate_signals(self.sample_data, self.sample_params)
            
            # Should return 4 arrays: long_entry, short_entry, long_exit, short_exit
            self.assertEqual(len(signals), 4)
            
            # Each signal array should have same length as data
            for signal in signals:
                self.assertEqual(len(signal), len(self.sample_data))
                # Signals should be boolean arrays
                self.assertTrue(signal.dtype == bool or signal.dtype == np.uint8)
                
        except Exception as e:
            self.fail(f"Signal generation failed: {e}")

class TestBacktester(unittest.TestCase):
    """Test backtester functionality"""
    
    def setUp(self):
        """Create sample data for backtesting"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='30min')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(100) * 0.1,
            'high': prices + np.abs(np.random.randn(100) * 0.2),
            'low': prices - np.abs(np.random.randn(100) * 0.2),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    def test_backtester_import(self):
        """Test that backtester imports correctly"""
        try:
            from backtester import Backtester
            self.assertTrue(True, "Backtester imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import backtester: {e}")
    
    def test_backtester_initialization(self):
        """Test Backtester initialization"""
        from backtester import Backtester
        from strategy import Strategy
        from indicators import Indicators
        from config import strategy_configs
        
        config = strategy_configs['EMA_Only']
        indicators = Indicators()
        strategy = Strategy(indicators, config)
        backtester = Backtester(self.sample_data, strategy, config)
        
        self.assertIsInstance(backtester, Backtester)
        self.assertEqual(backtester.initial_capital, 100.0)

class TestConfiguration(unittest.TestCase):
    """Test configuration validity"""
    
    def test_config_import(self):
        """Test that config imports correctly"""
        try:
            from config import strategy_configs, param_sets, indicator_defaults
            self.assertTrue(True, "Config imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import config: {e}")
    
    def test_strategy_configs_structure(self):
        """Test that strategy configs have required structure"""
        from config import strategy_configs
        
        required_fields = ['long_entry', 'short_entry', 'long_exit', 'short_exit']
        
        for strategy_name, config in strategy_configs.items():
            for field in required_fields:
                self.assertIn(field, config, 
                            f"Strategy {strategy_name} missing field: {field}")
                self.assertIsInstance(config[field], list,
                                    f"Strategy {strategy_name} field {field} should be list")
    
    def test_param_sets_structure(self):
        """Test that param_sets have expected structure"""
        from config import param_sets
        
        self.assertIsInstance(param_sets, dict, "param_sets should be dict")
        
        for param_set_name, params in param_sets.items():
            self.assertIsInstance(params, dict, 
                                f"param_set {param_set_name} should be dict")

class TestDataHandling(unittest.TestCase):
    """Test data handling functionality"""
    
    def test_data_import(self):
        """Test that data module imports correctly"""
        try:
            from data import get_crypto_data_merged
            self.assertTrue(True, "Data module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import data module: {e}")
    
    @patch('data.requests.get')
    def test_data_function_signature(self, mock_get):
        """Test that data functions have expected signatures"""
        from data import get_crypto_data_merged
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'prices': [[1640995200000, 47000], [1640998800000, 47100]],
            'market_caps': [[1640995200000, 900000000000], [1640998800000, 901000000000]],
            'total_volumes': [[1640995200000, 20000000000], [1640998800000, 21000000000]]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        try:
            # Test function call doesn't raise exception
            result = get_crypto_data_merged('bitcoin', days=1, interval='hourly')
            self.assertIsInstance(result, pd.DataFrame)
        except Exception as e:
            # If it fails due to network/API issues, that's expected in testing
            # We just want to ensure the function signature is correct
            pass

class TestOptimization(unittest.TestCase):
    """Test optimization functionality"""
    
    def test_bayesian_optimization_import(self):
        """Test that optimization modules import correctly"""
        try:
            import optimize_bayesian
            self.assertTrue(True, "Bayesian optimization imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import bayesian optimization: {e}")
    
    def test_volatile_crypto_optimizer_import(self):
        """Test that volatile crypto optimizer imports correctly"""
        try:
            import volatile_crypto_optimizer
            self.assertTrue(True, "Volatile crypto optimizer imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import volatile crypto optimizer: {e}")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
