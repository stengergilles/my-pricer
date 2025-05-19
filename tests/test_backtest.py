import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call, ANY
from typing import List, Dict, Any, Optional, Type
import numpy as np

import importlib
import inspect
import math

# Assuming 'tests' directory is at the same level as 'stock_monitoring_app'
# or the project root containing 'stock_monitoring_app' is in PYTHONPATH.
from stock_monitoring_app.backtest.backtest import BackTest
from stock_monitoring_app.fetchers.base_fetcher import Fetcher
from stock_monitoring_app.fetchers import CoinGeckoFetcher, PolygonFetcher
from stock_monitoring_app.strategies.base_strategy import BaseStrategy, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from stock_monitoring_app.indicators.base_indicator import Indicator

from stock_monitoring_app.indicators.rsi_indicator import RSIIndicator
from stock_monitoring_app.indicators.bollinger_bands_indicator import BollingerBandsIndicator
from stock_monitoring_app.indicators.breakout_indicator import BreakoutIndicator

from pathlib import Path # Added for save_results tests
import json            # Added for save_results tests
from datetime import datetime as dt # Added for save_results tests, aliased as dt

# --- Mock Indicator classes for testing discovery ---
class MockIndicatorAlpha(Indicator):


    def __init__(self, params: Optional[Dict] = None):
        super().__init__(df=pd.DataFrame(), **(params or {}))
        self.name = "MockIndicatorAlpha"

    def calculate(self) -> pd.DataFrame:        # The 'data' parameter was removed to match the base Indicator class.
        # Calculations now use self.df, assuming it's populated appropriately.
        self.df[f'{self.name}_Signal'] = SIGNAL_HOLD # Example signal
        return self.df
        return data
    def get_signals(self, data: pd.DataFrame) -> pd.Series:
        return data[f'{self.name}_Signal']

class MockIndicatorBeta(Indicator):



    def __init__(self, params: Optional[Dict] = None):
        super().__init__(df=pd.DataFrame(), **(params or {}))
        self.name = "MockIndicatorBeta"

    def calculate(self) -> pd.DataFrame:
        # The 'data' parameter was removed to match the base Indicator class.
        # Calculations now use self.df, assuming it's populated appropriately.
        self.df[f'{self.name}_Signal'] = SIGNAL_BUY # Example signal
        return self.df
    def get_signals(self, data: pd.DataFrame) -> pd.Series:
        return data[f'{self.name}_Signal']# --- Pytest Fixtures ---


@pytest.fixture
def sample_ohlcv_data_fixture():
    data = {
        'Timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06', '2023-01-07']),
        'Open': [100, 102, 101, 105, 103, 98, 100],
        'High': [103, 104, 106, 107, 105, 100, 102],
        'Low': [99, 101, 100, 103, 102, 97, 99],
        'Close': [102, 103, 105, 104, 103, 99, 101],
        'Volume': [1000, 1100, 1200, 1050, 1300, 900, 1050]
    }
    df = pd.DataFrame(data)
    df.set_index('Timestamp', inplace=True)
    return df


@pytest.fixture
def backtest_stock_instance_fixture():
    with patch('stock_monitoring_app.backtest.backtest.PolygonFetcher') as MockPolygonFetcher, \
         patch('stock_monitoring_app.backtest.backtest.CoinGeckoFetcher') as MockCoinGeckoFetcher:
        mock_polygon_fetcher_instance = MockPolygonFetcher.return_value
        mock_polygon_fetcher_instance.get_service_name.return_value = "PolygonMock"
        
        mock_coingecko_fetcher_instance = MockCoinGeckoFetcher.return_value # Not used by stock
        
        # Test with a default leverage for stock that is not 1.0
        bt = BackTest(ticker="AAPL", period="1mo", interval="1d", leverage=2.0)
        bt.fetcher = mock_polygon_fetcher_instance # Ensure it's set for tests
        return bt


@pytest.fixture
def backtest_crypto_instance_fixture():
    with patch('stock_monitoring_app.backtest.backtest.PolygonFetcher') as MockPolygonFetcher, \
         patch('stock_monitoring_app.backtest.backtest.CoinGeckoFetcher') as MockCoinGeckoFetcher:
        mock_coingecko_fetcher_instance = MockCoinGeckoFetcher.return_value
        mock_coingecko_fetcher_instance.get_service_name.return_value = "CoinGeckoMock"

        mock_polygon_fetcher_instance = MockPolygonFetcher.return_value # Not used by crypto
        
        # Test with a leverage that should be overridden for crypto
        bt = BackTest(ticker="bitcoin", period="1mo", interval="1d", leverage=5.0)        
        bt.fetcher = mock_coingecko_fetcher_instance # Ensure it's set for tests
        return bt

# --- Test Class for BackTest ---

