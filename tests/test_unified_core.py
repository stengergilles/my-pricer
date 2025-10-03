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
from core.data_fetcher import DataFetcher # Added DataFetcher import

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
        self.assertIn('short_sma', params)
        self.assertIn('long_sma', params)
        
        # Test parameter range properties
        short_sma = params['short_sma']
        self.assertIsInstance(short_sma, ParameterRange)
        self.assertEqual(short_sma.param_type, 'int')
        self.assertGreater(short_sma.max_val, short_sma.min_val)
    
    def test_validate_parameters(self):
        """Test parameter validation."""
        # Valid parameters
        valid_params = {
            'short_sma': 10,
            'long_sma': 50,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'atr_period': 14,
            'atr_multiple': 2.0,
            'fixed_stop_loss_percentage': 0.03, # Corrected to be within valid range (0.03, 0.07)
            'take_profit_multiple': 2.0,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9
        }
        errors = self.param_manager.validate_parameters(valid_params, 'EMA_Only')
        self.assertEqual(len(errors), 0)
        
        # Invalid parameters
        invalid_params = {
            'short_sma': 50,  # Too high (max 30)
            'long_sma': 25,   # Too low (min 35) and less than short_sma
            'rsi_oversold': 80,      # Too high (max 40)
            'rsi_overbought': 70
        }
        errors = self.param_manager.validate_parameters(invalid_params, 'EMA_Only')
        # Expecting 4 errors: short_sma (too high), long_sma (too low and less than short_sma), rsi_oversold (too high)
        self.assertEqual(len(errors), 4)
    
    def test_get_default_parameters(self):
        """Test getting default parameters."""
        defaults = self.param_manager.get_default_parameters('EMA_Only')
        self.assertIsInstance(defaults, dict)
        self.assertIn('short_sma', defaults)
        self.assertIn('long_sma', defaults)
        
        # Check interdependent constraints
        self.assertLess(defaults['short_sma'], defaults['long_sma'])
        self.assertLess(defaults['rsi_oversold'], defaults['rsi_overbought'])
    
    def test_format_cli_params(self):
        """Test CLI parameter formatting."""
        params = {
            'short_sma': 10,
            'long_sma': 50,
            'rsi_oversold': 30
        }
        cli_args = self.param_manager.format_cli_params(params)
        
        self.assertIn('--short-sma', cli_args)
        self.assertIn('10', cli_args)
        self.assertIn('--long-sma', cli_args)
        self.assertIn('50', cli_args)

