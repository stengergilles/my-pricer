import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import logging
import json
import argparse
import itertools
import os
import multiprocessing
from tqdm import tqdm
import random
import sys
from config import strategy_configs, param_sets, DEFAULT_TIMEFRAME, DEFAULT_INTERVAL, DEFAULT_SPREAD_PERCENTAGE, DEFAULT_SLIPPAGE_PERCENTAGE, indicator_defaults

from indicators import Indicators, calculate_atr
from strategy import Strategy
from core.data_fetcher import DataFetcher
from core.rate_limiter import RateLimiter

try:
    from backtester_cython import run_backtest_cython
    CYTHON_AVAILABLE = True
    logging.info("--- cython imported successfully ---")
except ImportError as e:
    logging.error(f"--- cython import error: {e} ---")
    CYTHON_AVAILABLE = False
    run_backtest_cython = None

class Backtester:
    def __init__(self, strategy, config, data_fetcher=None):
        self.strategy = strategy
        self.config = config
        self.initial_capital = 100.0
        if data_fetcher is None:
            # Instantiate its own DataFetcher if not provided
            rate_limiter = RateLimiter(requests_per_minute=8, seconds_per_request=1.11) # Default values, can be configured
            self.data_fetcher = DataFetcher(rate_limiter)
        else:
            self.data_fetcher = data_fetcher
        self.data = None # Data will be fetched later

    def set_data(self, data):
        self.data = data

    def fetch_data(self, symbol: str, interval: str, start_date: datetime, end_date: datetime):
        """Fetches historical klines data using the internal DataFetcher."""
        start_time_ms = int(start_date.timestamp() * 1000)
        end_time_ms = int(end_date.timestamp() * 1000)
        klines_data = self.data_fetcher.fetch_klines(symbol, interval, start_time_ms, end_time_ms)
        
        # Convert klines_data (list of lists) to DataFrame
        # Assuming klines_data format: [[timestamp, open, high, low, close, volume, ...]]
        df = pd.DataFrame(klines_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        return df

    def run_backtest(self, params):
        logging.info("Backtester.run_backtest started.")
        if not CYTHON_AVAILABLE:
            logging.error("Cython backtester not available. Please compile it first.")
            return None

        prices = self.data['close'].to_numpy(dtype=np.float64)
        
        logging.info("Generating signals...")
        long_entry, short_entry, long_exit, short_exit = self.strategy.generate_signals(self.data, params)
        logging.info("Signals generated.")

        # Convert to numpy uint8 for Cython
        long_entry = long_entry.to_numpy(dtype=np.uint8)
        short_entry = short_entry.to_numpy(dtype=np.uint8)
        long_exit = long_exit.to_numpy(dtype=np.uint8)
        short_exit = short_exit.to_numpy(dtype=np.uint8)

        atr_values = calculate_atr(self.data, params.get('atr_period', indicator_defaults['atr_period'])).to_numpy(dtype=np.float64)

        atr_multiple = params.get('atr_multiple', indicator_defaults['atr_multiple'])
        fixed_stop_loss_percentage = params.get('fixed_stop_loss_percentage', indicator_defaults['fixed_stop_loss_percentage'])
        take_profit_multiple = params.get('take_profit_multiple', indicator_defaults['take_profit_multiple'])

        # Calculate daily volatility for position sizing decision
        daily_volatility = 0.0
        if len(prices) > 1:
            price_change = (prices[-1] - prices[0]) / prices[0]
            daily_volatility = abs(price_change)

        logging.info("Calling Cython backtest module...")
        cython_results_json = run_backtest_cython(
            prices,
            long_entry,
            short_entry,
            long_exit,
            short_exit,
            atr_values,
            atr_multiple,
            fixed_stop_loss_percentage,
            take_profit_multiple,
            self.initial_capital,
            params['spread_percentage'],
            params['slippage_percentage'],
            daily_volatility
        )
        logging.info("Cython backtest module returned.")

        # The Cython module might return a JSON string or a dict (on error)
        if isinstance(cython_results_json, str):
            results = json.loads(cython_results_json)
        else:
            results = cython_results_json
        return results

def display_results(results, params, initial_capital=100.0):
    if not results:
        logging.info("No results to display.")
        return

    logging.info(f"  Initial Capital: {initial_capital:.2f}")
    logging.info(f"  Final Capital: {results['final_capital']:.2f}")
    logging.info(f"  Total Profit/Loss: {results['total_profit_loss']:.2f}")
    logging.info(f"  Sharpe Ratio: {results.get('sharpe_ratio', 'N/A')}")
    logging.info(f"  Total Trades: {results['total_trades']}")
    logging.info(f"  Winning Trades: {results['winning_trades']}")
    logging.info(f"  Losing Trades: {results['losing_trades']}")
    logging.info(f"  Win Rate: {results['win_rate'] * 100:.2f}%")
    logging.info(f"  Long Trades: {results.get('num_long_trades', 0)}, Profit: {results.get('long_profit', 0.0):.2f}")
    logging.info(f"  Short Trades: {results.get('num_short_trades', 0)}, Profit: {results.get('short_profit', 0.0):.2f}")
    logging.info(f"  Parameters:")
    for param, value in params.items():
        if isinstance(value, float):
            logging.info(f"    {param}: {value:.4f}")
        else:
            logging.info(f"    {param}: {value}")

def generate_param_grid(param_ranges, num_samples):
    key_mapping = {
        'short_sma_range': 'short_sma_period',
        'long_sma_range': 'long_sma_period',
        'rsi_overbought_range': 'rsi_overbought',
        'rsi_oversold_range': 'rsi_oversold',
        'macd_fast_period_range': 'macd_fast_period',
        'macd_slow_period_range': 'macd_slow_period',
        'macd_signal_period_range': 'macd_signal_period',
        'fixed_stop_loss_percentage_range': 'fixed_stop_loss_percentage',
        'take_profit_multiple_range': 'take_profit_multiple',
        'atr_period_range': 'atr_period',
        'atr_multiple_range': 'atr_multiple'
    }

    param_values_map = {}
    for range_key, param_name in key_mapping.items():
        if range_key in param_ranges:
            start, stop, step = param_ranges[range_key]
            param_values_map[param_name] = np.arange(start, stop, step).tolist()

    param_grid = []
    for _ in range(num_samples):
        param_dict = {}
        for param_name, values_list in param_values_map.items():
            param_dict[param_name] = random.choice(values_list)
        param_grid.append(param_dict)

    return param_grid

def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    return obj

def run_single_backtest(args, config, data_fetcher=None):
    """
    Runs a single backtest with the given parameters.
    """
    logging.info(f"Starting single backtest for {args.crypto} with strategy {args.strategy}")
    
    # Create indicators and strategy
    indicators = Indicators()
    strategy_config = strategy_configs[args.strategy]
    strategy = Strategy(indicators, strategy_config)

    # Create backtester, passing the data_fetcher
    backtester = Backtester(strategy, config, data_fetcher) # Changed constructor call

    # Load data using the backtester's fetch_data method
    try:
        logging.info(f"Attempting to fetch data for {args.crypto}...")
        # Define a reasonable date range for backtesting, e.g., last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90) # Fetch data for the last 90 days
        data = backtester.fetch_data(args.crypto, DEFAULT_TIMEFRAME, start_date, end_date)
        backtester.set_data(data) # Set the fetched data
        logging.info(f"Successfully fetched data for {args.crypto}. Data points: {len(data)}")
    except Exception as e: # Catching a more general exception now
        logging.error(f"Failed to fetch data for {args.crypto}: {e}")
        return # Exit gracefully if data fetching fails

    # Collect parameters from args
    params = {
        'short_sma_period': args.short_sma_period,
        'long_sma_period': args.long_sma_period,
        'short_ema_period': args.short_ema_period,
        'long_ema_period': args.long_ema_period,
        'rsi_oversold': args.rsi_oversold,
        'rsi_overbought': args.rsi_overbought,
        'bb_period': args.bb_period,
        'bb_std_dev': args.bb_std_dev,
        'rsi_period': args.rsi_period,
        'atr_period': args.atr_period,
        'atr_multiple': args.atr_multiple,
        'fixed_stop_loss_percentage': args.fixed_stop_loss_percentage,
        'take_profit_multiple': args.take_profit_multiple,
        'macd_fast_period': args.macd_fast_period,
        'macd_slow_period': args.macd_slow_period,
        'macd_signal_period': args.macd_signal_period,
        'spread_percentage': DEFAULT_SPREAD_PERCENTAGE,
        'slippage_percentage': DEFAULT_SLIPPAGE_PERCENTAGE,
    }
    # Filter out None values so that defaults from indicator_defaults can be used
    params = {k: v for k, v in params.items() if v is not None}
    
    # Fill missing params with defaults
    for p in indicator_defaults:
        if p not in params:
            params[p] = indicator_defaults[p]


    logging.info("Running backtest...")
    results = backtester.run_backtest(params)
    logging.info("Backtest completed.")

    if results:
        display_results(results, params)
        # Print results in a machine-readable format for the optimizer
        results_with_source = convert_numpy_types(results)
        results_with_source['source'] = args.source
        print(f"OPTIMIZER_RESULTS:{json.dumps(results_with_source)}")
    else:
        logging.info("No profitable parameters found.")


if __name__ == "__main__":
    from core.app_config import Config
    

    available_strategies = list(strategy_configs.keys())
    available_param_sets = set(param_sets['default_sets'].keys())
    for crypto in param_sets:
        if crypto != 'default_sets':
            available_param_sets.update(param_sets[crypto].keys())

    parser = argparse.ArgumentParser(
        description='Crypto Backtester',
        formatter_class=argparse.RawTextHelpFormatter
    )
    # --- Core Arguments ---
    parser.add_argument('--crypto', required=True, help='Cryptocurrency ID from CoinGecko')
    parser.add_argument('--strategy', required=True, help=f"The trading strategy to use. Available: {', '.join(available_strategies)}")
    
    # --- Mode Selection ---
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--param-set', help=f"Run in search mode with a predefined parameter set. Available: {', '.join(available_param_sets)}")
    group.add_argument('--single-run', action='store_true', help='Run a single backtest with the specified parameters.')
    parser.add_argument('--source', type=str, default='manual', help='Source of the backtest (e.g., "manual", "optimized").')

    # --- Search Mode Arguments ---
    parser.add_argument('--num-samples', type=int, default=1000, help='Number of random samples for parameter search.')

    # --- Single Run Parameter Arguments ---
    parser.add_argument('--short-sma-period', type=int)
    parser.add_argument('--long-sma-period', type=int)
    parser.add_argument('--short-ema-period', type=int)
    parser.add_argument('--long-ema-period', type=int)
    parser.add_argument('--rsi-oversold', type=int)
    parser.add_argument('--rsi-overbought', type=int)
    parser.add_argument('--bb-period', type=int)
    parser.add_argument('--bb-std-dev', type=float)
    parser.add_argument('--rsi-period', type=int)
    parser.add_argument('--atr-period', type=int)
    parser.add_argument('--atr-multiple', type=float)
    parser.add_argument('--fixed-stop-loss-percentage', type=float)
    parser.add_argument('--take-profit-multiple', type=float)
    parser.add_argument('--macd-fast-period', type=int)
    parser.add_argument('--macd-slow-period', type=int)
    parser.add_argument('--macd-signal-period', type=int)

    args = parser.parse_args()

    if args.strategy not in strategy_configs:
        logging.error(f"Error: Strategy '{args.strategy}' not found. Available: {', '.join(available_strategies)}")
        exit()

    if args.single_run:
        app_config = Config() # Instantiate Config
        run_single_backtest(args, app_config, data_fetcher=None) # Pass the instance, let it create its own DataFetcher
    else: # Search mode
        app_config = Config() # Instantiate Config for search mode as well

        # Create strategy
        indicators = Indicators()
        strategy_config = strategy_configs[args.strategy]
        strategy = Strategy(indicators, strategy_config)
        
        # For multiprocessing, each process will need its own DataFetcher
        # to avoid issues with sharing connections/rate limiters across processes.
        # The Backtester constructor will handle creating one if not provided.
        
        # Get param ranges
        if args.crypto in param_sets and args.param_set in param_sets[args.crypto]:
            param_ranges = param_sets[args.crypto][args.param_set]
        elif args.param_set in param_sets['default_sets']:
            param_ranges = param_sets['default_sets'][args.param_set]
        else:
            logging.error(f"Error: Param set '{args.param_set}' not found. Available: {', '.join(available_param_sets)}")
            exit()

        param_grid = generate_param_grid(param_ranges, args.num_samples)

        for p_set in param_grid:
            p_set['spread_percentage'] = DEFAULT_SPREAD_PERCENTAGE
            p_set['slippage_percentage'] = DEFAULT_SLIPPAGE_PERCENTAGE

        # Define a helper function for multiprocessing to create its own backtester and fetch data
        def run_backtest_with_data_fetch(params):
            # Each process creates its own Backtester and DataFetcher
            local_backtester = Backtester(strategy, app_config) # Backtester will create its own DataFetcher
            
            # Define a reasonable date range for backtesting, e.g., last 90 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90) # Fetch data for the last 90 days
            
            try:
                data = local_backtester.fetch_data(args.crypto, DEFAULT_TIMEFRAME, start_date, end_date)
                local_backtester.set_data(data)
                return local_backtester.run_backtest(params)
            except Exception as e:
                logging.error(f"Error in multiprocessing backtest for {args.crypto} with params {params}: {e}")
                return None

        # Run backtests in parallel
        num_processes = os.cpu_count() // 2 if os.cpu_count() > 1 else 1
        with multiprocessing.Pool(processes=num_processes) as pool:
            results_list = list(tqdm(pool.imap(run_backtest_with_data_fetch, param_grid), total=len(param_grid)))

        # Find and display best results
        best_profit = -float('inf')
        best_params = None
        best_results = None

        for i, results in enumerate(results_list):
            if results and results['total_profit_loss'] > best_profit:
                best_profit = results['total_profit_loss']
                best_params = param_grid[i]
                best_results = results

        if best_results:
            logging.info("--- Best Results (Search Mode) ---")
            display_results(best_results, best_params)
            # ... (rest of the boundary checking and saving logic)
        else:
            logging.info("No profitable parameters found in search mode.")
