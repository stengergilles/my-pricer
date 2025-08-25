#!/usr/bin/env python3
"""
Comprehensive tests for the unified core architecture.
Tests all new core components and their integration.
"""

import unittest
import sys
import os
import tempfile
import shutil
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.parameter_manager import ParameterManager, ParameterRange
from core.crypto_discovery import CryptoDiscovery
from core.optimizer import BayesianOptimizer
from core.backtester_wrapper import BacktesterWrapper
from core.trading_engine import TradingEngine
from core.app_config import Config

class TestParameterManager(unittest.TestCase):
    """Test parameter management functionality."""
    
    def setUp(self):
        self.param_manager = ParameterManager()
    
    def test_get_available_strategies(self):
        """Test getting available strategies."""
        strategies = self.param_manager.get_available_strategies()
        self.assertIsInstance(strategies, list)
        self.assertIn('EMA_Only', strategies)
        self.assertIn('Strict', strategies)
    
    def test_get_strategy_parameters(self):
        """Test getting strategy parameters."""
        params = self.param_manager.get_strategy_parameters('EMA_Only')
        self.assertIsInstance(params, dict)
        self.assertIn('short_ema_period', params)
        self.assertIn('long_ema_period', params)
        
        # Test parameter range properties
        short_ema = params['short_ema_period']
        self.assertIsInstance(short_ema, ParameterRange)
        self.assertEqual(short_ema.param_type, 'int')
        self.assertGreater(short_ema.max_val, short_ema.min_val)
    
    def test_validate_parameters(self):
        """Test parameter validation."""
        # Valid parameters
        valid_params = {
            'short_ema_period': 12,
            'long_ema_period': 26,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'atr_period': 14,
            'atr_multiple': 2.0,
            'fixed_stop_loss_percentage': 0.02,
            'take_profit_multiple': 2.0,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9
        }
        errors = self.param_manager.validate_parameters(valid_params, 'EMA_Only')
        self.assertEqual(len(errors), 0)
        
        # Invalid parameters
        invalid_params = {
            'short_ema_period': 50,  # Too high
            'long_ema_period': 25,   # Less than short_ema_period
            'rsi_oversold': 80,      # Greater than rsi_overbought
            'rsi_overbought': 70
        }
        errors = self.param_manager.validate_parameters(invalid_params, 'EMA_Only')
        self.assertGreater(len(errors), 0)
    
    def test_get_default_parameters(self):
        """Test getting default parameters."""
        defaults = self.param_manager.get_default_parameters('EMA_Only')
        self.assertIsInstance(defaults, dict)
        self.assertIn('short_ema_period', defaults)
        self.assertIn('long_ema_period', defaults)
        
        # Check interdependent constraints
        self.assertLess(defaults['short_ema_period'], defaults['long_ema_period'])
        self.assertLess(defaults['rsi_oversold'], defaults['rsi_overbought'])
    
    def test_format_cli_params(self):
        """Test CLI parameter formatting."""
        params = {
            'short_ema_period': 12,
            'long_ema_period': 26,
            'rsi_oversold': 30
        }
        cli_args = self.param_manager.format_cli_params(params)
        
        self.assertIn('--short-ema-period', cli_args)
        self.assertIn('12', cli_args)
        self.assertIn('--long-ema-period', cli_args)
        self.assertIn('26', cli_args)