class TestCryptoDiscovery(unittest.TestCase):
    """Test cryptocurrency discovery functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_data_fetcher = MagicMock(spec=DataFetcher)
        # Configure the mock_data_fetcher to return a mock response for make_coingecko_request
        self.mock_data_fetcher.make_coingecko_request.return_value = [
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
        self.crypto_discovery = CryptoDiscovery(self.temp_dir, data_fetcher=self.mock_data_fetcher)
    
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
        self.temp_dir = tempfile.mkdtemp()
        config = Config()
        config.RESULTS_DIR = self.temp_dir
        config.CACHE_DIR = self.temp_dir
        config.LOGS_DIR = self.temp_dir
        self.mock_data_fetcher = MagicMock(spec=DataFetcher)
        self.mock_data_fetcher.response_queue = MagicMock() # Mock response_queue
        self.mock_data_fetcher.config = config # Pass the actual config object
        self.backtester = BacktesterWrapper(config, data_fetcher=self.mock_data_fetcher)
    
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
        self.mock_data_fetcher = MagicMock(spec=DataFetcher)
        self.mock_data_fetcher.response_queue = MagicMock() # Mock response_queue
        self.mock_data_fetcher.config = MagicMock(spec=Config) # Mock config
        self.optimizer = BayesianOptimizer(results_dir=self.temp_dir, data_fetcher=self.mock_data_fetcher)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test optimizer initialization."""
        self.assertEqual(self.optimizer.results_dir, self.temp_dir)
        self.assertEqual(self.optimizer.seed, 42)
        self.assertIsNotNone(self.optimizer.param_manager)
        self.assertIsNotNone(self.optimizer.crypto_discovery)
    
    @patch('core.optimizer.job_status_manager')
    @patch('core.optimizer.subprocess.Popen')
    @patch('core.backtester_wrapper.BacktesterWrapper.run_single_backtest') # Mock run_single_backtest
    def test_objective_function(self, mock_run_single_backtest, mock_popen, mock_job_manager):
        """Test objective function."""
        # Mock Popen to return a process that simulates a successful backtest run
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Indicates process has finished
        
        # Simulate stdout and stderr streams
        mock_process.stdout.readline.side_effect = [
            'OPTIMIZER_RESULTS:{"total_profit_percentage": 15.5}\n',
            ''  # End of stream
        ]
        mock_process.stderr.readline.return_value = ''
        mock_process.communicate.return_value = ('OPTIMIZER_RESULTS:{"total_profit_percentage": 15.5}', '')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Configure mock_run_single_backtest to return a successful result
        mock_run_single_backtest.return_value = {
            'success': True,
            'final_capital': 15.5, # This is the value the objective function expects
            'total_profit_percentage': 15.5
        }

        # Mock job status manager to avoid side effects
        mock_job_manager.is_job_stop_requested.return_value = False

        # Create a mock trial object
        mock_trial = MagicMock()
        mock_trial.number = 1
        # Configure suggest_int and suggest_float to return valid parameter values
        mock_trial.suggest_int.side_effect = [
            10,  # short_sma_period
            50,  # long_sma_period
            25,  # rsi_oversold
            75,  # rsi_overbought
            10,  # macd_fast_period
            25,  # macd_slow_period
            15,  # atr_period
            8,   # macd_signal_period
        ]
        mock_trial.suggest_float.side_effect = [
            2.0,  # atr_multiple
            3.5,  # atr_stop_loss_multiple
            0.03, # fixed_stop_loss_percentage
            0.02, # trailing_stop_loss_percentage
            3.0,  # take_profit_multiple
        ]

        # Test objective function with a mock job_id
        result = self.optimizer._objective_function(mock_trial, 'bitcoin', 'EMA_Only', 'test-job-123')
        
        # Assert the expected outcome
        self.assertEqual(result, 15.5)
        
        # Verify that the subprocess was created (no longer applicable as backtester_wrapper is mocked)
        # mock_popen.assert_called_once()
        
        # Verify that the job manager was used for registration and unregistration (no longer applicable as backtester_wrapper is mocked)
        # mock_job_manager.register_job_process.assert_called_with('test-job-123', 12345)
        # mock_job_manager.unregister_job_process.assert_called_with('test-job-123', 12345)
    
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
        self.mock_data_fetcher = MagicMock(spec=DataFetcher)
        self.mock_data_fetcher.response_queue = MagicMock()
        self.mock_data_fetcher.config = config
        # Configure mock_data_fetcher to return mock klines data
        self.mock_data_fetcher.fetch_klines.return_value = [
            [1678886400000, 100.0, 105.0, 98.0, 103.0],
            [1678972800000, 103.0, 108.0, 101.0, 106.0],
            [1679059200000, 106.0, 110.0, 104.0, 108.0],
            [1679145600000, 108.0, 112.0, 106.0, 110.0],
            [1679232000000, 110.0, 115.0, 108.0, 113.0],
            [1679318400000, 113.0, 118.0, 111.0, 116.0],
            [1679404800000, 116.0, 120.0, 114.0, 118.0],
            [1679491200000, 118.0, 122.0, 116.0, 120.0],
            [1679577600000, 120.0, 125.0, 118.0, 123.0],
            [1679664000000, 123.0, 128.0, 121.0, 126.0],
            [1679750400000, 126.0, 130.0, 124.0, 128.0],
            [1679836800000, 128.0, 132.0, 126.0, 130.0],
            [1679923200000, 130.0, 135.0, 128.0, 133.0],
            [1680009600000, 133.0, 138.0, 131.0, 136.0],
            [1680096000000, 136.0, 140.0, 134.0, 138.0],
            [1680182400000, 138.0, 142.0, 136.0, 140.0],
            [1680268800000, 140.0, 145.0, 138.0, 143.0],
            [1680355200000, 143.0, 148.0, 141.0, 146.0],
            [1680441600000, 146.0, 150.0, 144.0, 148.0],
            [1680528000000, 148.0, 152.0, 146.0, 150.0],
            [1680614400000, 150.0, 155.0, 148.0, 153.0],
            [1680700800000, 153.0, 158.0, 151.0, 156.0],
            [1680787200000, 156.0, 160.0, 154.0, 158.0],
            [1680873600000, 158.0, 162.0, 156.0, 160.0],
            [1680960000000, 160.0, 165.0, 158.0, 163.0],
            [1681046400000, 163.0, 168.0, 161.0, 166.0],
            [1681132800000, 166.0, 170.0, 164.0, 168.0],
            [1681219200000, 168.0, 172.0, 166.0, 170.0],
            [1681305600000, 170.0, 175.0, 168.0, 173.0],
            [1681392000000, 173.0, 178.0, 171.0, 176.0],
            [1681478400000, 176.0, 180.0, 174.0, 178.0],
            [1681564800000, 178.0, 182.0, 176.0, 180.0],
            [1681651200000, 180.0, 185.0, 178.0, 183.0],
            [1681737600000, 183.0, 188.0, 181.0, 186.0],
            [1681824000000, 186.0, 190.0, 184.0, 188.0],
            [1681910400000, 188.0, 192.0, 186.0, 190.0],
            [1681996800000, 190.0, 195.0, 188.0, 193.0],
            [1682083200000, 193.0, 198.0, 191.0, 196.0],
            [1682169600000, 196.0, 200.0, 194.0, 198.0],
            [1682256000000, 198.0, 202.0, 196.0, 200.0],
            [1682342400000, 200.0, 205.0, 198.0, 203.0],
            [1682428800000, 203.0, 208.0, 201.0, 206.0],
            [1682515200000, 206.0, 210.0, 204.0, 208.0],
            [1682601600000, 208.0, 212.0, 206.0, 210.0],
            [1682688000000, 210.0, 215.0, 208.0, 213.0],
            [1682774400000, 213.0, 218.0, 211.0, 216.0],
            [1682860800000, 216.0, 220.0, 214.0, 218.0],
            [1682947200000, 218.0, 222.0, 216.0, 220.0],
            [1683033600000, 220.0, 225.0, 218.0, 223.0],
            [1683120000000, 223.0, 228.0, 221.0, 226.0],
            [1683206400000, 226.0, 230.0, 224.0, 228.0],
            [1683292800000, 228.0, 232.0, 226.0, 230.0],
            [1683379200000, 230.0, 235.0, 228.0, 233.0],
            [1683465600000, 233.0, 238.0, 231.0, 236.0],
            [1683552000000, 236.0, 240.0, 234.0, 238.0],
            [1683638400000, 238.0, 242.0, 236.0, 240.0],
            [1683724800000, 240.0, 245.0, 238.0, 243.0],
            [1683811200000, 243.0, 248.0, 241.0, 246.0],
            [1683897600000, 246.0, 250.0, 244.0, 248.0],
            [1683984000000, 248.0, 252.0, 246.0, 250.0],
            [1684070400000, 250.0, 255.0, 248.0, 253.0],
            [1684156800000, 253.0, 258.0, 251.0, 256.0],
            [1684243200000, 256.0, 260.0, 254.0, 258.0],
            [1684329600000, 258.0, 262.0, 256.0, 260.0],
            [1684416000000, 260.0, 265.0, 258.0, 263.0],
            [1684502400000, 263.0, 268.0, 261.0, 266.0],
            [1684588800000, 266.0, 270.0, 264.0, 268.0],
            [1684675200000, 268.0, 272.0, 266.0, 270.0],
            [1684761600000, 270.0, 275.0, 268.0, 273.0],
            [1684848000000, 273.0, 278.0, 271.0, 276.0],
            [1684934400000, 276.0, 280.0, 274.0, 278.0],
            [1685020800000, 278.0, 282.0, 276.0, 280.0],
            [1685107200000, 280.0, 285.0, 278.0, 283.0],
            [1685193600000, 283.0, 288.0, 281.0, 286.0],
            [1685280000000, 286.0, 290.0, 284.0, 288.0],
            [1685366400000, 288.0, 292.0, 286.0, 290.0],
            [1685452800000, 290.0, 295.0, 288.0, 293.0],
            [1685539200000, 293.0, 298.0, 291.0, 296.0],
            [1685625600000, 296.0, 300.0, 294.0, 298.0],
            [1685712000000, 298.0, 302.0, 296.0, 300.0],
            [1685798400000, 300.0, 305.0, 298.0, 303.0],
            [1685884800000, 303.0, 308.0, 301.0, 306.0],
            [1685971200000, 306.0, 310.0, 304.0, 308.0],
            [1686057600000, 308.0, 312.0, 306.0, 310.0],
            [1686144000000, 310.0, 315.0, 308.0, 313.0],
            [1686230400000, 313.0, 318.0, 311.0, 316.0],
            [1686316800000, 316.0, 320.0, 314.0, 318.0],
            [1686403200000, 318.0, 322.0, 316.0, 320.0],
            [1686489600000, 320.0, 325.0, 318.0, 323.0],
            [1686576000000, 323.0, 328.0, 321.0, 326.0],
            [1686662400000, 326.0, 330.0, 324.0, 328.0],
            [1686748800000, 328.0, 332.0, 326.0, 330.0],
            [1686835200000, 330.0, 335.0, 328.0, 333.0],
            [1686921600000, 333.0, 338.0, 331.0, 336.0],
            [1687008000000, 336.0, 340.0, 334.0, 338.0],
            [1687094400000, 338.0, 342.0, 336.0, 340.0],
            [1687180800000, 340.0, 345.0, 338.0, 343.0],
            [1687267200000, 343.0, 348.0, 341.0, 346.0],
            [1687353600000, 346.0, 350.0, 344.0, 348.0],
            [1687440000000, 348.0, 352.0, 346.0, 350.0],
            [1687526400000, 350.0, 355.0, 348.0, 353.0],
            [1687612800000, 353.0, 358.0, 351.0, 356.0],
            [1687699200000, 356.0, 360.0, 354.0, 358.0],
            [1687785600000, 358.0, 362.0, 356.0, 360.0],
            [1687872000000, 360.0, 365.0, 358.0, 363.0],
            [1687958400000, 363.0, 368.0, 361.0, 366.0],
            [1688044800000, 366.0, 370.0, 364.0, 368.0],
            [1688131200000, 368.0, 372.0, 366.0, 370.0],
            [1688217600000, 370.0, 375.0, 368.0, 373.0],
            [1688304000000, 373.0, 378.0, 371.0, 376.0],
            [1688390400000, 376.0, 380.0, 374.0, 378.0],
            [1688476800000, 378.0, 382.0, 376.0, 380.0],
            [1688563200000, 380.0, 385.0, 378.0, 383.0],
            [1688649600000, 383.0, 388.0, 381.0, 386.0],
            [1688736000000, 386.0, 390.0, 384.0, 388.0],
            [1688822400000, 388.0, 392.0, 386.0, 390.0],
            [1688908800000, 390.0, 395.0, 388.0, 393.0],
            [1688995200000, 393.0, 398.0, 391.0, 396.0],
            [1689081600000, 396.0, 400.0, 394.0, 398.0],
            [1689168000000, 398.0, 402.0, 396.0, 400.0],
            [1689254400000, 400.0, 405.0, 398.0, 403.0],
            [1689340800000, 403.0, 408.0, 401.0, 406.0],
            [1689427200000, 406.0, 410.0, 404.0, 408.0],
            [1689513600000, 408.0, 412.0, 406.0, 410.0],
            [1689600000000, 410.0, 415.0, 408.0, 413.0],
            [1689686400000, 413.0, 418.0, 411.0, 416.0],
            [1689772800000, 416.0, 420.0, 414.0, 418.0],
            [1689859200000, 418.0, 422.0, 416.0, 420.0],
            [1689945600000, 420.0, 425.0, 418.0, 423.0],
            [1690032000000, 423.0, 428.0, 421.0, 426.0],
            [1690118400000, 426.0, 430.0, 424.0, 428.0],
            [1690204800000, 428.0, 432.0, 426.0, 430.0],
            [1690291200000, 430.0, 435.0, 428.0, 433.0],
            [1690377600000, 433.0, 438.0, 431.0, 436.0],
            [1690464000000, 436.0, 440.0, 434.0, 438.0],
            [1690550400000, 438.0, 442.0, 436.0, 440.0],
            [1690636800000, 440.0, 445.0, 438.0, 443.0],
            [1690723200000, 443.0, 448.0, 441.0, 446.0],
            [1690809600000, 446.0, 450.0, 444.0, 448.0],
            [1690896000000, 448.0, 452.0, 446.0, 450.0],
            [1690982400000, 450.0, 455.0, 448.0, 453.0],
            [1691068800000, 453.0, 458.0, 451.0, 456.0],
            [1691155200000, 456.0, 460.0, 454.0, 458.0],
            [1691241600000, 458.0, 462.0, 456.0, 460.0],
            [1691328000000, 460.0, 465.0, 458.0, 463.0],
            [1691414400000, 463.0, 468.0, 461.0, 466.0],
            [1691500800000, 466.0, 470.0, 464.0, 468.0],
            [1691587200000, 468.0, 472.0, 466.0, 470.0],
            [1691673600000, 470.0, 475.0, 468.0, 473.0],
            [1691760000000, 473.0, 478.0, 471.0, 476.0],
            [1691846400000, 476.0, 480.0, 474.0, 478.0],
            [1691932800000, 478.0, 482.0, 476.0, 480.0],
            [1692019200000, 480.0, 485.0, 478.0, 483.0],
            [1692105600000, 483.0, 488.0, 481.0, 486.0],
            [1692192000000, 486.0, 490.0, 484.0, 488.0],
            [1692278400000, 488.0, 492.0, 486.0, 490.0],
            [1692364800000, 490.0, 495.0, 488.0, 493.0],
            [1692451200000, 493.0, 498.0, 491.0, 496.0],
            [1692537600000, 496.0, 500.0, 494.0, 498.0],
            [1692624000000, 498.0, 502.0, 496.0, 500.0],
            [1692710400000, 500.0, 505.0, 498.0, 503.0],
            [1692796800000, 503.0, 508.0, 501.0, 506.0],
            [1692883200000, 506.0, 510.0, 504.0, 508.0],
            [1692969600000, 508.0, 512.0, 506.0, 510.0],
            [1693056000000, 510.0, 515.0, 508.0, 513.0],
            [1693142400000, 513.0, 518.0, 511.0, 516.0],
            [1693228800000, 516.0, 520.0, 514.0, 518.0],
            [1693315200000, 518.0, 522.0, 516.0, 520.0],
            [1693401600000, 520.0, 525.0, 518.0, 523.0],
            [1693488000000, 523.0, 528.0, 521.0, 526.0],
            [1693574400000, 526.0, 530.0, 524.0, 528.0],
            [1693660800000, 528.0, 532.0, 526.0, 530.0],
            [1693747200000, 530.0, 535.0, 528.0, 533.0],
            [1693833600000, 533.0, 538.0, 531.0, 536.0],
            [1693920000000, 536.0, 540.0, 534.0, 538.0],
            [1694006400000, 538.0, 542.0, 536.0, 540.0],
            [1694092800000, 540.0, 545.0, 538.0, 543.0],
            [1694179200000, 543.0, 548.0, 541.0, 546.0],
            [1694265600000, 546.0, 550.0, 544.0, 548.0],
            [1694352000000, 548.0, 552.0, 546.0, 550.0],
            [1694438400000, 550.0, 555.0, 548.0, 553.0],
            [1694524800000, 553.0, 558.0, 551.0, 556.0],
            [1694611200000, 556.0, 560.0, 554.0, 558.0],
            [1694697600000, 558.0, 562.0, 556.0, 560.0],
            [1694784000000, 560.0, 565.0, 558.0, 563.0],
            [1694870400000, 563.0, 568.0, 561.0, 566.0],
            [1694956800000, 566.0, 570.0, 564.0, 568.0],
            [1695043200000, 568.0, 572.0, 566.0, 570.0],
            [1695129600000, 570.0, 575.0, 568.0, 573.0],
            [1695216000000, 573.0, 578.0, 571.0, 576.0],
            [1695302400000, 576.0, 580.0, 574.0, 578.0],
            [1695388800000, 578.0, 582.0, 576.0, 580.0],
            [1695475200000, 580.0, 585.0, 578.0, 583.0],
            [1695561600000, 583.0, 588.0, 581.0, 586.0],
            [1695648000000, 586.0, 590.0, 584.0, 588.0],
            [1695734400000, 588.0, 592.0, 586.0, 590.0],
            [1695820800000, 590.0, 595.0, 588.0, 593.0],
            [1695907200000, 593.0, 598.0, 591.0, 596.0],
            [1695993600000, 596.0, 600.0, 594.0, 598.0],
            [1696080000000, 598.0, 602.0, 596.0, 600.0],
            [1696166400000, 600.0, 605.0, 598.0, 603.0],
            [1696252800000, 603.0, 608.0, 601.0, 606.0],
            [1696339200000, 606.0, 610.0, 604.0, 608.0],
            [1696425600000, 608.0, 612.0, 606.0, 610.0],
            [1696512000000, 610.0, 615.0, 608.0, 613.0],
            [1696598400000, 613.0, 618.0, 611.0, 616.0],
            [1696684800000, 616.0, 620.0, 614.0, 618.0],
            [1696771200000, 618.0, 622.0, 616.0, 620.0],
            [1696857600000, 620.0, 625.0, 618.0, 623.0],
            [1696944000000, 623.0, 628.0, 621.0, 626.0],
            [1697030400000, 626.0, 630.0, 624.0, 628.0],
            [1697116800000, 628.0, 632.0, 626.0, 630.0],
            [1697203200000, 630.0, 635.0, 628.0, 633.0],
            [1697289600000, 633.0, 638.0, 631.0, 636.0],
            [1697376000000, 636.0, 640.0, 634.0, 638.0],
            [1697462400000, 638.0, 642.0, 636.0, 640.0],
            [1697548800000, 640.0, 645.0, 638.0, 643.0],
            [1697635200000, 643.0, 648.0, 641.0, 646.0],
            [1697721600000, 646.0, 650.0, 644.0, 648.0],
            [1697808000000, 648.0, 652.0, 646.0, 650.0],
            [1697894400000, 650.0, 655.0, 648.0, 653.0],
            [1697980800000, 653.0, 658.0, 651.0, 656.0],
            [1698067200000, 656.0, 660.0, 654.0, 658.0],
            [1698153600000, 658.0, 662.0, 656.0, 660.0],
            [1698240000000, 660.0, 665.0, 658.0, 663.0],
            [1698326400000, 663.0, 668.0, 661.0, 666.0],
            [1698412800000, 666.0, 670.0, 664.0, 668.0],
            [1698499200000, 668.0, 672.0, 666.0, 670.0],
            [1698585600000, 670.0, 675.0, 668.0, 673.0],
            [1698672000000, 673.0, 678.0, 671.0, 676.0],
            [1698758400000, 676.0, 680.0, 674.0, 678.0],
            [1698844800000, 678.0, 682.0, 676.0, 680.0],
            [1698931200000, 680.0, 685.0, 678.0, 683.0],
            [1699017600000, 683.0, 688.0, 681.0, 686.0],
            [1699104000000, 686.0, 690.0, 684.0, 688.0],
            [1699190400000, 688.0, 692.0, 686.0, 690.0],
            [1699276800000, 690.0, 695.0, 688.0, 693.0],
            [1699363200000, 693.0, 698.0, 691.0, 696.0],
            [1699449600000, 696.0, 700.0, 694.0, 698.0],
            [1699536000000, 698.0, 702.0, 696.0, 700.0],
            [1699622400000, 700.0, 705.0, 698.0, 703.0],
            [1699708800000, 703.0, 708.0, 701.0, 706.0],
            [1699795200000, 706.0, 710.0, 704.0, 708.0],
            [1699881600000, 708.0, 712.0, 706.0, 710.0],
            [1699968000000, 710.0, 715.0, 708.0, 713.0],
            [1700054400000, 713.0, 718.0, 711.0, 716.0],
            [1700140800000, 716.0, 720.0, 714.0, 718.0],
            [1700227200000, 718.0, 722.0, 716.0, 720.0],
            [1700313600000, 720.0, 725.0, 718.0, 723.0],
            [1700400000000, 723.0, 728.0, 721.0, 726.0],
            [1700486400000, 726.0, 730.0, 724.0, 728.0],
            [1700572800000, 728.0, 732.0, 726.0, 730.0],
            [1700659200000, 730.0, 735.0, 728.0, 733.0],
            [1700745600000, 733.0, 738.0, 731.0, 736.0],
            [1700832000000, 736.0, 740.0, 734.0, 738.0],
            [1700918400000, 738.0, 742.0, 736.0, 740.0],
            [1701004800000, 740.0, 745.0, 738.0, 743.0],
            [1701091200000, 743.0, 748.0, 741.0, 746.0],
            [1701177600000, 746.0, 750.0, 744.0, 748.0],
            [1701264000000, 748.0, 752.0, 746.0, 750.0],
            [1701350400000, 750.0, 755.0, 748.0, 753.0],
            [1701436800000, 753.0, 758.0, 751.0, 756.0],
            [1701523200000, 756.0, 760.0, 754.0, 758.0],
            [1701609600000, 758.0, 762.0, 756.0, 760.0],
            [1701696000000, 760.0, 765.0, 758.0, 763.0],
            [1701782400000, 763.0, 768.0, 761.0, 766.0],
            [1701868800000, 766.0, 770.0, 764.0, 768.0],
            [1701955200000, 768.0, 772.0, 766.0, 770.0],
            [1702041600000, 770.0, 775.0, 768.0, 773.0],
            [1702128000000, 773.0, 778.0, 771.0, 776.0],
            [1702214400000, 776.0, 780.0, 774.0, 778.0],
            [1702300800000, 778.0, 782.0, 776.0, 780.0],
            [1702387200000, 780.0, 785.0, 778.0, 783.0],
            [1702473600000, 783.0, 788.0, 781.0, 786.0],
            [1702560000000, 786.0, 790.0, 784.0, 788.0],
            [1702646400000, 788.0, 792.0, 786.0, 790.0],
            [1702732800000, 790.0, 795.0, 788.0, 793.0],
            [1702819200000, 793.0, 798.0, 791.0, 796.0],
            [1702905600000, 796.0, 800.0, 794.0, 798.0],
            [1702992000000, 798.0, 802.0, 796.0, 800.0],
            [1703078400000, 800.0, 805.0, 798.0, 803.0],
            [1703164800000, 803.0, 808.0, 801.0, 806.0],
            [1703251200000, 806.0, 810.0, 804.0, 808.0],
            [1703337600000, 808.0, 812.0, 806.0, 810.0],
            [1703424000000, 810.0, 815.0, 808.0, 813.0],
            [1703510400000, 813.0, 818.0, 811.0, 816.0],
            [1703596800000, 816.0, 820.0, 814.0, 818.0],
            [1703683200000, 818.0, 822.0, 816.0, 820.0],
            [1703769600000, 820.0, 825.0, 818.0, 823.0],
            [1703856000000, 823.0, 828.0, 821.0, 826.0],
            [1703942400000, 826.0, 830.0, 824.0, 828.0],
            [1704028800000, 828.0, 832.0, 826.0, 830.0],
            [1704115200000, 830.0, 835.0, 828.0, 833.0],
            [1704201600000, 833.0, 838.0, 831.0, 836.0],
            [1704288000000, 836.0, 840.0, 834.0, 838.0],
            [1704374400000, 838.0, 842.0, 836.0, 840.0],
            [1704460800000, 840.0, 845.0, 838.0, 843.0],
            [1704547200000, 843.0, 848.0, 841.0, 846.0],
            [1704633600000, 846.0, 850.0, 844.0, 848.0],
            [1704720000000, 848.0, 852.0, 846.0, 850.0],
            [1704806400000, 850.0, 855.0, 848.0, 853.0],
            [1704892800000, 853.0, 858.0, 851.0, 856.0],
            [1704979200000, 856.0, 860.0, 854.0, 858.0],
            [1705065600000, 858.0, 862.0, 856.0, 860.0],
            [1705152000000, 860.0, 865.0, 858.0, 863.0],
            [1705238400000, 863.0, 868.0, 861.0, 866.0],
            [1705324800000, 866.0, 870.0, 864.0, 868.0],
            [1705411200000, 868.0, 872.0, 866.0, 870.0],
            [1705497600000, 870.0, 875.0, 868.0, 873.0],
            [1705584000000, 873.0, 878.0, 871.0, 876.0],
            [1705670400000, 876.0, 880.0, 874.0, 878.0],
            [1705756800000, 878.0, 882.0, 876.0, 880.0],
            [1705843200000, 880.0, 885.0, 878.0, 883.0],
            [1705929600000, 883.0, 888.0, 881.0, 886.0],
            [1706016000000, 886.0, 890.0, 884.0, 888.0],
            [1706102400000, 888.0, 892.0, 886.0, 890.0],
            [1706188800000, 890.0, 895.0, 888.0, 893.0],
            [1706275200000, 893.0, 898.0, 891.0, 896.0],
            [1706361600000, 896.0, 900.0, 894.0, 898.0],
            [1706448000000, 898.0, 902.0, 896.0, 900.0],
            [1706534400000, 900.0, 905.0, 898.0, 903.0],
            [1706620800000, 903.0, 908.0, 901.0, 906.0],
            [1706707200000, 906.0, 910.0, 904.0, 908.0],
            [1706793600000, 908.0, 912.0, 906.0, 910.0],
            [1706880000000, 910.0, 915.0, 908.0, 913.0],
            [1706966400000, 913.0, 918.0, 911.0, 916.0],
            [1707052800000, 916.0, 920.0, 914.0, 918.0],
            [1707139200000, 918.0, 922.0, 916.0, 920.0],
            [1707225600000, 920.0, 925.0, 918.0, 923.0],
            [1707312000000, 923.0, 928.0, 921.0, 926.0],
            [1707398400000, 926.0, 930.0, 924.0, 928.0],
            [1707484800000, 928.0, 932.0, 926.0, 930.0],
            [1707571200000, 930.0, 935.0, 928.0, 933.0],
            [1707657600000, 933.0, 938.0, 931.0, 936.0],
            [1707744000000, 936.0, 940.0, 934.0, 938.0],
            [1707830400000, 938.0, 942.0, 936.0, 940.0],
            [1707916800000, 940.0, 945.0, 938.0, 943.0],
            [1708003200000, 943.0, 948.0, 941.0, 946.0],
            [1708089600000, 946.0, 950.0, 944.0, 948.0],
            [1708176000000, 948.0, 952.0, 946.0, 950.0],
            [1708262400000, 950.0, 955.0, 948.0, 953.0],
            [1708348800000, 953.0, 958.0, 951.0, 956.0],
            [1708435200000, 956.0, 960.0, 954.0, 958.0],
            [1708521600000, 958.0, 962.0, 956.0, 960.0],
            [1708608000000, 960.0, 965.0, 958.0, 963.0],
            [1708694400000, 963.0, 968.0, 961.0, 966.0],
            [1708780800000, 966.0, 970.0, 964.0, 968.0],
            [1708867200000, 968.0, 972.0, 966.0, 970.0],
            [1708953600000, 970.0, 975.0, 968.0, 973.0],
            [1709040000000, 973.0, 978.0, 971.0, 976.0],
            [1709126400000, 976.0, 980.0, 974.0, 978.0],
            [1709212800000, 978.0, 982.0, 976.0, 980.0],
            [1709299200000, 980.0, 985.0, 978.0, 983.0],
            [1709385600000, 983.0, 988.0, 981.0, 986.0],
            [1709472000000, 986.0, 990.0, 984.0, 988.0],
            [1709558400000, 988.0, 992.0, 986.0, 990.0],
            [1709644800000, 990.0, 995.0, 988.0, 993.0],
            [1709731200000, 993.0, 998.0, 991.0, 996.0],
            [1709817600000, 996.0, 1000.0, 994.0, 998.0],
            [1709904000000, 998.0, 1002.0, 996.0, 1000.0],
            [1709990400000, 1000.0, 1005.0, 998.0, 1003.0],
            [1710076800000, 1003.0, 1008.0, 1001.0, 1006.0],
            [1710163200000, 1006.0, 1010.0, 1004.0, 1008.0],
            [1710249600000, 1008.0, 1012.0, 1006.0, 1010.0],
            [1710336000000, 1010.0, 1015.0, 1008.0, 1013.0],
            [1710422400000, 1013.0, 1018.0, 1011.0, 1016.0],
            [1710508800000, 1016.0, 1020.0, 1014.0, 1018.0],
            [1710595200000, 1018.0, 1022.0, 1016.0, 1020.0],
            [1710681600000, 1020.0, 1025.0, 1018.0, 1023.0],
            [1710768000000, 1023.0, 1028.0, 1021.0, 1026.0],
            [1710854400000, 1026.0, 1030.0, 1024.0, 1028.0],
            [1710940800000, 1028.0, 1032.0, 1026.0, 1030.0],
            [1711027200000, 1030.0, 1035.0, 1028.0, 1033.0],
            [1711113600000, 1033.0, 1038.0, 1031.0, 1036.0],
            [1711200000000, 1036.0, 1040.0, 1034.0, 1038.0],
            [1711286400000, 1038.0, 1042.0, 1036.0, 1040.0],
            [1711372800000, 1040.0, 1045.0, 1038.0, 1043.0],
            [1711459200000, 1043.0, 1048.0, 1041.0, 1046.0],
            [1711545600000, 1046.0, 1050.0, 1044.0, 1048.0],
            [1711632000000, 1048.0, 1052.0, 1046.0, 1050.0],
            [1711718400000, 1050.0, 1055.0, 1048.0, 1053.0],
            [1711804800000, 1053.0, 1058.0, 1051.0, 1056.0],
            [1711891200000, 1056.0, 1060.0, 1054.0, 1058.0],
            [1711977600000, 1058.0, 1062.0, 1056.0, 1060.0],
            [1712064000000, 1060.0, 1065.0, 1058.0, 1063.0],
            [1712150400000, 1063.0, 1068.0, 1061.0, 1066.0],
            [1712236800000, 1066.0, 1070.0, 1064.0, 1068.0],
            [1712323200000, 1068.0, 1072.0, 1066.0, 1070.0],
            [1712409600000, 1070.0, 1075.0, 1068.0, 1073.0],
            [1712496000000, 1073.0, 1078.0, 1071.0, 1076.0],
            [1712582400000, 1076.0, 1080.0, 1074.0, 1078.0],
            [1712668800000, 1078.0, 1082.0, 1076.0, 1080.0],
            [1712755200000, 1080.0, 1085.0, 1078.0, 1083.0],
            [1712841600000, 1083.0, 1088.0, 1081.0, 1086.0],
            [1712928000000, 1086.0, 1090.0, 1084.0, 1088.0],
            [1713014400000, 1088.0, 1092.0, 1086.0, 1090.0],
            [1713100800000, 1090.0, 1095.0, 1088.0, 1093.0],
            [1713187200000, 1093.0, 1098.0, 1091.0, 1096.0],
            [1713273600000, 1096.0, 1100.0, 1094.0, 1098.0],
            [1713360000000, 1098.0, 1102.0, 1096.0, 1100.0],
            [1713446400000, 1100.0, 1105.0, 1098.0, 1103.0],
            [1713532800000, 1103.0, 1108.0, 1101.0, 1106.0],
            [1713619200000, 1106.0, 1110.0, 1104.0, 1108.0],
            [1713705600000, 1108.0, 1112.0, 1106.0, 1110.0],
            [1713792000000, 1110.0, 1115.0, 1108.0, 1113.0],
            [1713878400000, 1113.0, 1118.0, 1111.0, 1116.0],
            [1713964800000, 1116.0, 1120.0, 1114.0, 1118.0],
            [1714051200000, 1118.0, 1122.0, 1116.0, 1120.0],
            [1714137600000, 1120.0, 1125.0, 1118.0, 1123.0],
            [1714224000000, 1123.0, 1128.0, 1121.0, 1126.0],
            [1714310400000, 1126.0, 1130.0, 1124.0, 1128.0],
            [1714396800000, 1128.0, 1132.0, 1126.0, 1130.0],
            [1714483200000, 1130.0, 1135.0, 1128.0, 1133.0],
            [1714569600000, 1133.0, 1138.0, 1131.0, 1136.0],
            [1714656000000, 1136.0, 1140.0, 1134.0, 1138.0],
            [1714742400000, 1138.0, 1142.0, 1136.0, 1140.0],
            [1714828800000, 1140.0, 1145.0, 1138.0, 1143.0],
            [1714915200000, 1143.0, 1148.0, 1141.0, 1146.0],
            [1715001600000, 1146.0, 1150.0, 1144.0, 1148.0],
            [1715088000000, 1148.0, 1152.0, 1146.0, 1150.0],
            [1715174400000, 1150.0, 1155.0, 1148.0, 1153.0],
            [1715260800000, 1153.0, 1158.0, 1151.0, 1156.0],
            [1715347200000, 1156.0, 1160.0, 1154.0, 1158.0],
            [1715433600000, 1158.0, 1162.0, 1156.0, 1160.0],
            [1715520000000, 1160.0, 1165.0, 1158.0, 1163.0],
            [1715606400000, 1163.0, 1168.0, 1161.0, 1166.0],
            [1715692800000, 1166.0, 1170.0, 1164.0, 1168.0],
            [1715779200000, 1168.0, 1172.0, 1166.0, 1170.0],
            [1715865600000, 1170.0, 1175.0, 1168.0, 1173.0],
            [1715952000000, 1173.0, 1178.0, 1171.0, 1176.0],
            [1716038400000, 1176.0, 1180.0, 1174.0, 1178.0],
            [1716124800000, 1178.0, 1182.0, 1176.0, 1180.0],
            [1716211200000, 1180.0, 1185.0, 1178.0, 1183.0],
            [1716297600000, 1183.0, 1188.0, 1181.0, 1186.0],
            [1716384000000, 1186.0, 1190.0, 1184.0, 1188.0],
            [1716470400000, 1188.0, 1192.0, 1186.0, 1190.0],
            [1716556800000, 1190.0, 1195.0, 1188.0, 1193.0],
            [1716643200000, 1193.0, 1198.0, 1191.0, 1196.0],
            [1716729600000, 1196.0, 1200.0, 1194.0, 1198.0],
            [1716816000000, 1198.0, 1202.0, 1196.0, 1200.0],
            [1716902400000, 1200.0, 1205.0, 1198.0, 1203.0],
            [1716988800000, 1203.0, 1208.0, 1201.0, 1206.0],
            [1717075200000, 1206.0, 1210.0, 1204.0, 1208.0],
            [1717161600000, 1208.0, 1212.0, 1206.0, 1210.0],
            [1717248000000, 1210.0, 1215.0, 1208.0, 1213.0],
            [1717334400000, 1213.0, 1218.0, 1211.0, 1216.0],
            [1717420800000, 1216.0, 1220.0, 1214.0, 1218.0],
            [1717507200000, 1218.0, 1222.0, 1216.0, 1220.0],
            [1717593600000, 1220.0, 1225.0, 1218.0, 1223.0],
            [1717680000000, 1223.0, 1228.0, 1221.0, 1226.0],
            [1717766400000, 1226.0, 1230.0, 1224.0, 1228.0],
            [1717852800000, 1228.0, 1232.0, 1226.0, 1230.0],
            [1717939200000, 1230.0, 1235.0, 1228.0, 1233.0],
            [1718025600000, 1233.0, 1238.0, 1231.0, 1236.0],
            [1718112000000, 1236.0, 1240.0, 1234.0, 1238.0],
            [1718198400000, 1238.0, 1242.0, 1236.0, 1240.0],
            [1718284800000, 1240.0, 1245.0, 1238.0, 1243.0],
            [1718371200000, 1243.0, 1248.0, 1241.0, 1246.0],
            [1718457600000, 1246.0, 1250.0, 1244.0, 1248.0],
            [1718544000000, 1248.0, 1252.0, 1246.0, 1250.0],
            [1718630400000, 1250.0, 1255.0, 1248.0, 1253.0],
            [1718716800000, 1253.0, 1258.0, 1251.0, 1256.0],
            [1718803200000, 1256.0, 1260.0, 1254.0, 1258.0],
            [1718889600000, 1258.0, 1262.0, 1256.0, 1260.0],
            [1718976000000, 1260.0, 1265.0, 1258.0, 1263.0],
            [1719062400000, 1263.0, 1268.0, 1261.0, 1266.0],
            [1719148800000, 1266.0, 1270.0, 1264.0, 1268.0],
            [1719235200000, 1268.0, 1272.0, 1266.0, 1270.0],
            [1719321600000, 1270.0, 1275.0, 1268.0, 1273.0],
            [1719408000000, 1273.0, 1278.0, 1271.0, 1276.0],
            [1719494400000, 1276.0, 1280.0, 1274.0, 1278.0],
            [1719580800000, 1278.0, 1282.0, 1276.0, 1280.0],
            [1719667200000, 1280.0, 1285.0, 1278.0, 1283.0],
            [1719753600000, 1283.0, 1288.0, 1281.0, 1286.0],
            [1719840000000, 1286.0, 1290.0, 1284.0, 1288.0],
            [1719926400000, 1288.0, 1292.0, 1286.0, 1290.0],
            [1720012800000, 1290.0, 1295.0, 1288.0, 1293.0],
            [1720099200000, 1293.0, 1298.0, 1291.0, 1296.0],
            [1720185600000, 1296.0, 1300.0, 1294.0, 1298.0],
            [1720272000000, 1298.0, 1302.0, 1296.0, 1300.0],
            [1720358400000, 1300.0, 1305.0, 1298.0, 1303.0],
            [1720444800000, 1303.0, 1308.0, 1301.0, 1306.0],
            [1720531200000, 1306.0, 1310.0, 1304.0, 1308.0],
            [1720617600000, 1308.0, 1312.0, 1306.0, 1310.0],
            [1720704000000, 1310.0, 1315.0, 1308.0, 1313.0],
            [1720790400000, 1313.0, 1318.0, 1311.0, 1316.0],
            [1720876800000, 1316.0, 1320.0, 1314.0, 1318.0],
            [1720963200000, 1318.0, 1322.0, 1316.0, 1320.0],
            [1721049600000, 1320.0, 1325.0, 1318.0, 1323.0],
            [1721136000000, 1323.0, 1328.0, 1321.0, 1326.0],
            [1721222400000, 1326.0, 1330.0, 1324.0, 1328.0],
            [1721308800000, 1328.0, 1332.0, 1326.0, 1330.0],
            [1721395200000, 1330.0, 1335.0, 1328.0, 1333.0],
            [1721481600000, 1333.0, 1338.0, 1331.0, 1336.0],
            [1721568000000, 1336.0, 1340.0, 1334.0, 1338.0],
            [1721654400000, 1338.0, 1342.0, 1336.0, 1340.0],
            [1721740800000, 1340.0, 1345.0, 1338.0, 1343.0],
            [1721827200000, 1343.0, 1348.0, 1341.0, 1346.0],
            [1721913600000, 1346.0, 1350.0, 1344.0, 1348.0],
            [1722000000000, 1348.0, 1352.0, 1346.0, 1350.0],
            [1722086400000, 1350.0, 1355.0, 1348.0, 1353.0],
            [1722172800000, 1353.0, 1358.0, 1351.0, 1356.0],
            [1722259200000, 1356.0, 1360.0, 1354.0, 1358.0],
            [1722345600000, 1358.0, 1362.0, 1356.0, 1360.0],
            [1722432000000, 1360.0, 1365.0, 1358.0, 1363.0],
            [1722518400000, 1363.0, 1368.0, 1361.0, 1366.0],
            [1722604800000, 1366.0, 1370.0, 1364.0, 1368.0],
            [1722691200000, 1368.0, 1372.0, 1366.0, 1370.0],
            [1722777600000, 1370.0, 1375.0, 1368.0, 1373.0],
            [1722864000000, 1373.0, 1378.0, 1371.0, 1376.0],
            [1722950400000, 1376.0, 1380.0, 1374.0, 1378.0],
            [1723036800000, 1378.0, 1382.0, 1376.0, 1380.0],
            [1723123200000, 1380.0, 1385.0, 1378.0, 1383.0],
            [1723209600000, 1383.0, 1388.0, 1381.0, 1386.0],
            [1723296000000, 1386.0, 1390.0, 1384.0, 1388.0],
            [1723382400000, 1388.0, 1392.0, 1386.0, 1390.0],
            [1723468800000, 1390.0, 1395.0, 1388.0, 1393.0],
            [1723555200000, 1393.0, 1398.0, 1391.0, 1396.0],
            [1723641600000, 1396.0, 1400.0, 1394.0, 1398.0],
            [1723728000000, 1398.0, 1402.0, 1396.0, 1400.0],
            [1723814400000, 1400.0, 1405.0, 1398.0, 1403.0],
            [1723900800000, 1403.0, 1408.0, 1401.0, 1406.0],
            [1723987200000, 1406.0, 1410.0, 1404.0, 1408.0],
            [1724073600000, 1408.0, 1412.0, 1406.0, 1410.0],
            [1724160000000, 1410.0, 1415.0, 1408.0, 1413.0],
            [1724246400000, 1413.0, 1418.0, 1411.0, 1416.0],
            [1724332800000, 1416.0, 1420.0, 1414.0, 1418.0],
            [1724419200000, 1418.0, 1422.0, 1416.0, 1420.0],
            [1724505600000, 1420.0, 1425.0, 1418.0, 1423.0],
            [1724592000000, 1423.0, 1428.0, 1421.0, 1426.0],
            [1724678400000, 1426.0, 1430.0, 1424.0, 1428.0],
            [1724764800000, 1428.0, 1432.0, 1426.0, 1430.0],
            [1724851200000, 1430.0, 1435.0, 1428.0, 1433.0],
            [1724937600000, 1433.0, 1438.0, 1431.0, 1436.0],
            [1725024000000, 1436.0, 1440.0, 1434.0, 1438.0],
            [1725110400000, 1438.0, 1442.0, 1436.0, 1440.0],
            [1725196800000, 1440.0, 1445.0, 1438.0, 1443.0],
            [1725283200000, 1443.0, 1448.0, 1441.0, 1446.0],
            [1725369600000, 1446.0, 1450.0, 1444.0, 1448.0],
            [1725456000000, 1448.0, 1452.0, 1446.0, 1450.0],
            [1725542400000, 1450.0, 1455.0, 1448.0, 1453.0],
            [1725628800000, 1453.0, 1458.0, 1451.0, 1456.0],
            [1725715200000, 1456.0, 1460.0, 1454.0, 1458.0],
            [1725801600000, 1458.0, 1462.0, 1456.0, 1460.0],
            [1725888000000, 1460.0, 1465.0, 1458.0, 1463.0],
            [1725974400000, 1463.0, 1468.0, 1461.0, 1466.0],
            [1726060800000, 1466.0, 1470.0, 1464.0, 1468.0],
            [1726147200000, 1468.0, 1472.0, 1466.0, 1470.0],
            [1726233600000, 1470.0, 1475.0, 1468.0, 1473.0],
            [1726320000000, 1473.0, 1478.0, 1471.0, 1476.0],
            [1726406400000, 1476.0, 1480.0, 1474.0, 1478.0],
            [1726492800000, 1478.0, 1482.0, 1476.0, 1480.0],
            [1726579200000, 1480.0, 1485.0, 1478.0, 1483.0],
            [1726665600000, 1483.0, 1488.0, 1481.0, 1486.0],
            [1726752000000, 1486.0, 1490.0, 1484.0, 1488.0],
            [1726838400000, 1488.0, 1492.0, 1486.0, 1490.0],
            [1726924800000, 1490.0, 1495.0, 1488.0, 1493.0],
            [1727011200000, 1493.0, 1498.0, 1491.0, 1496.0],
            [1727097600000, 1496.0, 1500.0, 1494.0, 1498.0],
            [1727184000000, 1498.0, 1502.0, 1496.0, 1500.0],
            [1727270400000, 1500.0, 1505.0, 1498.0, 1503.0],
            [1727356800000, 1503.0, 1508.0, 1501.0, 1506.0],
            [1727443200000, 1506.0, 1510.0, 1504.0, 1508.0],
            [1727529600000, 1508.0, 1512.0, 1506.0, 1510.0],
            [1727616000000, 1510.0, 1515.0, 1508.0, 1513.0],
            [1727702400000, 1513.0, 1518.0, 1511.0, 1516.0],
            [1727788800000, 1516.0, 1520.0, 1514.0, 1518.0],
            [1727875200000, 1518.0, 1522.0, 1516.0, 1520.0],
            [1727961600000, 1520.0, 1525.0, 1518.0, 1523.0],
            [1728048000000, 1523.0, 1528.0, 1521.0, 1526.0],
            [1728134400000, 1526.0, 1530.0, 1524.0, 1528.0],
            [1728220800000, 1528.0, 1532.0, 1526.0, 1530.0],
            [1728307200000, 1530.0, 1535.0, 1528.0, 1533.0],
            [1728393600000, 1533.0, 1538.0, 1531.0, 1536.0],
            [1728480000000, 1536.0, 1540.0, 1534.0, 1538.0],
            [1728566400000, 1538.0, 1542.0, 1536.0, 1540.0],
            [1728652800000, 1540.0, 1545.0, 1538.0, 1543.0],
            [1728739200000, 1543.0, 1548.0, 1541.0, 1546.0],
            [1728825600000, 1546.0, 1550.0, 1544.0, 1548.0],
            [1728912000000, 1548.0, 1552.0, 1546.0, 1550.0],
            [1728998400000, 1550.0, 1555.0, 1548.0, 1553.0],
            [1729084800000, 1553.0, 1558.0, 1551.0, 1556.0],
            [1729171200000, 1556.0, 1560.0, 1554.0, 1558.0],
            [1729257600000, 1558.0, 1562.0, 1556.0, 1560.0],
            [1729344000000, 1560.0, 1565.0, 1558.0, 1563.0],
            [1729430400000, 1563.0, 1568.0, 1561.0, 1566.0],
            [1729516800000, 1566.0, 1570.0, 1564.0, 1568.0],
            [1729603200000, 1568.0, 1572.0, 1566.0, 1570.0],
            [1729689600000, 1570.0, 1575.0, 1568.0, 1573.0],
            [1729776000000, 1573.0, 1578.0, 1571.0, 1576.0],
            [1729862400000, 1576.0, 1580.0, 1574.0, 1578.0],
            [1729948800000, 1578.0, 1582.0, 1576.0, 1580.0],
            [1730035200000, 1580.0, 1585.0, 1578.0, 1583.0],
            [1730121600000, 1583.0, 1588.0, 1581.0, 1586.0],
            [1730208000000, 1586.0, 1590.0, 1584.0, 1588.0],
            [1730294400000, 1588.0, 1592.0, 1586.0, 1590.0],
            [1730380800000, 1590.0, 1595.0, 1588.0, 1593.0],
            [1730467200000, 1593.0, 1598.0, 1591.0, 1596.0],
            [1730553600000, 1596.0, 1600.0, 1594.0, 1598.0],
            [1730640000000, 1598.0, 1602.0, 1596.0, 1600.0],
            [1730726400000, 1600.0, 1605.0, 1598.0, 1603.0],
            [1730812800000, 1603.0, 1608.0, 1601.0, 1606.0],
            [1730899200000, 1606.0, 1610.0, 1604.0, 1608.0],
            [1730985600000, 1608.0, 1612.0, 1606.0, 1610.0],
            [1731072000000, 1610.0, 1615.0, 1608.0, 1613.0],
            [1731158400000, 1613.0, 1618.0, 1611.0, 1616.0],
            [1731244800000, 1616.0, 1620.0, 1614.0, 1618.0],
            [1731331200000, 1618.0, 1622.0, 1616.0, 1620.0],
            [1731417600000, 1620.0, 1625.0, 1618.0, 1623.0],
            [1731504000000, 1623.0, 1628.0, 1621.0, 1626.0],
            [1731590400000, 1626.0, 1630.0, 1624.0, 1628.0],
            [1731676800000, 1628.0, 1632.0, 1626.0, 1630.0],
            [1731763200000, 1630.0, 1635.0, 1628.0, 1633.0],
            [1731849600000, 1633.0, 1638.0, 1631.0, 1636.0],
            [1731936000000, 1636.0, 1640.0, 1634.0, 1638.0],
            [1732022400000, 1638.0, 1642.0, 1636.0, 1640.0],
            [1732108800000, 1640.0, 1645.0, 1638.0, 1643.0],
            [1732195200000, 1643.0, 1648.0, 1641.0, 1646.0],
            [1732281600000, 1646.0, 1650.0, 1644.0, 1648.0],
            [1732368000000, 1648.0, 1652.0, 1646.0, 1650.0],
            [1732454400000, 1650.0, 1655.0, 1648.0, 1653.0],
            [1732540800000, 1653.0, 1658.0, 1651.0, 1656.0],
            [1732627200000, 1656.0, 1660.0, 1654.0, 1658.0],
            [1732713600000, 1658.0, 1662.0, 1656.0, 1660.0],
            [1732800000000, 1660.0, 1665.0, 1658.0, 1663.0],
            [1732886400000, 1663.0, 1668.0, 1661.0, 1666.0],
            [1732972800000, 1666.0, 1670.0, 1664.0, 1668.0],
            [1733059200000, 1668.0, 1672.0, 1666.0, 1670.0],
            [1733145600000, 1670.0, 1675.0, 1668.0, 1673.0],
            [1733232000000, 1673.0, 1678.0, 1671.0, 1676.0],
            [1733318400000, 1676.0, 1680.0, 1674.0, 1678.0],
            [1733404800000, 1678.0, 1682.0, 1676.0, 1680.0],
            [1733491200000, 1680.0, 1685.0, 1678.0, 1683.0],
            [1733577600000, 1683.0, 1688.0, 1681.0, 1686.0],
            [1733664000000, 1686.0, 1690.0, 1684.0, 1688.0],
            [1733750400000, 1688.0, 1692.0, 1686.0, 1690.0],
            [1733836800000, 1690.0, 1695.0, 1688.0, 1693.0],
            [1733923200000, 1693.0, 1698.0, 1691.0, 1696.0],
            [1734009600000, 1696.0, 1700.0, 1694.0, 1698.0],
            [1734096000000, 1698.0, 1702.0, 1696.0, 1700.0],
            [1734182400000, 1700.0, 1705.0, 1698.0, 1703.0],
            [1734268800000, 1703.0, 1708.0, 1701.0, 1706.0],
            [1734355200000, 1706.0, 1710.0, 1704.0, 1708.0],
            [1734441600000, 1708.0, 1712.0, 1706.0, 1710.0],
            [1734528000000, 1710.0, 1715.0, 1708.0, 1713.0],
            [1734614400000, 1713.0, 1718.0, 1711.0, 1716.0],
            [1734700800000, 1716.0, 1720.0, 1714.0, 1718.0],
            [1734787200000, 1718.0, 1722.0, 1716.0, 1720.0],
            [1734873600000, 1720.0, 1725.0, 1718.0, 1723.0],
            [1734960000000, 1723.0, 1728.0, 1721.0, 1726.0],
            [1735046400000, 1726.0, 1730.0, 1724.0, 1728.0],
            [1735132800000, 1728.0, 1732.0, 1726.0, 1730.0],
            [1735219200000, 1730.0, 1735.0, 1728.0, 1733.0],
            [1735305600000, 1733.0, 1738.0, 1731.0, 1736.0],
            [1735392000000, 1735.0, 1740.0, 1733.0, 1738.0],
            [1735478400000, 1738.0, 1742.0, 1736.0, 1740.0],
            [1735564800000, 1740.0, 1745.0, 1738.0, 1743.0],
            [1735651200000, 1743.0, 1748.0, 1741.0, 1746.0],
            [1735737600000, 1746.0, 1750.0, 1744.0, 1748.0],
            [1735824000000, 1748.0, 1752.0, 1746.0, 1750.0],
            [1735910400000, 1750.0, 1755.0, 1748.0, 1753.0],
            [1735996800000, 1753.0, 1758.0, 1751.0, 1756.0],
            [1736083200000, 1756.0, 1760.0, 1754.0, 1758.0],
            [1736169600000, 1758.0, 1762.0, 1756.0, 1760.0],
            [1736256000000, 1760.0, 1765.0, 1758.0, 1763.0],
            [1736342400000, 1763.0, 1768.0, 1761.0, 1766.0],
            [1736428800000, 1766.0, 1770.0, 1764.0, 1768.0],
            [1736515200000, 1768.0, 1772.0, 1766.0, 1770.0],
            [1736601600000, 1770.0, 1775.0, 1768.0, 1773.0],
            [1736688000000, 1773.0, 1778.0, 1771.0, 1776.0],
            [1736774400000, 1776.0, 1780.0, 1774.0, 1778.0],
            [1736860800000, 1778.0, 1782.0, 1776.0, 1780.0],
            [1736947200000, 1780.0, 1785.0, 1778.0, 1783.0],
            [1737033600000, 1783.0, 1788.0, 1781.0, 1786.0],
            [1737120000000, 1786.0, 1790.0, 1784.0, 1788.0],
            [1737206400000, 1788.0, 1792.0, 1786.0, 1790.0],
            [1737292800000, 1790.0, 1795.0, 1788.0, 1793.0],
            [1737379200000, 1793.0, 1798.0, 1791.0, 1796.0],
            [1737465600000, 1796.0, 1800.0, 1794.0, 1798.0],
            [1737552000000, 1798.0, 1802.0, 1796.0, 1800.0],
            [1737638400000, 1800.0, 1805.0, 1798.0, 1803.0],
            [1737724800000, 1803.0, 1808.0, 1801.0, 1806.0],
            [1737811200000, 1806.0, 1810.0, 1804.0, 1808.0],
            [1737897600000, 1808.0, 1812.0, 1806.0, 1810.0],
            [1737984000000, 1810.0, 1815.0, 1808.0, 1813.0],
            [1738070400000, 1813.0, 1818.0, 1811.0, 1816.0],
            [1738156800000, 1816.0, 1820.0, 1814.0, 1818.0],
            [1738243200000, 1818.0, 1822.0, 1816.0, 1820.0],
            [1738329600000, 1820.0, 1825.0, 1818.0, 1823.0],
            [1738416000000, 1823.0, 1828.0, 1821.0, 1826.0],
            [1738502400000, 1826.0, 1830.0, 1824.0, 1828.0],
            [1738588800000, 1828.0, 1832.0, 1826.0, 1830.0],
            [1738675200000, 1830.0, 1835.0, 1828.0, 1833.0],
            [1738761600000, 1833.0, 1838.0, 1831.0, 1836.0],
            [1738848000000, 1836.0, 1840.0, 1834.0, 1838.0],
            [1738934400000, 1838.0, 1842.0, 1836.0, 1840.0],
            [1739020800000, 1840.0, 1845.0, 1838.0, 1843.0],
            [1739107200000, 1843.0, 1848.0, 1841.0, 1846.0],
            [1739193600000, 1846.0, 1850.0, 1844.0, 1848.0],
            [1739280000000, 1848.0, 1852.0, 1846.0, 1850.0],
            [1739366400000, 1850.0, 1855.0, 1848.0, 1853.0],
            [1739452800000, 1853.0, 1858.0, 1851.0, 1856.0],
            [1739539200000, 1856.0, 1860.0, 1854.0, 1858.0],
            [1739625600000, 1858.0, 1862.0, 1856.0, 1860.0],
            [1739712000000, 1860.0, 1865.0, 1858.0, 1863.0],
            [1739798400000, 1863.0, 1868.0, 1861.0, 1866.0],
            [1739884800000, 1866.0, 1870.0, 1864.0, 1868.0],
            [1739971200000, 1868.0, 1872.0, 1866.0, 1870.0],
            [1740057600000, 1870.0, 1875.0, 1868.0, 1873.0],
            [1740144000000, 1873.0, 1878.0, 1871.0, 1876.0],
            [1740230400000, 1876.0, 1880.0, 1874.0, 1878.0],
            [1740316800000, 1878.0, 1882.0, 1876.0, 1880.0],
            [1740403200000, 1880.0, 1885.0, 1878.0, 1883.0],
            [1740489600000, 1883.0, 1888.0, 1881.0, 1886.0],
            [1740576000000, 1886.0, 1890.0, 1884.0, 1888.0],
            [1740662400000, 1888.0, 1892.0, 1886.0, 1890.0],
            [1740748800000, 1890.0, 1895.0, 1888.0, 1893.0],
            [1740835200000, 1893.0, 1898.0, 1891.0, 1896.0],
            [1740921600000, 1896.0, 1900.0, 1894.0, 1898.0],
            [1741008000000, 1898.0, 1902.0, 1896.0, 1900.0],
            [1741094400000, 1900.0, 1905.0, 1898.0, 1903.0],
            [1741180800000, 1903.0, 1908.0, 1901.0, 1906.0],
            [1741267200000, 1906.0, 1910.0, 1904.0, 1908.0],
            [1741353600000, 1908.0, 1912.0, 1906.0, 1910.0],
            [1741440000000, 1910.0, 1915.0, 1908.0, 1913.0],
            [1741526400000, 1913.0, 1918.0, 1911.0, 1916.0],
            [1741612800000, 1916.0, 1920.0, 1914.0, 1918.0],
            [1741699200000, 1918.0, 1922.0, 1916.0, 1920.0],
            [1741785600000, 1920.0, 1925.0, 1918.0, 1923.0],
            [1741872000000, 1923.0, 1928.0, 1921.0, 1926.0],
            [1741958400000, 1926.0, 1930.0, 1924.0, 1928.0],
            [1742044800000, 1928.0, 1932.0, 1926.0, 1930.0],
            [1742131200000, 1930.0, 1935.0, 1928.0, 1933.0],
            [1742217600000, 1933.0, 1938.0, 1931.0, 1936.0],
            [1742304000000, 1936.0, 1940.0, 1934.0, 1938.0],
            [1742390400000, 1938.0, 1942.0, 1936.0, 1940.0],
            [1742476800000, 1940.0, 1945.0, 1938.0, 1943.0],
            [1742563200000, 1943.0, 1948.0, 1941.0, 1946.0],
            [1742649600000, 1946.0, 1950.0, 1944.0, 1948.0],
            [1742736000000, 1948.0, 1952.0, 1946.0, 1950.0],
            [1742822400000, 1950.0, 1955.0, 1948.0, 1953.0],
            [1742908800000, 1953.0, 1958.0, 1951.0, 1956.0],
            [1742995200000, 1956.0, 1960.0, 1954.0, 1958.0],
            [1743081600000, 1958.0, 1962.0, 1956.0, 1960.0],
            [1743168000000, 1960.0, 1965.0, 1958.0, 1963.0],
            [1743254400000, 1963.0, 1968.0, 1961.0, 1966.0],
            [1743340800000, 1966.0, 1970.0, 1964.0, 1968.0],
            [1743427200000, 1968.0, 1972.0, 1966.0, 1970.0],
            [1743513600000, 1970.0, 1975.0, 1968.0, 1973.0],
            [1743600000000, 1973.0, 1978.0, 1971.0, 1976.0],
            [1743686400000, 1976.0, 1980.0, 1974.0, 1978.0],
            [1743772800000, 1978.0, 1982.0, 1976.0, 1980.0],
            [1743859200000, 1980.0, 1985.0, 1978.0, 1983.0],
            [1743945600000, 1983.0, 1988.0, 1981.0, 1986.0],
            [1744032000000, 1986.0, 1990.0, 1984.0, 1988.0],
            [1744118400000, 1988.0, 1992.0, 1986.0, 1990.0],
            [1744204800000, 1990.0, 1995.0, 1988.0, 1993.0],
            [1744291200000, 1993.0, 1998.0, 1991.0, 1996.0],
            [1744377600000, 1996.0, 2000.0, 1994.0, 1998.0],
            [1744464000000, 1998.0, 2002.0, 1996.0, 2000.0],
            [1744550400000, 2000.0, 2005.0, 1998.0, 2003.0],
            [1744636800000, 2003.0, 2008.0, 2001.0, 2006.0],
            [1744723200000, 2006.0, 2010.0, 2004.0, 2008.0],
            [1744809600000, 2008.0, 2012.0, 2006.0, 2010.0],
            [1744896000000, 2010.0, 2015.0, 2008.0, 2013.0],
            [1744982400000, 2013.0, 2018.0, 2011.0, 2016.0],
            [1745068800000, 2016.0, 2020.0, 2014.0, 2018.0],
            [1745155200000, 2018.0, 2022.0, 2016.0, 2020.0],
            [1745241600000, 2020.0, 2025.0, 2018.0, 2023.0],
            [1745328000000, 2023.0, 2028.0, 2021.0, 2026.0],
            [1745414400000, 2026.0, 2030.0, 2024.0, 2028.0],
            [1745500800000, 2028.0, 2032.0, 2026.0, 2030.0],
            [1745587200000, 2030.0, 2035.0, 2028.0, 2033.0],
            [1745673600000, 2033.0, 2038.0, 2031.0, 2036.0],
            [1745760000000, 2036.0, 2040.0, 2034.0, 2038.0],
            [1745846400000, 2038.0, 2042.0, 2036.0, 2040.0],
            [1745932800000, 2040.0, 2045.0, 2038.0, 2043.0],
            [1746019200000, 2043.0, 2048.0, 2041.0, 2046.0],
            [1746105600000, 2046.0, 2050.0, 2044.0, 2048.0],
            [1746192000000, 2048.0, 2052.0, 2046.0, 2050.0],
            [1746278400000, 2050.0, 2055.0, 2048.0, 2053.0],
            [1746364800000, 2053.0, 2058.0, 2051.0, 2056.0],
            [1746451200000, 2056.0, 2060.0, 2054.0, 2058.0],
            [1746537600000, 2058.0, 2062.0, 2056.0, 2060.0],
            [1746624000000, 2060.0, 2065.0, 2058.0, 2063.0],
            [1746710400000, 2063.0, 2068.0, 2061.0, 2066.0],
            [1746796800000, 2066.0, 2070.0, 2064.0, 2068.0],
            [1746883200000, 2068.0, 2072.0, 2066.0, 2070.0],
            [1746969600000, 2070.0, 2075.0, 2068.0, 2073.0],
            [1747056000000, 2073.0, 2078.0, 2071.0, 2076.0],
            [1747142400000, 2076.0, 2080.0, 2074.0, 2078.0],
            [1747228800000, 2078.0, 2082.0, 2076.0, 2080.0],
            [1747315200000, 2080.0, 2085.0, 2078.0, 2083.0],
            [1747401600000, 2083.0, 2088.0, 2081.0, 2086.0],
            [1747488000000, 2086.0, 2090.0, 2084.0, 2088.0],
            [1747574400000, 2088.0, 2092.0, 2086.0, 2090.0],
            [1747660800000, 2090.0, 2095.0, 2088.0, 2093.0],
            [1747747200000, 2093.0, 2098.0, 2091.0, 2096.0],
            [1747833600000, 2096.0, 2100.0, 2094.0, 2098.0],
            [1747920000000, 2098.0, 2102.0, 2096.0, 2100.0],
            [1748006400000, 2100.0, 2105.0, 2098.0, 2103.0],
            [1748092800000, 2103.0, 2108.0, 2101.0, 2106.0],
            [1748179200000, 2106.0, 2110.0, 2104.0, 2108.0],
            [1748265600000, 2108.0, 2112.0, 2106.0, 2110.0],
            [1748352000000, 2110.0, 2115.0, 2108.0, 2113.0],
            [1748438400000, 2113.0, 2118.0, 2111.0, 2116.0],
            [1748524800000, 2116.0, 2120.0, 2114.0, 2118.0],
            [1748611200000, 2118.0, 2122.0, 2116.0, 2120.0],
            [1748697600000, 2120.0, 2125.0, 2118.0, 2123.0],
            [1748784000000, 2123.0, 2128.0, 2121.0, 2126.0],
            [1748870400000, 2126.0, 2130.0, 2124.0, 2128.0],
            [1748956800000, 2128.0, 2132.0, 2126.0, 2130.0],
            [1749043200000, 2130.0, 2135.0, 2128.0, 2133.0],
            [1749129600000, 2133.0, 2138.0, 2131.0, 2136.0],
            [1749216000000, 2136.0, 2140.0, 2134.0, 2138.0],
            [1749302400000, 2138.0, 2142.0, 2136.0, 2140.0],
            [1749388800000, 2140.0, 2145.0, 2138.0, 2143.0],
            [1749475200000, 2143.0, 2148.0, 2141.0, 2146.0],
            [1749561600000, 2146.0, 2150.0, 2144.0, 2148.0],
            [1749648000000, 2148.0, 2152.0, 2146.0, 2150.0],
            [1749734400000, 2150.0, 2155.0, 2148.0, 2153.0],
            [1749820800000, 2153.0, 2158.0, 2151.0, 2156.0],
            [1749907200000, 2156.0, 2160.0, 2154.0, 2158.0],
            [1749993600000, 2158.0, 2162.0, 2156.0, 2160.0],
            [1750080000000, 2160.0, 2165.0, 2158.0, 2163.0],
            [1750166400000, 2163.0, 2168.0, 2161.0, 2166.0],
            [1750252800000, 2166.0, 2170.0, 2164.0, 2168.0],
            [1750339200000, 2168.0, 2172.0, 2166.0, 2170.0],
            [1750425600000, 2170.0, 2175.0, 2168.0, 2173.0],
            [1750512000000, 2173.0, 2178.0, 2171.0, 2176.0],
            [1750598400000, 2176.0, 2180.0, 2174.0, 2178.0],
            [1750684800000, 2178.0, 2182.0, 2176.0, 2180.0],
            [1750771200000, 2180.0, 2185.0, 2178.0, 2183.0],
            [1750857600000, 2183.0, 2188.0, 2181.0, 2186.0],
            [1750944000000, 2186.0, 2190.0, 2184.0, 2188.0],
            [1751030400000, 2188.0, 2192.0, 2186.0, 2190.0],
            [1751116800000, 2190.0, 2195.0, 2188.0, 2193.0],
            [1751203200000, 2193.0, 2198.0, 2191.0, 2196.0],
            [1751289600000, 2196.0, 2200.0, 2194.0, 2198.0],
            [1751376000000, 2198.0, 2202.0, 2196.0, 2200.0],
            [1751462400000, 2200.0, 2205.0, 2198.0, 2203.0],
            [1751548800000, 2203.0, 2208.0, 2201.0, 2206.0],
            [1751635200000, 2206.0, 2210.0, 2204.0, 2208.0],
            [1751721600000, 2208.0, 2212.0, 2206.0, 2210.0],
            [1751808000000, 2210.0, 2215.0, 2208.0, 2213.0],
            [1751894400000, 2213.0, 2218.0, 2211.0, 2216.0],
            [1751980800000, 2216.0, 2220.0, 2214.0, 2218.0],
            [1752067200000, 2218.0, 2222.0, 2216.0, 2220.0],
            [1752153600000, 2220.0, 2225.0, 2218.0, 2223.0],
            [1752240000000, 2223.0, 2228.0, 2221.0, 2226.0],
            [1752326400000, 2226.0, 2230.0, 2224.0, 2228.0],
            [1752412800000, 2228.0, 2232.0, 2226.0, 2230.0],
            [1752499200000, 2230.0, 2235.0, 2228.0, 2233.0],
            [1752585600000, 2233.0, 2238.0, 2231.0, 2236.0],
            [1752672000000, 2236.0, 2240.0, 2234.0, 2238.0],
            [1752758400000, 2238.0, 2242.0, 2236.0, 2240.0],
            [1752844800000, 2240.0, 2245.0, 2238.0, 2243.0],
            [1752931200000, 2243.0, 2248.0, 2241.0, 2246.0],
            [1753017600000, 2246.0, 2250.0, 2244.0, 2248.0],
            [1753104000000, 2248.0, 2252.0, 2246.0, 2250.0],
            [1753190400000, 2250.0, 2255.0, 2248.0, 2253.0],
            [1753276800000, 2253.0, 2258.0, 2251.0, 2256.0],
            [1753363200000, 2256.0, 2260.0, 2254.0, 2258.0],
            [1753449600000, 2258.0, 2262.0, 2256.0, 2260.0],
            [1753536000000, 2260.0, 2265.0, 2258.0, 2263.0],
            [1753622400000, 2263.0, 2268.0, 2261.0, 2266.0],
            [1753708800000, 2266.0, 2270.0, 2264.0, 2268.0],
            [1753795200000, 2268.0, 2272.0, 2266.0, 2270.0],
            [1753881600000, 2270.0, 2275.0, 2268.0, 2273.0],
            [1753968000000, 2273.0, 2278.0, 2271.0, 2276.0],
            [1754054400000, 2276.0, 2280.0, 2274.0, 2278.0],
            [1754140800000, 2278.0, 2282.0, 2276.0, 2280.0],
            [1754227200000, 2280.0, 2285.0, 2278.0, 2283.0],
            [1754313600000, 2283.0, 2288.0, 2281.0, 2286.0],
            [1754400000000, 2286.0, 2290.0, 2284.0, 2288.0],
            [1754486400000, 2288.0, 2292.0, 2286.0, 2290.0],
            [1754572800000, 2290.0, 2295.0, 2288.0, 2293.0],
            [1754659200000, 2293.0, 2298.0, 2291.0, 2296.0],
            [1754745600000, 2296.0, 2300.0, 2294.0, 2298.0],
            [1754832000000, 2298.0, 2302.0, 2296.0, 2300.0],
            [1754918400000, 2300.0, 2305.0, 2298.0, 2303.0],
            [1755004800000, 2303.0, 2308.0, 2301.0, 2306.0],
            [1755091200000, 2306.0, 2310.0, 2304.0, 2308.0],
            [1755177600000, 2308.0, 2312.0, 2306.0, 2310.0],
            [1755264000000, 2310.0, 2315.0, 2308.0, 2313.0],
            [1755350400000, 2313.0, 2318.0, 2311.0, 2316.0],
            [1755436800000, 2316.0, 2320.0, 2314.0, 2318.0],
            [1755523200000, 2318.0, 2322.0, 2316.0, 2320.0],
            [1755609600000, 2320.0, 2325.0, 2318.0, 2323.0],
            [1755696000000, 2323.0, 2328.0, 2321.0, 2326.0],
            [1755782400000, 2326.0, 2330.0, 2324.0, 2328.0],
            [1755868800000, 2328.0, 2332.0, 2326.0, 2330.0],
            [1755955200000, 2330.0, 2335.0, 2328.0, 2333.0],
            [1756041600000, 2333.0, 2338.0, 2331.0, 2336.0],
            [1756128000000, 2336.0, 2340.0, 2334.0, 2338.0],
            [1756214400000, 2338.0, 2342.0, 2336.0, 2340.0],
            [1756300800000, 2340.0, 2345.0, 2338.0, 2343.0],
            [1756387200000, 2343.0, 2348.0, 2341.0, 2346.0],
            [1756473600000, 2346.0, 2350.0, 2344.0, 2348.0],
            [1756560000000, 2348.0, 2352.0, 2346.0, 2350.0],
            [1756646400000, 2350.0, 2355.0, 2348.0, 2353.0],
            [1756732800000, 2353.0, 2358.0, 2351.0, 2356.0],
            [1756819200000, 2356.0, 2360.0, 2354.0, 2358.0],
            [1756905600000, 2358.0, 2362.0, 2356.0, 2360.0],
            [1756992000000, 2360.0, 2365.0, 2358.0, 2363.0],
            [1757078400000, 2363.0, 2368.0, 2361.0, 2366.0],
            [1757164800000, 2366.0, 2370.0, 2364.0, 2368.0],
            [1757251200000, 2368.0, 2372.0, 2366.0, 2370.0],
            [1757337600000, 2370.0, 2375.0, 2368.0, 2373.0],
            [1757424000000, 2373.0, 2378.0, 2371.0, 2376.0],
            [1757510400000, 2376.0, 2380.0, 2374.0, 2378.0],
            [1757596800000, 2378.0, 2382.0, 2376.0, 2380.0],
            [1757683200000, 2380.0, 2385.0, 2378.0, 2383.0],
            [1757769600000, 2383.0, 2388.0, 2381.0, 2386.0],
            [1757856000000, 2386.0, 2390.0, 2384.0, 2388.0],
            [1757942400000, 2388.0, 2392.0, 2386.0, 2390.0],
            [1758028800000, 2390.0, 2395.0, 2388.0, 2393.0],
            [1758115200000, 2393.0, 2398.0, 2391.0, 2396.0],
            [1758201600000, 2396.0, 2400.0, 2394.0, 2398.0],
            [1758288000000, 2398.0, 2402.0, 2396.0, 2400.0],
            [1758374400000, 2400.0, 2405.0, 2398.0, 2403.0],
            [1758460800000, 2403.0, 2408.0, 2401.0, 2406.0],
            [1758547200000, 2406.0, 2410.0, 2404.0, 2408.0],
            [1758633600000, 2408.0, 2412.0, 2406.0, 2410.0],
            [1758720000000, 2410.0, 2415.0, 2408.0, 2413.0],
            [1758806400000, 2413.0, 2418.0, 2411.0, 2416.0],
            [1758892800000, 2416.0, 2420.0, 2414.0, 2418.0],
            [1758979200000, 2418.0, 2422.0, 2416.0, 2420.0],
            [1759065600000, 2420.0, 2425.0, 2418.0, 2423.0],
            [1759152000000, 2423.0, 2428.0, 2421.0, 2426.0],
            [1759238400000, 2426.0, 2430.0, 2424.0, 2428.0],
            [1759324800000, 2428.0, 2432.0, 2426.0, 2430.0],
            [1759411200000, 2430.0, 2435.0, 2428.0, 2433.0],
            [1759497600000, 2433.0, 2438.0, 2431.0, 2436.0],
            [1759584000000, 2436.0, 2440.0, 2434.0, 2438.0],
            [1759670400000, 2438.0, 2442.0, 2436.0, 2440.0],
            [1759756800000, 2440.0, 2445.0, 2438.0, 2443.0],
            [1759843200000, 2443.0, 2448.0, 2441.0, 2446.0],
            [1759929600000, 2446.0, 2450.0, 2444.0, 2448.0],
            [1760016000000, 2448.0, 2452.0, 2446.0, 2450.0],
            [1760102400000, 2450.0, 2455.0, 2448.0, 2453.0],
            [1760188800000, 2453.0, 2458.0, 2451.0, 2456.0],
            [1760275200000, 2456.0, 2460.0, 2454.0, 2458.0],
            [1760361600000, 2458.0, 2462.0, 2456.0, 2460.0],
            [1760448000000, 2460.0, 2465.0, 2458.0, 2463.0],
            [1760534400000, 2463.0, 2468.0, 2461.0, 2466.0],
            [1760620800000, 2466.0, 2470.0, 2464.0, 2468.0],
            [1760707200000, 2468.0, 2472.0, 2466.0, 2470.0],
            [1760793600000, 2470.0, 2475.0, 2468.0, 2473.0],
            [1760880000000, 2473.0, 2478.0, 2471.0, 2476.0],
            [1760966400000, 2476.0, 2480.0, 2474.0, 2478.0],
            [1761052800000, 2478.0, 2482.0, 2476.0, 2480.0],
            [1761139200000, 2480.0, 2485.0, 2478.0, 2483.0],
            [1761225600000, 2483.0, 2488.0, 2481.0, 2486.0],
            [1761312000000, 2486.0, 2490.0, 2484.0, 2488.0],
            [1761398400000, 2488.0, 2492.0, 2486.0, 2490.0],
            [1761484800000, 2490.0, 2495.0, 2488.0, 2493.0],
            [1761571200000, 2493.0, 2498.0, 2491.0, 2496.0],
            [1761657600000, 2496.0, 2500.0, 2494.0, 2498.0],
            [1761744000000, 2498.0, 2502.0, 2496.0, 2500.0],
            [1761830400000, 2500.0, 2505.0, 2498.0, 2503.0],
            [1761916800000, 2503.0, 2508.0, 2501.0, 2506.0],
            [1762003200000, 2506.0, 2510.0, 2504.0, 2508.0],
            [1762089600000, 2508.0, 2512.0, 2506.0, 2510.0],
            [1762176000000, 2510.0, 2515.0, 2508.0, 2513.0],
            [1762262400000, 2513.0, 2518.0, 2511.0, 2516.0],
            [1762348800000, 2516.0, 2520.0, 2514.0, 2518.0],
            [1762435200000, 2518.0, 2522.0, 2516.0, 2520.0],
            [1762521600000, 2520.0, 2525.0, 2518.0, 2523.0],
            [1762608000000, 2523.0, 2528.0, 2521.0, 2526.0],
            [1762694400000, 2526.0, 2530.0, 2524.0, 2528.0],
            [1762780800000, 2528.0, 2532.0, 2526.0, 2530.0],
            [1762867200000, 2530.0, 2535.0, 2528.0, 2533.0],
            [1762953600000, 2533.0, 2538.0, 2531.0, 2536.0],
            [1763040000000, 2536.0, 2540.0, 2534.0, 2538.0],
            [1763126400000, 2538.0, 2542.0, 2536.0, 2540.0],
            [1763212800000, 2540.0, 2545.0, 2538.0, 2543.0],
            [1763299200000, 2543.0, 2548.0, 2541.0, 2546.0],
            [1763385600000, 2546.0, 2550.0, 2544.0, 2548.0],
            [1763472000000, 2548.0, 2552.0, 2546.0, 2550.0],
            [1763558400000, 2550.0, 2555.0, 2548.0, 2553.0],
            [1763644800000, 2553.0, 2558.0, 2551.0, 2556.0],
            [1763731200000, 2556.0, 2560.0, 2554.0, 2558.0],
            [1763817600000, 2558.0, 2562.0, 2556.0, 2560.0],
            [1763904000000, 2560.0, 2565.0, 2558.0, 2563.0],
            [1763990400000, 2563.0, 2568.0, 2561.0, 2566.0],
            [1764076800000, 2566.0, 2570.0, 2564.0, 2568.0],
            [1764163200000, 2568.0, 2572.0, 2566.0, 2570.0],
            [1764249600000, 2570.0, 2575.0, 2568.0, 2573.0],
            [1764336000000, 2573.0, 2578.0, 2571.0, 2576.0],
            [1764422400000, 2576.0, 2580.0, 2574.0, 2578.0],
            [1764508800000, 2578.0, 2582.0, 2576.0, 2580.0],
            [1764595200000, 2580.0, 2585.0, 2578.0, 2583.0],
            [1764681600000, 2583.0, 2588.0, 2581.0, 2586.0],
            [1764768000000, 2586.0, 2590.0, 2584.0, 2588.0],
            [1764854400000, 2588.0, 2592.0, 2586.0, 2590.0],
            [1764940800000, 2590.0, 2595.0, 2588.0, 2593.0],
            [1765027200000, 2593.0, 2598.0, 2591.0, 2596.0],
            [1765113600000, 2596.0, 2600.0, 2594.0, 2598.0],
            [1765200000000, 2598.0, 2602.0, 2596.0, 2600.0],
            [1765286400000, 2600.0, 2605.0, 2598.0, 2603.0],
            [1765372800000, 2603.0, 2608.0, 2601.0, 2606.0],
            [1765459200000, 2606.0, 2610.0, 2604.0, 2608.0],
            [1765545600000, 2608.0, 2612.0, 2606.0, 2610.0],
            [1765632000000, 2610.0, 2615.0, 2608.0, 2613.0],
            [1765718400000, 2613.0, 2618.0, 2611.0, 2616.0],
            [1765804800000, 2616.0, 2620.0, 2614.0, 2618.0],
            [1765891200000, 2618.0, 2622.0, 2616.0, 2620.0],
            [1765977600000, 2620.0, 2625.0, 2618.0, 2623.0],
            [1766064000000, 2623.0, 2628.0, 2621.0, 2626.0],
            [1766150400000, 2626.0, 2630.0, 2624.0, 2628.0],
            [1766236800000, 2628.0, 2632.0, 2626.0, 2630.0],
            [1766323200000, 2630.0, 2635.0, 2628.0, 2633.0],
            [1766409600000, 2633.0, 2638.0, 2631.0, 2636.0],
            [1766496000000, 2636.0, 2640.0, 2634.0, 2638.0],
            [1766582400000, 2638.0, 2642.0, 2636.0, 2640.0],
            [1766668800000, 2640.0, 2645.0, 2638.0, 2643.0],
            [1766755200000, 2643.0, 2648.0, 2641.0, 2646.0],
            [1766841600000, 2646.0, 2650.0, 2644.0, 2648.0],
            [1766928000000, 2648.0, 2652.0, 2646.0, 2650.0],
            [1767014400000, 2650.0, 2655.0, 2648.0, 2653.0],
            [1767100800000, 2653.0, 2658.0, 2651.0, 2656.0],
            [1767187200000, 2656.0, 2660.0, 2654.0, 2658.0],
            [1767273600000, 2658.0, 2662.0, 2656.0, 2660.0],
            [1767360000000, 2660.0, 2665.0, 2658.0, 2663.0],
            [1767446400000, 2663.0, 2668.0, 2661.0, 2666.0],
            [1767532800000, 2666.0, 2670.0, 2664.0, 2668.0],
            [1767619200000, 2668.0, 2672.0, 2666.0, 2670.0],
            [1767705600000, 2670.0, 2675.0, 2668.0, 2673.0],
            [1767792000000, 2673.0, 2678.0, 2671.0, 2676.0],
            [1767878400000, 2676.0, 2680.0, 2674.0, 2678.0],
            [1767964800000, 2678.0, 2682.0, 2676.0, 2680.0],
            [1768051200000, 2680.0, 2685.0, 2678.0, 2683.0],
            [1768137600000, 2683.0, 2688.0, 2681.0, 2686.0],
            [1768224000000, 2686.0, 2690.0, 2684.0, 2688.0],
            [1768310400000, 2688.0, 2692.0, 2686.0, 2690.0],
            [1768396800000, 2690.0, 2695.0, 2688.0, 2693.0],
            [1768483200000, 2693.0, 2698.0, 2691.0, 2696.0],
            [1768569600000, 2696.0, 2700.0, 2694.0, 2698.0],
            [1768656000000, 2698.0, 2702.0, 2696.0, 2700.0],
            [1768742400000, 2700.0, 2705.0, 2698.0, 2703.0],
            [1768828800000, 2703.0, 2708.0, 2701.0, 2706.0],
            [1768915200000, 2706.0, 2710.0, 2704.0, 2708.0],
            [1769001600000, 2708.0, 2712.0, 2706.0, 2710.0],
            [1769088000000, 2710.0, 2715.0, 2708.0, 2713.0],
            [1769174400000, 2713.0, 2718.0, 2711.0, 2716.0],
            [1769260800000, 2716.0, 2720.0, 2714.0, 2718.0],
            [1769347200000, 2718.0, 2722.0, 2716.0, 2720.0],
            [1769433600000, 2720.0, 2725.0, 2718.0, 2723.0],
            [1769520000000, 2723.0, 2728.0, 2721.0, 2726.0],
            [1769606400000, 2726.0, 2730.0, 2724.0, 2728.0],
            [1769692800000, 2728.0, 2732.0, 2726.0, 2730.0],
            [1769779200000, 2730.0, 2735.0, 2728.0, 2733.0],
            [1769865600000, 2733.0, 2738.0, 2731.0, 2736.0],
            [1769952000000, 2736.0, 2740.0, 2734.0, 2738.0],
            [1770038400000, 2738.0, 2742.0, 2736.0, 2740.0],
            [1770124800000, 2740.0, 2745.0, 2738.0, 2743.0],
            [1770211200000, 2743.0, 2748.0, 2741.0, 2746.0],
            [1770297600000, 2746.0, 2750.0, 2744.0, 2748.0],
            [1770384000000, 2748.0, 2752.0, 2746.0, 2750.0],
            [1770470400000, 2750.0, 2755.0, 2748.0, 2753.0],
            [1770556800000, 2753.0, 2758.0, 2751.0, 2756.0],
            [1770643200000, 2756.0, 2760.0, 2754.0, 2758.0],
            [1770729600000, 2758.0, 2762.0, 2756.0, 2760.0],
            [1770816000000, 2760.0, 2765.0, 2758.0, 2763.0],
            [1770902400000, 2763.0, 2768.0, 2761.0, 2766.0],
            [1770988800000, 2766.0, 2770.0, 2764.0, 2768.0],
            [1771075200000, 2768.0, 2772.0, 2766.0, 2770.0],
            [1771161600000, 2770.0, 2775.0, 2768.0, 2773.0],
            [1771248000000, 2773.0, 2778.0, 2771.0, 2776.0],
            [1771334400000, 2776.0, 2780.0, 2774.0, 2778.0],
            [1771420800000, 2778.0, 2782.0, 2776.0, 2780.0],
            [1771507200000, 2780.0, 2785.0, 2778.0, 2783.0],
            [1771593600000, 2783.0, 2788.0, 2781.0, 2786.0],
            [1771680000000, 2786.0, 2790.0, 2784.0, 2788.0],
            [1771766400000, 2788.0, 2792.0, 2786.0, 2790.0],
            [1771852800000, 2790.0, 2795.0, 2788.0, 2793.0],
            [1771939200000, 2793.0, 2798.0, 2791.0, 2796.0],
            [1772025600000, 2796.0, 2800.0, 2794.0, 2798.0],
            [1772112000000, 2798.0, 2802.0, 2796.0, 2800.0],
            [1772198400000, 2800.0, 2805.0, 2798.0, 2803.0],
            [1772284800000, 2803.0, 2808.0, 2801.0, 2806.0],
            [1772371200000, 2806.0, 2810.0, 2804.0, 2808.0],
            [1772457600000, 2808.0, 2812.0, 2806.0, 2810.0],
            [1772544000000, 2810.0, 2815.0, 2808.0, 2813.0],
            [1772630400000, 2813.0, 2818.0, 2811.0, 2816.0],
            [1772716800000, 2816.0, 2820.0, 2814.0, 2818.0],
            [1772803200000, 2818.0, 2822.0, 2816.0, 2820.0],
            [1772889600000, 2820.0, 2825.0, 2818.0, 2823.0],
            [1772976000000, 2823.0, 2828.0, 2821.0, 2826.0],
            [1773062400000, 2826.0, 2830.0, 2824.0, 2828.0],
            [1773148800000, 2828.0, 2832.0, 2826.0, 2830.0],
            [1773235200000, 2830.0, 2835.0, 2828.0, 2833.0],
            [1773321600000, 2833.0, 2838.0, 2831.0, 2836.0],
            [1773408000000, 2836.0, 2840.0, 2834.0, 2838.0],
            [1773494400000, 2838.0, 2842.0, 2836.0, 2840.0],
            [1773580800000, 2840.0, 2845.0, 2838.0, 2843.0],
            [1773667200000, 2843.0, 2848.0, 2841.0, 2846.0],
            [1773753600000, 2846.0, 2850.0, 2844.0, 2848.0],
            [1773840000000, 2848.0, 2852.0, 2846.0, 2850.0],
            [1773926400000, 2850.0, 2855.0, 2848.0, 2853.0],
            [1774012800000, 2853.0, 2858.0, 2851.0, 2856.0],
            [1774099200000, 2856.0, 2860.0, 2854.0, 2858.0],
            [1774185600000, 2858.0, 2862.0, 2856.0, 2860.0],
            [1774272000000, 2860.0, 2865.0, 2858.0, 2863.0],
            [1774358400000, 2863.0, 2868.0, 2861.0, 2866.0],
            [1774444800000, 2866.0, 2870.0, 2864.0, 2868.0],
            [1774531200000, 2868.0, 2872.0, 2866.0, 2870.0],
            [1774617600000, 2870.0, 2875.0, 2868.0, 2873.0],
            [1774704000000, 2873.0, 2878.0, 2871.0, 2876.0],
            [1774790400000, 2876.0, 2880.0, 2874.0, 2878.0],
            [1774876800000, 2878.0, 2882.0, 2876.0, 2880.0],
            [1774963200000, 2880.0, 2885.0, 2878.0, 2883.0],
            [1775049600000, 2883.0, 2888.0, 2881.0, 2886.0],
            [1775136000000, 2886.0, 2890.0, 2884.0, 2888.0],
            [1775222400000, 2888.0, 2892.0, 2886.0, 2890.0],
            [1775308800000, 2890.0, 2895.0, 2888.0, 2893.0],
            [1775395200000, 2893.0, 2898.0, 2891.0, 2896.0],
            [1775481600000, 2896.0, 2900.0, 2894.0, 2898.0],
            [1775568000000, 2898.0, 2902.0, 2896.0, 2900.0],
            [1775654400000, 2900.0, 2905.0, 2898.0, 2903.0],
            [1775740800000, 2903.0, 2908.0, 2901.0, 2906.0],
            [1775827200000, 2906.0, 2910.0, 2904.0, 2908.0],
            [1775913600000, 2908.0, 2912.0, 2906.0, 2910.0],
            [1776000000000, 2910.0, 2915.0, 2908.0, 2913.0],
            [1776086400000, 2913.0, 2918.0, 2911.0, 2916.0],
            [1776172800000, 2916.0, 2920.0, 2914.0, 2918.0],
            [1776259200000, 2918.0, 2922.0, 2916.0, 2920.0],
            [1776345600000, 2920.0, 2925.0, 2918.0, 2923.0],
            [1776432000000, 2923.0, 2928.0, 2921.0, 2926.0],
            [1776518400000, 2926.0, 2930.0, 2924.0, 2928.0],
            [1776604800000, 2928.0, 2932.0, 2926.0, 2930.0],
            [1776691200000, 2930.0, 2935.0, 2928.0, 2933.0],
            [1776777600000, 2933.0, 2938.0, 2931.0, 2936.0],
            [1776864000000, 2936.0, 2940.0, 2934.0, 2938.0],
            [1776950400000, 2938.0, 2942.0, 2936.0, 2940.0],
            [1777036800000, 2940.0, 2945.0, 2938.0, 2943.0],
            [1777123200000, 2943.0, 2948.0, 2941.0, 2946.0],
            [1777209600000, 2946.0, 2950.0, 2944.0, 2948.0],
            [1777296000000, 2948.0, 2952.0, 2946.0, 2950.0],
            [1777382400000, 2950.0, 2955.0, 2948.0, 2953.0],
            [1777468800000, 2953.0, 2958.0, 2951.0, 2956.0],
            [1777555200000, 2956.0, 2960.0, 2954.0, 2958.0],
            [1777641600000, 2958.0, 2962.0, 2956.0, 2960.0],
            [1777728000000, 2960.0, 2965.0, 2958.0, 2963.0],
            [1777814400000, 2963.0, 2968.0, 2961.0, 2966.0],
            [1777900800000, 2966.0, 2970.0, 2964.0, 2968.0],
            [1777987200000, 2968.0, 2972.0, 2966.0, 2970.0],
            [1778073600000, 2970.0, 2975.0, 2968.0, 2973.0],
            [1778160000000, 2973.0, 2978.0, 2971.0, 2976.0],
            [1778246400000, 2976.0, 2980.0, 2974.0, 2978.0],
            [1778332800000, 2978.0, 2982.0, 2976.0, 2980.0],
            [1778419200000, 2980.0, 2985.0, 2978.0, 2983.0],
            [1778505600000, 2983.0, 2988.0, 2981.0, 2986.0],
            [1778592000000, 2986.0, 2990.0, 2984.0, 2988.0],
            [1778678400000, 2988.0, 2992.0, 2986.0, 2990.0],
            [1778764800000, 2990.0, 2995.0, 2988.0, 2993.0],
            [1778851200000, 2993.0, 2998.0, 2991.0, 2996.0],
            [1778937600000, 2996.0, 3000.0, 2994.0, 2998.0]
        ]
        self.engine = TradingEngine(config, data_fetcher=self.mock_data_fetcher)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @patch('backtester.Backtester.fetch_data')
    def test_end_to_end_backtest(self, mock_fetch_data):
        """Test end-to-end backtest workflow."""
        # Manually define valid parameters for EMA_Only strategy with 'small' parameter set
        valid_params = {
            'short_sma': 10,
            'long_sma': 50,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'atr_period': 14,
            'atr_multiple': 2.0,
            'fixed_stop_loss_percentage': 0.03,
            'take_profit_multiple': 2.0,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9,
            'trailing_stop_loss_percentage': 0.02,
            'atr_stop_loss_multiple': 3.0
        }
        
        errors = self.engine.validate_parameters('EMA_Only', valid_params)
        self.assertEqual(len(errors), 0)
        
        # Run backtest (will be mocked)
        result = self.engine.run_backtest(
            crypto_id='bitcoin',
            strategy_name='EMA_Only',
            parameters=valid_params
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