class TestBackTest:

    def test_init_and_get_fetcher_stock(self):
        with patch('stock_monitoring_app.backtest.backtest.PolygonFetcher') as MockPolygonFetcher:
            mock_fetcher_instance = MockPolygonFetcher.return_value
            bt = BackTest(ticker="MSFT", period="1y", interval="1d", leverage=10.0)
            assert bt.ticker == "MSFT"
            assert bt.leverage == 10.0
            assert not bt._is_crypto
            assert bt.fetcher is mock_fetcher_instance
            MockPolygonFetcher.assert_called_once()

    def test_init_and_get_fetcher_crypto(self):
        with patch('stock_monitoring_app.backtest.backtest.CoinGeckoFetcher') as MockCoinGeckoFetcher:
            mock_fetcher_instance = MockCoinGeckoFetcher.return_value
            bt = BackTest(ticker="ethereum", period="1y", interval="1d", leverage=10.0) # Leverage should be overridden
            assert bt.ticker == "ethereum"
            assert bt.leverage == 1.0 # Crypto leverage is always 1.0            assert bt._is_crypto
            assert bt.fetcher is mock_fetcher_instance
            MockCoinGeckoFetcher.assert_called_once()

    def test_init_leverage_clamping_too_high(self, capsys):
        with patch('stock_monitoring_app.backtest.backtest.PolygonFetcher'):
            bt = BackTest(ticker="STOCK", period="1d", interval="1h", leverage=25.0)
            assert bt.leverage == 20.0
            captured = capsys.readouterr()
            assert "WARNING: Leverage 25.0 for 'STOCK' exceeds maximum 20.0. Clamping to 20.0." in captured.out

    def test_init_leverage_clamping_too_low(self, capsys):
        with patch('stock_monitoring_app.backtest.backtest.PolygonFetcher'):
            bt = BackTest(ticker="STOCK", period="1d", interval="1h", leverage=0.5)
            assert bt.leverage == 1.0
            captured = capsys.readouterr()
            assert "WARNING: Leverage 0.5 for 'STOCK' is below minimum 1.0. Clamping to 1.0." in captured.out            

    def test_init_leverage_crypto_override(self, capsys):
        with patch('stock_monitoring_app.backtest.backtest.CoinGeckoFetcher'):
            bt = BackTest(ticker="bitcoin", period="1d", interval="1h", leverage=10.0)
            assert bt.leverage == 1.0
            captured = capsys.readouterr()
            assert "INFO: Leverage for crypto asset 'bitcoin' is always 1.0. Overriding provided leverage 10.0." in captured.out

    def test_fetch_historical_data_success(self, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture

        # Replace bt.fetcher.fetch_data with a new MagicMock to control its behavior
        bt.fetcher.fetch_data = MagicMock(return_value=sample_ohlcv_data_fixture)
        
        data = bt.fetch_historical_data()
        
        bt.fetcher.fetch_data.assert_called_once_with("AAPL", "1mo", "1d")
        assert data is not None        
        pd.testing.assert_frame_equal(data, sample_ohlcv_data_fixture)
        assert bt.historical_data is data

    def test_fetch_historical_data_failure_exception(self, backtest_stock_instance_fixture: BackTest):

        bt = backtest_stock_instance_fixture        
        # Replace bt.fetcher.fetch_data with a new MagicMock to control its behavior
        bt.fetcher.fetch_data = MagicMock(side_effect=Exception("API Error"))
        
        data = bt.fetch_historical_data()
        
        bt.fetcher.fetch_data.assert_called_once_with("AAPL", "1mo", "1d")
        assert data is not None        







        assert data.empty
        assert bt.historical_data is not None
        assert bt.historical_data.empty # SUT sets self.historical_data to an empty DataFrame on exception


    def test_fetch_historical_data_no_data_returned(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture
        # Replace bt.fetcher.fetch_data with a new MagicMock to control its behavior
        bt.fetcher.fetch_data = MagicMock(return_value=pd.DataFrame())
        

        data = bt.fetch_historical_data()
        assert data is not None





        assert data.empty    
        assert bt.historical_data is not None   
        assert bt.historical_data.empty # SUT sets self.historical_data to an empty DataFrame if fetcher returns empty

    @patch('importlib.import_module')
    @patch('inspect.getmembers')
    def test_determine_relevant_indicators_success(self, mock_getmembers, mock_import_module, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        mock_module = MagicMock()
        mock_import_module.return_value = mock_module
        
        mock_getmembers.return_value = [
            ('MockIndicatorAlpha', MockIndicatorAlpha),
            ('MockIndicatorBeta', MockIndicatorBeta),
            ('BaseIndicator', Indicator), 
            ('some_other_function', lambda x: x)
        ]
        
        configs = bt.determine_relevant_indicators(sample_ohlcv_data_fixture)
        
        mock_import_module.assert_called_once_with("stock_monitoring_app.indicators")
        mock_getmembers.assert_called_once_with(mock_module)
        assert len(configs) == 2        
        assert {'type': MockIndicatorAlpha, 'params': {}} in configs
        assert {'type': MockIndicatorBeta, 'params': {}} in configs
        assert bt.current_indicator_configs == configs

    @patch('importlib.import_module')
    def test_determine_relevant_indicators_import_error(self, mock_import_module, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        mock_import_module.side_effect = ImportError("Module not found")
        
        configs = bt.determine_relevant_indicators(sample_ohlcv_data_fixture)
        assert len(configs) == 0
        assert bt.current_indicator_configs == []

    @patch('importlib.import_module')
    @patch('inspect.getmembers')
    def test_determine_relevant_indicators_no_indicators_found(self, mock_getmembers, mock_import_module, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        mock_module = MagicMock()
        mock_import_module.return_value = mock_module
        mock_getmembers.return_value = [('BaseIndicator', Indicator), ('some_function', lambda x:x)]
        
        configs = bt.determine_relevant_indicators(sample_ohlcv_data_fixture)
        assert len(configs) == 0


    def test_calculate_placeholder_pnl(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture
        # Default leverage for backtest_stock_instance_fixture is 2.0
        # Original PNL = (105-102) + (108-103) = 3 + 5 = 8
        # Leveraged PNL = 8 * 2.0 = 16.0
        data = {
            'Close': [100, 102, 101, 105, 103, 108],
            'Strategy_Signal': [SIGNAL_HOLD, SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL, SIGNAL_BUY, SIGNAL_SELL]
        }
        results_df = pd.DataFrame(data)
        pnl = bt._calculate_placeholder_pnl(results_df)
        assert pnl == pytest.approx(16.0) # Expected: 8.0 * 2.0 (leverage from fixture)

        bt.leverage = 1.0 # Test with leverage 1
        pnl_no_leverage = bt._calculate_placeholder_pnl(results_df)
        assert pnl_no_leverage == pytest.approx(8.0)
        
        bt.leverage = 3.0 # Test with different leverage
        pnl_other_leverage = bt._calculate_placeholder_pnl(results_df)        
        assert pnl_other_leverage == pytest.approx(24.0) # Expected: 8.0 * 3.0

        pnl_empty = bt._calculate_placeholder_pnl(pd.DataFrame())
        assert pnl_empty == -float('inf')

        pnl_no_trades = bt._calculate_placeholder_pnl(pd.DataFrame({'Close': [1,2], 'Strategy_Signal': [SIGNAL_HOLD, SIGNAL_HOLD]}))
        assert pnl_no_trades == 0.0
        
        pnl_open_trade = bt._calculate_placeholder_pnl(pd.DataFrame({'Close': [1,2], 'Strategy_Signal': [SIGNAL_BUY, SIGNAL_HOLD]}))
        assert pnl_open_trade == 0.0 # Only closed trades contribute


    def test_calculate_placeholder_pnl_with_short_positions(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture
        # Default leverage for backtest_stock_instance_fixture is 2.0
        # Original PNL = (102-105) + (103-98) = -3 + 5 = 2
        # Leveraged PNL = 2 * 2.0 = 4.0
        data = {
            'Close': [100, 102, 101, 105, 103, 98],
            'Strategy_Signal': [SIGNAL_HOLD, SIGNAL_SELL, SIGNAL_HOLD, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_BUY]
        }
        results_df = pd.DataFrame(data)
        pnl = bt._calculate_placeholder_pnl(results_df)
        assert pnl == pytest.approx(4.0) # Expected 2.0 * 2.0 (leverage from fixture)

        bt.leverage = 1.0 # Test with leverage 1
        pnl_no_leverage = bt._calculate_placeholder_pnl(results_df)
        assert pnl_no_leverage == pytest.approx(2.0)

        bt.leverage = 0.5 # Test if clamping works during PNL calc if leverage somehow got below 1 after init (though init should prevent this)
                          # For this test, assume leverage can be set post-init. The PNL calc itself doesn't re-clamp.
                          # To truly test clamping's effect on PNL, we'd need to re-init.
                          # Here, we just test if _calculate_placeholder_pnl uses the current self.leverage.
        pnl_other_leverage = bt._calculate_placeholder_pnl(results_df)
        assert pnl_other_leverage == pytest.approx(1.0) # Expected 2.0 * 0.5

    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')    
    def test_optimize_thresholds_flow(self, MockBaseStrategy, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        
        mock_strategy_instance = MockBaseStrategy.return_value
        # Simulate strategy run results
        mock_strategy_instance.run.return_value = pd.DataFrame({'Close': [1,2], 'Strategy_Signal': [SIGNAL_BUY, SIGNAL_SELL]}) 
        
        pnl_call_count = 0
        def mock_pnl_calculator(df): # Simulate PNL increasing with trials
            nonlocal pnl_call_count
            pnl_call_count += 1
            return float(pnl_call_count) 

        # Patch the internal _calculate_placeholder_pnl
        with patch.object(bt, '_calculate_placeholder_pnl', side_effect=mock_pnl_calculator) as mock_calc_pnl:
            initial_configs = [
                {'type': RSIIndicator, 'params': {}}, 
                {'type': BollingerBandsIndicator, 'params': {}},
                {'type': BreakoutIndicator, 'params': {}},
                {'type': MockIndicatorAlpha, 'params': {}} # No specific opt. logic
            ]
            
            optimized_configs = bt.optimize_thresholds(sample_ohlcv_data_fixture, initial_configs)
            
            assert len(optimized_configs) == 4
            assert MockBaseStrategy.call_count > len(initial_configs) # Base + trials
            assert mock_calc_pnl.call_count > len(initial_configs)

            # RSI: 1 baseline + 3*3*3 trials = 28 calls
            # BB: 1 baseline + 3*3 trials = 10 calls
            # Breakout: 1 baseline + 3 trials = 4 calls
            # MockIndicatorAlpha: 1 baseline call            # Total expected PNL calls = 28 + 10 + 4 + 1 = 43
            assert mock_calc_pnl.call_count == 43 
            
            rsi_opt_config = next(c for c in optimized_configs if c['type'] == RSIIndicator)
            assert rsi_opt_config['params'] != {} # Should have "optimized" params
            assert 'period' in rsi_opt_config['params']

            bb_opt_config = next(c for c in optimized_configs if c['type'] == BollingerBandsIndicator)
            assert 'window' in bb_opt_config['params']
            
            bo_opt_config = next(c for c in optimized_configs if c['type'] == BreakoutIndicator)
            assert 'window' in bo_opt_config['params']

            mock_alpha_opt_config = next(c for c in optimized_configs if c['type'] == MockIndicatorAlpha)
            assert mock_alpha_opt_config['params'] == {} # Default params as no opt logic

    def test_optimize_thresholds_empty_data_or_configs(self, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        initial_configs = [{'type': RSIIndicator, 'params': {}}]        
        optimized_empty_data = bt.optimize_thresholds(pd.DataFrame(), initial_configs)
        assert optimized_empty_data == initial_configs

        optimized_empty_configs = bt.optimize_thresholds(sample_ohlcv_data_fixture, [])
        assert optimized_empty_configs == []

    @patch('stock_monitoring_app.backtest.backtest.BackTest.fetch_historical_data')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.optimize_thresholds')
    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')

    @patch('stock_monitoring_app.backtest.backtest.BackTest.evaluate_performance')
    def test_run_backtest_success_flow(self, mock_eval_perf, MockBaseStrategy, mock_opt_thresh, mock_det_ind, mock_fetch_data, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        
        # Setup mocks
        mock_fetch_data.return_value = sample_ohlcv_data_fixture
        bt.historical_data = sample_ohlcv_data_fixture # Pre-set for this test path
        
        discovered_configs = [{'type': MockIndicatorAlpha, 'params': {}}]
        mock_det_ind.return_value = discovered_configs
        

        optimized_configs = [{'type': MockIndicatorAlpha, 'params': {'optimized': True}}]
        mock_opt_thresh.return_value = optimized_configs
        mock_strategy_instance = MockBaseStrategy.return_value

        # This is what the strategy.run() mock should return (before portfolio columns are added)
        mock_df_from_strategy_run = sample_ohlcv_data_fixture.copy()
        mock_df_from_strategy_run['Strategy_Signal'] = SIGNAL_HOLD 
        mock_strategy_instance.run.return_value = mock_df_from_strategy_run        
        # This is the expected final DataFrame after run_backtest adds portfolio columns
        expected_final_results_df = mock_df_from_strategy_run.copy()
        expected_final_results_df['Shares_Held'] = 0.0
        expected_final_results_df['Cash_Balance'] = bt.initial_capital # Default is 10000.0
        expected_final_results_df['Portfolio_Value'] = bt.initial_capital
        expected_final_results_df['Trade_Action'] = ""
        
        mock_eval_perf.return_value = {"net_profit": 100} # Simulate eval result

        # Run
        results = bt.run_backtest()        
        # Assertions
        mock_fetch_data.assert_not_called() # Data was pre-set
        mock_det_ind.assert_called_once_with(sample_ohlcv_data_fixture)
        mock_opt_thresh.assert_called_once_with(sample_ohlcv_data_fixture, discovered_configs)
        MockBaseStrategy.assert_called_once_with(indicator_configs=optimized_configs)
        mock_strategy_instance.run.assert_called_once() 
        # Check that the argument to strategy.run is a copy of historical_data
        pd.testing.assert_frame_equal(mock_strategy_instance.run.call_args[0][0], sample_ohlcv_data_fixture)
        assert id(mock_strategy_instance.run.call_args[0][0]) != id(sample_ohlcv_data_fixture)

        mock_eval_perf.assert_called_once()
        
        assert results is not None
        # Compare the final 'results' DataFrame with the 'expected_final_results_df'
        pd.testing.assert_frame_equal(results, expected_final_results_df)

        assert bt.results is results

        # Manually set performance_metrics as evaluate_performance is mocked
        bt.performance_metrics = mock_eval_perf.return_value 
        # The mock_eval_perf.return_value should ideally include "leverage_applied": bt.leverage
        # For this test, if mock_eval_perf is very simple, we just check what it returned.
        # If mock_eval_perf was more sophisticated or we were testing the actual evaluate_performance,
        # we'd expect "leverage_applied" to be in the dict.
        # Let's update the mock_eval_perf.return_value for this test to be more complete.
        expected_perf_metrics = {"net_profit": 100, "leverage_applied": bt.leverage}
        mock_eval_perf.return_value = expected_perf_metrics        # Re-run to capture the updated mock_eval_perf return value
        results = bt.run_backtest() # This will call the mocked evaluate_performance
        bt.performance_metrics = mock_eval_perf.return_value # Ensure bt state reflects the mock
        
        assert bt.get_performance_metrics() == expected_perf_metrics


    def test_run_backtest_fetch_data_path(self, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        # Ensure historical_data is None initially to trigger fetch
        bt.historical_data = None 
        
        with patch.object(bt, 'fetch_historical_data', return_value=sample_ohlcv_data_fixture) as mock_fetch, \
             patch.object(bt, 'determine_relevant_indicators', return_value=[{'type': MockIndicatorAlpha, 'params': {}}]) as mock_det, \
             patch.object(bt, 'optimize_thresholds', side_effect=lambda d, c: c) as mock_opt, \
             patch('stock_monitoring_app.backtest.backtest.BaseStrategy') as MockStrategy, \
             patch.object(bt, 'evaluate_performance') as mock_eval:
            
            mock_strategy_instance = MockStrategy.return_value
            mock_strategy_instance.run.return_value = sample_ohlcv_data_fixture # Dummy results

            bt.run_backtest()
            mock_fetch.assert_called_once()    
    def test_run_backtest_no_data_after_fetch(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture
        bt.historical_data = None
        with patch.object(bt, 'fetch_historical_data', return_value=pd.DataFrame()) as mock_fetch:
            results = bt.run_backtest()
            mock_fetch.assert_called_once()

            assert results is None
            assert bt.results is None

    @patch('stock_monitoring_app.backtest.backtest.BackTest.evaluate_performance')
    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.optimize_thresholds')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.fetch_historical_data')
    def test_run_backtest_when_historical_data_is_already_empty(self,
                                                               mock_fetch_data,
                                                               mock_det_ind,
                                                               mock_opt_thresh,
                                                               MockBaseStrategy,
                                                               mock_eval_perf,
                                                               backtest_stock_instance_fixture: BackTest):
        """
        Tests that run_backtest handles pre-existing empty historical_data correctly.
        It should not attempt to fetch data again and should skip all processing.
        """
        bt = backtest_stock_instance_fixture
        bt.historical_data = pd.DataFrame() # Set historical_data to an empty DataFrame

        results = bt.run_backtest()

        assert results is None, "Results should be None when historical_data is initially empty"

        assert bt.results is None, "bt.results attribute should be None"
        
        # Configure mock_fetch_data to return empty, simulating fetch yielding no new data
        mock_fetch_data.return_value = pd.DataFrame()
        
        # mock_fetch_data should be called if historical_data is initially empty
        mock_fetch_data.assert_called_once() 
        mock_det_ind.assert_not_called()       
        mock_opt_thresh.assert_not_called()
        MockBaseStrategy.assert_not_called()
        mock_eval_perf.assert_not_called()

    @patch('stock_monitoring_app.backtest.backtest.BackTest.evaluate_performance')
    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.optimize_thresholds')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators')
    @patch.object(BackTest, 'fetch_historical_data') # Patching on the class to mock the instance method
    def test_run_backtest_no_data_after_fetch_explicitly_skips_processing(self,
                                                                        mock_fetch_data_method,
                                                                        mock_det_ind,
                                                                        mock_opt_thresh,
                                                                        MockBaseStrategy,
                                                                        mock_eval_perf,
                                                                        backtest_stock_instance_fixture: BackTest):
        """
        Tests that run_backtest skips processing steps if fetch_historical_data returns no data.
        This is an enhancement of the existing test_run_backtest_no_data_after_fetch
        by explicitly checking that downstream methods are not called.
        """
        bt = backtest_stock_instance_fixture
        bt.historical_data = None # Ensure fetch_historical_data is called        # Configure the mock for the instance method fetch_historical_data
        mock_fetch_data_method.return_value = pd.DataFrame()

        results = bt.run_backtest()

        assert results is None, "Results should be None when fetched data is empty"
        assert bt.results is None, "bt.results attribute should be None"

        mock_fetch_data_method.assert_called_once()
        mock_det_ind.assert_not_called()
        mock_opt_thresh.assert_not_called()
        MockBaseStrategy.assert_not_called()
        mock_eval_perf.assert_not_called()

    @patch('stock_monitoring_app.backtest.backtest.BackTest.fetch_historical_data')
    def test_run_backtest_no_indicators_discovered(self, mock_fetch_data, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        bt.historical_data = sample_ohlcv_data_fixture # Simulate data is present
        mock_fetch_data.return_value = sample_ohlcv_data_fixture        
        with patch.object(bt, 'determine_relevant_indicators', return_value=[]) as mock_det_ind:
            results = bt.run_backtest()
            mock_det_ind.assert_called_once()
            assert results is None

    def test_evaluate_performance_no_results(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture
        bt.results = None
        metrics = bt.evaluate_performance()
        assert metrics == {}

        bt.results = pd.DataFrame()
        metrics_empty_df = bt.evaluate_performance()
        assert metrics_empty_df == {}
        

    def test_evaluate_performance_missing_columns(self, backtest_stock_instance_fixture: BackTest):

        bt = backtest_stock_instance_fixture
        bt.historical_data = pd.DataFrame({'SomeData': [1,2,3]}) # For total_data_points
        # Ensure 'Close' is present, but 'Strategy_Signal' is missing
        bt.results = pd.DataFrame({'Close': [10,11,12]}) 
        
        # Test that evaluate_performance raises KeyError when 'Strategy_Signal' is missing
        with pytest.raises(KeyError, match="'Strategy_Signal'"):
            bt.evaluate_performance()


    def test_evaluate_performance_detailed_metrics(self, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture # Ticker AAPL, leverage = 2.0 from fixture
        bt.historical_data = sample_ohlcv_data_fixture.iloc[:6].copy()
        
        # Original PNLs:
        # Trade 1 (long): Buy at 100, Sell at 110 -> PNL_per_share = +10
        # Trade 2 (long): Buy at 105, Sell at 100 -> PNL_per_share = -5
        # Unleveraged Net PNL = 10 - 5 = 5
        # Leveraged Net PNL = 5 * 2.0 = 10.0
        results_data = {
            'Timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06']),
            'Close':         [90,  100,  110,  108,  105,  100], 
            'Strategy_Signal': [SIGNAL_HOLD, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD, SIGNAL_BUY, SIGNAL_SELL]
        }        
        bt.results = pd.DataFrame(results_data).set_index('Timestamp')
        
        metrics = bt.evaluate_performance()
        
        current_leverage = bt.leverage # Should be 2.0 from fixture

        assert metrics["ticker"] == "AAPL"
        assert metrics["period_tested"] == "1mo"
        assert metrics["interval_tested"] == "1d"
        assert metrics["leverage_applied"] == current_leverage        
        assert metrics["total_data_points"] == 6
        assert metrics["total_signals_non_hold"] == 4
        assert metrics["num_buy_signals"] == 2
        assert metrics["num_sell_signals"] == 2
        assert metrics["total_trades"] == 2
        assert metrics["winning_trades"] == 1
        assert metrics["losing_trades"] == 1
        assert metrics["win_rate_pct"] == pytest.approx(50.0)
        
        assert metrics["net_profit"] == pytest.approx(5.0 * current_leverage) 
        assert metrics["gross_profit"] == pytest.approx(10.0 * current_leverage)
        assert metrics["gross_loss"] == pytest.approx(5.0 * current_leverage)
        assert metrics["avg_profit_per_winning_trade"] == pytest.approx(10.0 * current_leverage)
        assert metrics["avg_loss_per_losing_trade"] == pytest.approx(5.0 * current_leverage) 
        assert metrics["profit_factor"] == pytest.approx(2.0) # (10*L) / (5*L) = 10/5 = 2.0
        assert metrics["avg_pnl_per_trade"] == pytest.approx(2.5 * current_leverage)

        # Max Drawdown with leverage:
        # Initial equity: 10000
        # Trade 1 PNL (leveraged): +10 * 2.0 = +20. Equity: 10000 + 20 = 10020. Peak: 10020.
        # Trade 2 PNL (leveraged): -5 * 2.0 = -10. Equity: 10020 - 10 = 10010. Peak: 10020.
        # Drawdown from peak: 10020 - 10010 = 10.
        expected_max_drawdown_value = 5.0 * current_leverage # Max single loss trade * leverage
        # Peak equity for drawdown calc: 10000 + (10 * current_leverage)
        peak_equity_for_dd = 10000.0 + (10.0 * current_leverage)
        expected_max_drawdown_percentage = (expected_max_drawdown_value / peak_equity_for_dd) * 100 if peak_equity_for_dd > 0 else 0.0
        
        assert metrics["max_drawdown_value"] == pytest.approx(expected_max_drawdown_value)
        assert metrics["max_drawdown_percentage"] == pytest.approx(expected_max_drawdown_percentage, 2)

        # Simplified Sharpe Ratio: Unleveraged returns: +10/100 = 10%, -5/105 = -4.7619%
        # Leveraged returns: (+10*L)/100 = 10%*L, (-5*L)/105 = -4.7619%*L
        # Both mean and std dev of returns scale by L, so Sharpe ratio should be unchanged by leverage (for zero risk-free rate).
        unleveraged_trade_returns_pct = [(10/100)*100, (-5/105)*100] # Original returns per trade
        mean_ret_unleveraged = np.mean(unleveraged_trade_returns_pct)
        std_ret_unleveraged = np.std(unleveraged_trade_returns_pct)
        expected_sharpe = "N/A"
        if std_ret_unleveraged > 0 :
            expected_sharpe = round(mean_ret_unleveraged / std_ret_unleveraged, 3)        
            assert metrics["sharpe_ratio_simplified_per_trade"] == expected_sharpe
        


    def test_evaluate_performance_with_short_positions(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture # leverage = 2.0 from fixture        
        bt.historical_data = pd.DataFrame({
            'Close': [100, 102, 101, 105, 103, 98]  # Corrected indentation
        })


        # Original PNLs:
        # Short 102, Buy 105 (PNL_per_share = -3)
        # Short 103, Buy 98 (PNL_per_share = +5)
        # Unleveraged Net PNL = -3 + 5 = 2
        # Leveraged Net PNL = 2 * 2.0 (fixture leverage) = 4.0
        results_data = {
            'Close': [100, 102, 101, 105, 103, 98],
            'Strategy_Signal': [SIGNAL_HOLD, SIGNAL_SELL, SIGNAL_HOLD, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_BUY]
        }        
        bt.results = pd.DataFrame(results_data)
        current_leverage = bt.leverage # Should be 2.0 from fixture

        metrics = bt.evaluate_performance()

        assert metrics["leverage_applied"] == current_leverage
        assert metrics["net_profit"] == pytest.approx(2.0 * current_leverage)
        assert metrics["total_trades"] == 2
        assert metrics["winning_trades"] == 1
        assert metrics["losing_trades"] == 1
        assert metrics["gross_profit"] == pytest.approx(5.0 * current_leverage)
        assert metrics["gross_loss"] == pytest.approx(3.0 * current_leverage)
        assert metrics["avg_profit_per_winning_trade"] == pytest.approx(5.0 * current_leverage)
        assert metrics["avg_loss_per_losing_trade"] == pytest.approx(3.0 * current_leverage)
        assert metrics["profit_factor"] == pytest.approx((5.0 * current_leverage) / (3.0 * current_leverage) if (3.0 * current_leverage) > 0 else float('inf'))

        # Max Drawdown with leverage:
        # Initial equity: 10000
        # Trade 1 PNL (leveraged): -3 * 2.0 = -6. Equity: 10000 - 6 = 9994. Peak: 10000. Drawdown: 6.
        # Trade 2 PNL (leveraged): +5 * 2.0 = +10. Equity: 9994 + 10 = 10004. Peak: 10004 (or 10000 if we consider peak before this trade for prior DD)
        # Let's trace equity and peak:

        # Start: equity=10000, peak=10000, max_dd=0
        # Trade 1 (PNL -3 * L): equity = 10000 - 3*L. peak = 10000. drawdown = 3*L. max_dd=3*L.
        # Trade 2 (PNL +5 * L): equity = 10000 - 3*L + 5*L = 10000 + 2*L. peak becomes 10000 + 2*L (if 2*L > 0) or 10000.
        # If L=2, PNLs are -6 and +10.
        # Equity: 10000 -> 9994 (DD=6 from 10000) -> 10004 (DD=0 from new peak 10004)
        # Max DD Value is 6.
        expected_max_drawdown_value = abs(-3.0 * current_leverage) # Max single loss trade * leverage
        # Peak for this DD calc is initial capital if first trade is loss.
        peak_equity_for_dd = 10000.0 
        expected_max_drawdown_percentage = (expected_max_drawdown_value / peak_equity_for_dd) * 100 if peak_equity_for_dd > 0 and expected_max_drawdown_value > 0 else 0.0
        
        assert metrics["max_drawdown_value"] == pytest.approx(expected_max_drawdown_value)
        assert metrics["max_drawdown_percentage"] == pytest.approx(expected_max_drawdown_percentage, 2)

        # Sharpe ratio for short positions
        # Unleveraged PNLs: -3, +5. Entry prices: 102, 103
        # Returns: (-3/102)*100 = -2.941%, (+5/103)*100 = 4.854%
        unleveraged_trade_returns_pct_short = [(-3/102)*100, (5/103)*100]
        mean_ret_unleveraged_short = np.mean(unleveraged_trade_returns_pct_short)
        std_ret_unleveraged_short = np.std(unleveraged_trade_returns_pct_short)
        expected_sharpe_short = "N/A"
        if std_ret_unleveraged_short > 0:
            expected_sharpe_short = round(mean_ret_unleveraged_short / std_ret_unleveraged_short, 3)
        assert metrics["sharpe_ratio_simplified_per_trade"] == expected_sharpe_short


    def test_get_results(self, backtest_stock_instance_fixture: BackTest, sample_ohlcv_data_fixture: pd.DataFrame):
        bt = backtest_stock_instance_fixture
        bt.results = sample_ohlcv_data_fixture # Dummy results
        
        results_df = bt.get_results()
        assert results_df is not None, "get_results() should return a DataFrame in this test setup"
        pd.testing.assert_frame_equal(results_df, sample_ohlcv_data_fixture)
        assert results_df is sample_ohlcv_data_fixture




    def test_get_performance_metrics(self, backtest_stock_instance_fixture: BackTest):
        bt = backtest_stock_instance_fixture # leverage = 2.0
        dummy_metrics = {"profit": 100, "trades": 5, "leverage_applied": bt.leverage}
        bt.performance_metrics = dummy_metrics
        assert bt.get_performance_metrics() == dummy_metrics        
        assert bt.get_performance_metrics() is dummy_metrics

    # --- Fixture for save_results tests ---

    @pytest.fixture
    def backtest_instance_for_saving(self, tmp_path: Path):
        # Patch _get_project_root to return tmp_path for this test's scope
        # Patch fetchers to avoid real calls / dependency on API keys during init
        with patch('stock_monitoring_app.backtest.backtest.BackTest._get_project_root', return_value=tmp_path), \
             patch('stock_monitoring_app.backtest.backtest.PolygonFetcher') as MockPolygonFetcher, \
             patch('stock_monitoring_app.backtest.backtest.CoinGeckoFetcher') as MockCoinGeckoFetcher:

            mock_polygon_fetcher_instance = MockPolygonFetcher.return_value
            mock_polygon_fetcher_instance.get_service_name.return_value = "PolygonMockForSaving"
            
            mock_coingecko_fetcher_instance = MockCoinGeckoFetcher.return_value
            mock_coingecko_fetcher_instance.get_service_name.return_value = "CoinGeckoMockForSaving"

            # Use a specific leverage for saving tests, e.g., 3.0 for non-crypto
            bt_save = BackTest(ticker="TESTSAVE", period="1d", interval="1h", leverage=3.0)
            # If ticker was crypto, leverage would be 1.0. For "TESTSAVE" (non-crypto), it's 3.0.

            # Ensure the correct mock fetcher is assigned
            assert isinstance(bt_save.fetcher, MagicMock) 
            yield bt_save

    # --- Tests for save_results method ---

    @patch('stock_monitoring_app.backtest.backtest.datetime') 
    def test_save_results_success(self, mock_datetime_module, backtest_instance_for_saving: BackTest, sample_ohlcv_data_fixture: pd.DataFrame, tmp_path: Path):
        bt = backtest_instance_for_saving # leverage should be 3.0 from fixture
        bt.results = sample_ohlcv_data_fixture.head(3).copy()
        
        original_profit = 123.45
        # performance_metrics should reflect the applied leverage
        bt.performance_metrics = {
            "profit": original_profit * bt.leverage, # Profit is now leveraged
            "leverage_applied": bt.leverage,
            "trades": np.int64(10),
            "sharpe": np.float64(1.5), # Sharpe ratio ideally leverage-neutral
            "is_valid": np.bool_(True),
            "tags": ["test", "important"],
            "details": {"alpha": 0.05, "beta": np.float32(1.2)},
            "nan_value": np.nan,

            "inf_value": float('inf'),
            "neg_inf_value": float('-inf'),
            "pd_na_value": pd.NA
        } # Correctly closes the performance_metrics dictionary assignment



        # Use datetime.timezone.utc for robust compatibility
        from datetime import timezone as py_timezone # Import timezone
        utc_tz = py_timezone.utc

        # Use datetime.timezone.utc for robust compatibility

        from datetime import timezone as py_timezone # Import timezone
        utc_tz = py_timezone.utc
        
        # Create a fixed UTC timestamp. This is what mock_datetime_module.now() will return.
        fixed_timestamp_obj = dt(2023, 10, 26, 12, 30, 0, tzinfo=utc_tz)
        mock_datetime_module.now.return_value = fixed_timestamp_obj



        # The timestamp_str for expected filenames should be derived directly from this UTC fixed_timestamp_obj.
        timestamp_str = fixed_timestamp_obj.strftime("%Y%m%d_%H%M%S_UTC")


        expected_output_dir = tmp_path / "backtest_outputs"
        expected_results_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_results.csv"
        expected_metrics_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_metrics.json"
        expected_results_filepath = expected_output_dir / expected_results_filename
        expected_metrics_filepath = expected_output_dir / expected_metrics_filename

        bt.save_results()

        assert expected_output_dir.exists()
        assert expected_results_filepath.exists()
        assert expected_metrics_filepath.exists()

        saved_df = pd.read_csv(expected_results_filepath, index_col="Timestamp", parse_dates=True)
        pd.testing.assert_frame_equal(saved_df, bt.results, check_dtype=False)

        with open(expected_metrics_filepath, 'r') as f:
            saved_metrics = json.load(f)
        



        


        expected_serialized_metrics = {
            "profit": original_profit * bt.leverage, # Expected profit is leveraged
            "leverage_applied": bt.leverage,
            "trades": 10, 
            "sharpe": 1.5, 
            "is_valid": True,
            "tags": ["test", "important"], 
            "details": {"alpha": 0.05, "beta": 1.2000000476837158}, # np.float32 becomes float
            "nan_value": float('nan'),       # np.nan serializes to "NaN", loads as float('nan')

            "inf_value": float('inf'),       # float('inf') serializes to "Infinity", loads as float('inf')
            "neg_inf_value": float('-inf'),  # float('-inf') serializes to "-Infinity", loads as float('-inf')
            "pd_na_value": None,             # pd.NA serializes to null, loads as None


        }

        # Handle nested 'details' dictionary separately for pytest.approx
        # as pytest.approx does not support nested dictionaries directly when nan_ok=True is on the parent.
        expected_details_content = expected_serialized_metrics.pop("details")
        saved_details_content = saved_metrics.pop("details")

        assert saved_details_content == pytest.approx(expected_details_content), \
            "Comparison of 'details' dictionary failed"
        


        # Now compare the rest of the metrics, which may include NaN, inf, -inf values
        assert len(saved_metrics) == len(expected_serialized_metrics), \
            (f"Dictionaries have different lengths: "
             f"saved {len(saved_metrics)} (keys: {sorted(saved_metrics.keys())}), "
             f"expected {len(expected_serialized_metrics)} (keys: {sorted(expected_serialized_metrics.keys())})")
        
        for key in expected_serialized_metrics:
            assert key in saved_metrics, f"Key '{key}' missing in saved_metrics"
            
            expected_val = expected_serialized_metrics[key]
            saved_val = saved_metrics[key]

            if isinstance(expected_val, float) and math.isnan(expected_val):
                assert isinstance(saved_val, float) and math.isnan(saved_val), \
                    f"Mismatch for key '{key}': expected NaN, got {saved_val!r}"
            elif expected_val == float('inf'):
                assert saved_val == float('inf'), \
                    f"Mismatch for key '{key}': expected float('inf'), got {saved_val!r}"
            elif expected_val == float('-inf'):
                assert saved_val == float('-inf'), \
                    f"Mismatch for key '{key}': expected float('-inf'), got {saved_val!r}"
            elif isinstance(expected_val, (int, float)):
                 assert saved_val == pytest.approx(expected_val), \
                    f"Mismatch for key '{key}': expected approx {expected_val!r}, got {saved_val!r}"
            else: # For other types like bool, list, str, None
                assert saved_val == expected_val, \
                    f"Mismatch for key '{key}': expected {expected_val!r}, got {saved_val!r}"
        
        # Ensure all keys in saved_metrics were also in expected_metrics (covered by length check if all expected keys are present)
        # but an explicit check for extra keys in saved_metrics can be useful for debugging:
        extra_keys = set(saved_metrics.keys()) - set(expected_serialized_metrics.keys())
        assert not extra_keys, f"Extra keys found in saved_metrics: {extra_keys}"

        mock_datetime_module.now.assert_called_once()

    @patch('stock_monitoring_app.backtest.backtest.datetime')

    def test_save_results_no_df_still_saves_metrics(self, mock_datetime_module, backtest_instance_for_saving: BackTest, tmp_path: Path):
        bt = backtest_instance_for_saving # leverage=3.0
        bt.results = None

        bt.performance_metrics = {
            "note": "DataFrame was None, but metrics exist",
            "leverage_applied": bt.leverage 
        }


        # Use datetime.timezone.utc for robust compatibility
        from datetime import timezone as py_timezone # Import timezone
        utc_tz = py_timezone.utc
        
        fixed_timestamp_obj = dt(2023, 10, 26, 13, 0, 0, tzinfo=utc_tz) # Corrected time
        mock_datetime_module.now.return_value = fixed_timestamp_obj        # timestamp_str is derived directly from the UTC fixed_timestamp_obj
        timestamp_str = fixed_timestamp_obj.strftime("%Y%m%d_%H%M%S_UTC")


        expected_output_dir = tmp_path / "backtest_outputs"
        expected_results_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_results.csv"
        expected_metrics_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_metrics.json"
        expected_results_filepath = expected_output_dir / expected_results_filename
        expected_metrics_filepath = expected_output_dir / expected_metrics_filename

        bt.save_results()

        assert expected_output_dir.exists()
        assert not expected_results_filepath.exists()
        assert expected_metrics_filepath.exists()

        with open(expected_metrics_filepath, 'r') as f:
            saved_metrics = json.load(f)

        assert saved_metrics == {
            "note": "DataFrame was None, but metrics exist",
            "leverage_applied": bt.leverage # bt.leverage is 3.0
        }
        mock_datetime_module.now.assert_called_once()

    @patch('stock_monitoring_app.backtest.backtest.datetime')
    def test_save_results_no_metrics_still_saves_df(self, mock_datetime_module, backtest_instance_for_saving: BackTest, sample_ohlcv_data_fixture: pd.DataFrame, tmp_path: Path):
        bt = backtest_instance_for_saving
        bt.results = sample_ohlcv_data_fixture.head(2).copy()


        bt.performance_metrics = {}

        # Directly use datetime.timezone.utc for robust compatibility
        from datetime import timezone as py_timezone # Import timezone
        utc_tz = py_timezone.utc        
        fixed_timestamp_obj = dt(2023, 10, 26, 13, 30, 0, tzinfo=utc_tz)
        mock_datetime_module.now.return_value = fixed_timestamp_obj

        # timestamp_str is derived directly from the UTC fixed_timestamp_obj
        timestamp_str = fixed_timestamp_obj.strftime("%Y%m%d_%H%M%S_UTC")

        expected_output_dir = tmp_path / "backtest_outputs"
        expected_results_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_results.csv"
        expected_metrics_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_metrics.json"
        expected_results_filepath = expected_output_dir / expected_results_filename
        expected_metrics_filepath = expected_output_dir / expected_metrics_filename

        bt.save_results()

        assert expected_output_dir.exists()
        assert expected_results_filepath.exists()        
        assert not expected_metrics_filepath.exists()

        saved_df = pd.read_csv(expected_results_filepath, index_col="Timestamp", parse_dates=True)
        pd.testing.assert_frame_equal(saved_df, bt.results, check_dtype=False)
        mock_datetime_module.now.assert_called_once()

    def test_save_results_nothing_to_save(self, backtest_instance_for_saving: BackTest, tmp_path: Path):
        bt = backtest_instance_for_saving
        bt.results = None
        bt.performance_metrics = {}

        bt.save_results()

        expected_output_dir = tmp_path / "backtest_outputs"
        assert not expected_output_dir.exists()
        
        items_in_tmp = list(tmp_path.iterdir())
        assert not any(item.name.startswith(f"{bt.ticker}_{bt.period}_{bt.interval}_") and item.name.endswith("_results.csv") for item in items_in_tmp)

        assert not any(item.name.startswith(f"{bt.ticker}_{bt.period}_{bt.interval}_") and item.name.endswith("_metrics.json") for item in items_in_tmp)

    @patch('stock_monitoring_app.backtest.backtest.datetime')

    def test_save_results_results_empty_df_saves_metrics(self, mock_datetime_module, backtest_instance_for_saving: BackTest, tmp_path: Path):
        bt = backtest_instance_for_saving # leverage=3.0
        bt.results = pd.DataFrame()
        bt.performance_metrics = {
            "note": "DataFrame was empty, but metrics exist",
            "leverage_applied": bt.leverage
        }


        # Use datetime.timezone.utc for robust compatibility
        from datetime import timezone as py_timezone # Import timezone
        utc_tz = py_timezone.utc
        
        fixed_timestamp_obj = dt(2023, 10, 26, 14, 0, 0, tzinfo=utc_tz)
        mock_datetime_module.now.return_value = fixed_timestamp_obj

        # timestamp_str is derived directly from the UTC fixed_timestamp_obj
        timestamp_str = fixed_timestamp_obj.strftime("%Y%m%d_%H%M%S_UTC")

        expected_output_dir = tmp_path / "backtest_outputs"
        expected_results_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_results.csv"
        expected_metrics_filename = f"{bt.ticker}_{bt.period}_{bt.interval}_{timestamp_str}_metrics.json"
        expected_results_filepath = expected_output_dir / expected_results_filename        
        expected_metrics_filepath = expected_output_dir / expected_metrics_filename

        bt.save_results()

        assert expected_output_dir.exists()
        assert not expected_results_filepath.exists()
        assert expected_metrics_filepath.exists()

        with open(expected_metrics_filepath, 'r') as f:
            saved_metrics = json.load(f)
        assert saved_metrics == {
            "note": "DataFrame was empty, but metrics exist",
            "leverage_applied": bt.leverage # bt.leverage is 3.0
        }
        mock_datetime_module.now.assert_called_once()


    @patch('stock_monitoring_app.backtest.backtest.BackTest.save_results')                 # Innermost patch, first mock argument after self
    @patch('stock_monitoring_app.backtest.backtest.BackTest.evaluate_performance')         # Next patch
    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')                           # Next patch
    @patch('stock_monitoring_app.backtest.backtest.BackTest.optimize_thresholds')            # Next patch
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators') # Next patch (removed duplicate)
    @patch('stock_monitoring_app.backtest.backtest.BackTest.fetch_historical_data')         # Outermost patch, last mock argument
    def test_run_backtest_calls_save_results_on_success(
        self, 
        mock_fetch_historical_data,       # Corresponds to @patch('...fetch_historical_data')
        mock_determine_relevant_indicators, # Corresponds to @patch('...determine_relevant_indicators')        
        mock_optimize_thresholds,         # Corresponds to @patch('...optimize_thresholds')
        MockBaseStrategy,                 # Corresponds to @patch('...BaseStrategy')
        mock_evaluate_performance,        # Corresponds to @patch('...evaluate_performance')

        mock_save_results,                # Corresponds to @patch('...save_results')
        backtest_stock_instance_fixture: BackTest, # Fixture argument
        sample_ohlcv_data_fixture: pd.DataFrame    # Fixture argument
    ):
        bt = backtest_stock_instance_fixture # Use the actual fixture instance
        bt.historical_data = sample_ohlcv_data_fixture

        # Use the correctly named mock arguments
        mock_determine_relevant_indicators.return_value = [{'type': MockIndicatorAlpha, 'params': {}}]
        mock_optimize_thresholds.side_effect = lambda d, c: c # Optimize returns configs as is
        
        mock_strategy_instance = MockBaseStrategy.return_value
        mock_results_df = sample_ohlcv_data_fixture.copy()
        mock_results_df['Strategy_Signal'] = SIGNAL_HOLD
        mock_strategy_instance.run.return_value = mock_results_df
        
        # mock_evaluate_performance should return a dict that includes leverage
        mock_evaluate_performance.return_value = {"net_profit": 100 * bt.leverage, "leverage_applied": bt.leverage}
    
        bt.run_backtest()
        mock_save_results.assert_called_once()

    @patch('stock_monitoring_app.backtest.backtest.BackTest.fetch_historical_data')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.optimize_thresholds')
    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.evaluate_performance')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.save_results')
    def test_run_backtest_does_not_call_save_results_if_no_results_df(
        self, mock_save_results, mock_eval_perf, MockBaseStrategy, mock_opt_thresh, 
        mock_det_ind, mock_fetch_data, backtest_stock_instance_fixture: BackTest, 
        sample_ohlcv_data_fixture: pd.DataFrame
    ):
        bt = backtest_stock_instance_fixture
        bt.historical_data = sample_ohlcv_data_fixture
        mock_det_ind.return_value = [{'type': MockIndicatorAlpha, 'params': {}}]
        mock_opt_thresh.side_effect = lambda d, c: c
        mock_strategy_instance = MockBaseStrategy.return_value
        mock_strategy_instance.run.return_value = pd.DataFrame() 
        mock_eval_perf.return_value = {"note": "empty df"}

        bt.run_backtest()
        mock_save_results.assert_not_called()

    @patch('stock_monitoring_app.backtest.backtest.BackTest.fetch_historical_data')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.determine_relevant_indicators')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.optimize_thresholds')
    @patch('stock_monitoring_app.backtest.backtest.BaseStrategy')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.evaluate_performance')
    @patch('stock_monitoring_app.backtest.backtest.BackTest.save_results')
    def test_run_backtest_does_not_call_save_results_if_strategy_run_is_none(
        self, mock_save_results, mock_eval_perf, MockBaseStrategy, mock_opt_thresh, 
        mock_det_ind, mock_fetch_data, backtest_stock_instance_fixture: BackTest, 
        sample_ohlcv_data_fixture: pd.DataFrame
    ):
        bt = backtest_stock_instance_fixture
        bt.historical_data = sample_ohlcv_data_fixture
        mock_det_ind.return_value = [{'type': MockIndicatorAlpha, 'params': {}}]
        mock_opt_thresh.side_effect = lambda d, c: c
        mock_strategy_instance = MockBaseStrategy.return_value
        mock_strategy_instance.run.return_value = None 
        
        bt.run_backtest()
        mock_eval_perf.assert_not_called() 
        mock_save_results.assert_not_called()