class TestCryptoDiscovery(unittest.TestCase):
    """Test cryptocurrency discovery functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.crypto_discovery = CryptoDiscovery(self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @patch('requests.get')
    def test_get_volatile_cryptos(self, mock_get):
        """Test volatile crypto discovery."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'bitcoin',
                'symbol': 'btc',
                'name': 'Bitcoin',
                'current_price': 50000,
                'price_change_percentage_24h': 10.5,
                'market_cap': 1000000000,
                'market_cap_rank': 1
            },
            {
                'id': 'ethereum',
                'symbol': 'eth',
                'name': 'Ethereum',
                'current_price': 3000,
                'price_change_percentage_24h': -5.2,
                'market_cap': 500000000,
                'market_cap_rank': 2
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test discovery
        cryptos = self.crypto_discovery.get_volatile_cryptos(min_volatility=5.0, limit=10)
        
        self.assertIsInstance(cryptos, list)
        self.assertEqual(len(cryptos), 2)
        
        # Check data processing
        bitcoin = cryptos[0]  # Should be first due to higher volatility
        self.assertEqual(bitcoin['id'], 'bitcoin')
        self.assertEqual(bitcoin['symbol'], 'BTC')
        self.assertIn('volatility_score', bitcoin)
        self.assertEqual(bitcoin['volatility_score'], 10.5)
    
    @patch('requests.get')
    def test_get_top_movers(self, mock_get):
        """Test top movers functionality."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'gainer',
                'symbol': 'gain',
                'name': 'Gainer',
                'price_change_percentage_24h': 15.0
            },
            {
                'id': 'loser',
                'symbol': 'lose',
                'name': 'Loser',
                'price_change_percentage_24h': -12.0
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        movers = self.crypto_discovery.get_top_movers(count=1)
        
        self.assertIn('gainers', movers)
        self.assertIn('losers', movers)
        self.assertEqual(len(movers['gainers']), 1)
        self.assertEqual(len(movers['losers']), 1)
    
    def test_cache_functionality(self):
        """Test caching functionality."""
        # Create mock cache data
        cache_data = [
            {
                'id': 'bitcoin',
                'symbol': 'BTC',
                'volatility_score': 10.0
            }
        ]
        
        cache_file = os.path.join(self.temp_dir, 'volatile_cryptos.json')
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Test cache loading
        loaded_data = self.crypto_discovery._load_cache(cache_file)
        self.assertEqual(loaded_data, cache_data)
        
        # Test cache validity
        self.assertTrue(self.crypto_discovery._is_cache_valid(cache_file, 1))

class TestBacktesterWrapper(unittest.TestCase):
    """Test backtester wrapper functionality."""
    
    def setUp(self):
        self.backtester = BacktesterWrapper()
    
    def test_get_available_strategies(self):
        """Test getting available strategies."""
        strategies = self.backtester.get_available_strategies()
        self.assertIsInstance(strategies, list)
        # Should return mock strategies when backtester not available
        self.assertGreater(len(strategies), 0)
    
    def test_validate_parameters(self):
        """Test parameter validation."""
        # Test with mock strategy
        errors = self.backtester.validate_parameters('EMA_Only', {
            'short_ema_period': 12,
            'long_ema_period': 26
        })
        self.assertIsInstance(errors, dict)
    
    def test_run_single_backtest(self):
        """Test single backtest execution."""
        result = self.backtester.run_single_backtest(
            crypto='bitcoin',
            strategy='EMA_Only',
            parameters={'short_ema_period': 12, 'long_ema_period': 26}
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('crypto', result)
        self.assertIn('strategy', result)
        self.assertIn('success', result)
        
        # Should be mock result when backtester not available
        if result.get('mock_result'):
            self.assertIn('total_profit_percentage', result)

class TestBayesianOptimizer(unittest.TestCase):
    """Test Bayesian optimization functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.optimizer = BayesianOptimizer(results_dir=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test optimizer initialization."""
        self.assertEqual(self.optimizer.results_dir, self.temp_dir)
        self.assertEqual(self.optimizer.seed, 42)
        self.assertIsNotNone(self.optimizer.param_manager)
        self.assertIsNotNone(self.optimizer.crypto_discovery)
    
    @patch('subprocess.run')
    def test_objective_function(self, mock_run):
        """Test objective function."""
        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Total Profit: 15.5%"
        mock_run.return_value = mock_result
        
        # Create mock trial with enough return values
        mock_trial = MagicMock()
        # Set up side effects for all possible parameter suggestions
        mock_trial.suggest_int.side_effect = [12, 26, 30, 70, 14, 12, 26, 9]  # More values
        mock_trial.suggest_float.side_effect = [2.0, 0.02, 2.5]
        
        # Test objective function
        result = self.optimizer._objective_function(mock_trial, 'bitcoin', 'EMA_Only')
        self.assertEqual(result, 15.5)
    
    def test_save_and_load_results(self):
        """Test results saving and loading."""
        # Create test results
        results = {
            'crypto': 'bitcoin',
            'strategy': 'EMA_Only',
            'best_value': 25.5,
            'best_params': {'short_ema_period': 12}
        }
        
        # Save results
        self.optimizer._save_optimization_results(results)
        
        # Load results
        loaded_results = self.optimizer.load_optimization_results('bitcoin', 'EMA_Only')
        self.assertIsNotNone(loaded_results)
        self.assertEqual(loaded_results['best_value'], 25.5)

class TestTradingEngine(unittest.TestCase):
    """Test unified trading engine functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        config = Config()
        config.RESULTS_DIR = self.temp_dir
        config.CACHE_DIR = self.temp_dir
        config.LOGS_DIR = self.temp_dir
        self.engine = TradingEngine(config)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test engine initialization."""
        self.assertIsNotNone(self.engine.param_manager)
        self.assertIsNotNone(self.engine.crypto_discovery)
        self.assertIsNotNone(self.engine.optimizer)
        self.assertIsNotNone(self.engine.backtester)
    
    def test_get_strategies(self):
        """Test getting strategies."""
        strategies = self.engine.get_strategies()
        self.assertIsInstance(strategies, list)
        self.assertGreater(len(strategies), 0)
        
        # Check strategy structure
        strategy = strategies[0]
        self.assertIn('name', strategy)
        self.assertIn('display_name', strategy)
        self.assertIn('description', strategy)
        self.assertIn('parameters', strategy)
        self.assertIn('defaults', strategy)
    
    def test_validate_parameters(self):
        """Test parameter validation."""
        # Valid parameters
        errors = self.engine.validate_parameters('EMA_Only', {
            'short_ema_period': 12,
            'long_ema_period': 26
        })
        self.assertIsInstance(errors, dict)
    
    def test_get_config(self):
        """Test getting system configuration."""
        config = self.engine.get_config()
        self.assertIsInstance(config, dict)
        self.assertIn('strategies', config)
        self.assertIn('version', config)
        self.assertIn('supported_timeframes', config)
    
    def test_health_check(self):
        """Test system health check."""
        health = self.engine.health_check()
        self.assertIsInstance(health, dict)
        self.assertIn('status', health)
        self.assertIn('checks', health)
        self.assertIn('timestamp', health)
        
        # Should have various health checks
        checks = health['checks']
        self.assertIn('backtester', checks)
        self.assertIn('parameter_manager', checks)

class TestIntegration(unittest.TestCase):
    """Integration tests for the unified system."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        config = Config()
        config.RESULTS_DIR = self.temp_dir
        config.CACHE_DIR = self.temp_dir
        config.LOGS_DIR = self.temp_dir
        self.engine = TradingEngine(config)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_backtest(self):
        """Test end-to-end backtest workflow."""
        # Get default parameters
        defaults = self.engine.get_default_parameters('EMA_Only')
        self.assertIsInstance(defaults, dict)
        
        # Validate parameters - use only the parameters that exist in the strategy
        strategy_params = self.engine.param_manager.get_strategy_parameters('EMA_Only')
        filtered_defaults = {k: v for k, v in defaults.items() if k in strategy_params}
        
        errors = self.engine.validate_parameters('EMA_Only', filtered_defaults)
        self.assertEqual(len(errors), 0)
        
        # Run backtest (will be mocked)
        result = self.engine.run_backtest(
            crypto_id='bitcoin',
            strategy_name='EMA_Only',
            parameters=filtered_defaults
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('crypto', result)
        self.assertIn('strategy', result)
    
    @patch('core.crypto_discovery.requests.get')
    def test_volatile_crypto_workflow(self, mock_get):
        """Test volatile crypto discovery and optimization workflow."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'volatile-coin',
                'symbol': 'vol',
                'name': 'Volatile Coin',
                'current_price': 100,
                'price_change_percentage_24h': 25.0,
                'market_cap': 1000000,
                'market_cap_rank': 50
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Get volatile cryptos
        volatile_cryptos = self.engine.get_volatile_cryptos(min_volatility=20.0)
        self.assertIsInstance(volatile_cryptos, list)
        
        if volatile_cryptos:
            crypto = volatile_cryptos[0]
            self.assertEqual(crypto['id'], 'volatile-coin')
            self.assertEqual(crypto['volatility_score'], 25.0)

def run_all_tests():
    """Run all unified core tests."""
    # Create test suite
    test_classes = [
        TestParameterManager,
        TestCryptoDiscovery,
        TestBacktesterWrapper,
        TestBayesianOptimizer,
        TestTradingEngine,
        TestIntegration
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
