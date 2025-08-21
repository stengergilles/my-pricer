#!/usr/bin/env python3
"""
Performance Tests for Regression Detection

These tests capture current performance characteristics as baselines
to detect performance regressions after code changes.
"""

import os
import sys
import unittest
import time
import numpy as np
import pandas as pd
from pathlib import Path

# Try to import psutil, skip performance tests if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPerformanceBaselines(unittest.TestCase):
    """Test performance baselines for regression detection"""
    
    def setUp(self):
        """Create consistent test data"""
        if not PSUTIL_AVAILABLE:
            self.skipTest("psutil not available - install with: pip install psutil")
            
        np.random.seed(42)  # Reproducible performance tests
        dates = pd.date_range('2023-01-01', periods=1000, freq='30min')
        prices = 100 + np.cumsum(np.random.randn(1000) * 0.5)
        
        self.large_dataset = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(1000) * 0.1,
            'high': prices + np.abs(np.random.randn(1000) * 0.2),
            'low': prices - np.abs(np.random.randn(1000) * 0.2),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 1000)
        })
        
        self.test_params = {
            'short_ema_period': 10,
            'long_ema_period': 30,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'atr_period': 14,
            'atr_multiple': 2.0
        }
    
    def test_indicators_performance(self):
        """Test indicators calculation performance"""
        from indicators import Indicators
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Run indicators calculation
        indicators = Indicators(self.large_dataset)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Performance baselines (adjust based on your system)
        # These are generous limits to detect major regressions
        self.assertLess(execution_time, 5.0, 
                       f"Indicators calculation took {execution_time:.2f}s, expected < 5.0s")
        self.assertLess(memory_used, 100, 
                       f"Indicators used {memory_used:.2f}MB, expected < 100MB")
        
        print(f"Indicators performance: {execution_time:.3f}s, {memory_used:.2f}MB")
    
    def test_strategy_signal_generation_performance(self):
        """Test strategy signal generation performance"""
        from strategy import Strategy
        from config import strategy_configs
        
        config = strategy_configs['EMA_Only']
        strategy = Strategy(config)
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Generate signals
        signals = strategy.generate_signals(self.large_dataset, self.test_params)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Performance baselines
        self.assertLess(execution_time, 3.0,
                       f"Signal generation took {execution_time:.2f}s, expected < 3.0s")
        self.assertLess(memory_used, 50,
                       f"Signal generation used {memory_used:.2f}MB, expected < 50MB")
        
        print(f"Signal generation performance: {execution_time:.3f}s, {memory_used:.2f}MB")
    
    def test_backtester_performance(self):
        """Test backtester performance (if Cython is available)"""
        try:
            from backtester import Backtester, CYTHON_AVAILABLE
            from strategy import Strategy
            from config import strategy_configs
            
            if not CYTHON_AVAILABLE:
                self.skipTest("Cython backtester not available")
            
            config = strategy_configs['EMA_Only']
            strategy = Strategy(config)
            backtester = Backtester(self.large_dataset, strategy, config)
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Run backtest
            result = backtester.run_backtest(self.test_params)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_used = end_memory - start_memory
            
            # Performance baselines
            self.assertLess(execution_time, 2.0,
                           f"Backtest took {execution_time:.2f}s, expected < 2.0s")
            self.assertLess(memory_used, 30,
                           f"Backtest used {memory_used:.2f}MB, expected < 30MB")
            
            print(f"Backtest performance: {execution_time:.3f}s, {memory_used:.2f}MB")
            
        except ImportError:
            self.skipTest("Backtester not available")
    
    def test_multiple_strategy_performance(self):
        """Test performance with multiple strategies"""
        from strategy import Strategy
        from config import strategy_configs
        
        strategies_to_test = ['EMA_Only', 'Strict', 'BB_Breakout']
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        for strategy_name in strategies_to_test:
            config = strategy_configs[strategy_name]
            strategy = Strategy(config)
            signals = strategy.generate_signals(self.large_dataset, self.test_params)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Performance baseline for multiple strategies
        self.assertLess(execution_time, 10.0,
                       f"Multiple strategies took {execution_time:.2f}s, expected < 10.0s")
        self.assertLess(memory_used, 150,
                       f"Multiple strategies used {memory_used:.2f}MB, expected < 150MB")
        
        print(f"Multiple strategies performance: {execution_time:.3f}s, {memory_used:.2f}MB")

class TestScalabilityBaselines(unittest.TestCase):
    """Test scalability characteristics"""
    
    def setUp(self):
        if not PSUTIL_AVAILABLE:
            self.skipTest("psutil not available - install with: pip install psutil")
    
    def test_data_size_scaling(self):
        """Test performance scaling with different data sizes"""
        from indicators import Indicators
        
        data_sizes = [100, 500, 1000]
        times = []
        
        for size in data_sizes:
            # Create data of specific size
            np.random.seed(42)
            dates = pd.date_range('2023-01-01', periods=size, freq='30min')
            prices = 100 + np.cumsum(np.random.randn(size) * 0.5)
            
            data = pd.DataFrame({
                'timestamp': dates,
                'open': prices + np.random.randn(size) * 0.1,
                'high': prices + np.abs(np.random.randn(size) * 0.2),
                'low': prices - np.abs(np.random.randn(size) * 0.2),
                'close': prices,
                'volume': np.random.randint(1000, 10000, size)
            })
            
            start_time = time.time()
            indicators = Indicators(data)
            end_time = time.time()
            
            times.append(end_time - start_time)
        
        # Check that performance scales reasonably (not exponentially)
        # Time should roughly scale linearly with data size
        time_ratio_500_100 = times[1] / times[0] if times[0] > 0 else 1
        time_ratio_1000_500 = times[2] / times[1] if times[1] > 0 else 1
        
        # Should not be exponential scaling (ratio should be reasonable)
        self.assertLess(time_ratio_500_100, 10, 
                       f"Performance degradation too high: 500/100 ratio = {time_ratio_500_100:.2f}")
        self.assertLess(time_ratio_1000_500, 10,
                       f"Performance degradation too high: 1000/500 ratio = {time_ratio_1000_500:.2f}")
        
        print(f"Scaling times: {times}")
        print(f"Scaling ratios: 500/100={time_ratio_500_100:.2f}, 1000/500={time_ratio_1000_500:.2f}")

class TestMemoryBaselines(unittest.TestCase):
    """Test memory usage baselines"""
    
    def setUp(self):
        if not PSUTIL_AVAILABLE:
            self.skipTest("psutil not available - install with: pip install psutil")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations"""
        from indicators import Indicators
        
        # Create test data
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=500, freq='30min')
        prices = 100 + np.cumsum(np.random.randn(500) * 0.5)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(500) * 0.1,
            'high': prices + np.abs(np.random.randn(500) * 0.2),
            'low': prices - np.abs(np.random.randn(500) * 0.2),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 500)
        })
        
        # Measure memory before
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Perform repeated operations
        for i in range(10):
            indicators = Indicators(data)
            del indicators  # Explicit cleanup
        
        # Measure memory after
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Should not grow significantly (allow some growth for normal operations)
        self.assertLess(memory_growth, 50,
                       f"Memory grew by {memory_growth:.2f}MB, possible memory leak")
        
        print(f"Memory growth after 10 iterations: {memory_growth:.2f}MB")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
