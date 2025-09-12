#!/usr/bin/env python3
"""
Refactored Pricer - Removes code duplication by using existing backtester components

This refactored version eliminates duplication between pricer.py and backtester.py
by using the existing Strategy, Backtester, and other components.
"""

import requests
import pandas as pd
import argparse
import os
import json
import math
import time
import glob
from datetime import datetime, timedelta
import logging
from pathlib import Path

from core.logger_config import setup_logging
from core.app_config import Config
from core.result_manager import ResultManager
from strategy import Strategy
from backtester import Backtester
from indicators import Indicators
from config import strategy_configs, DEFAULT_TIMEFRAME, DEFAULT_INTERVAL, indicator_defaults
from pricer_compatibility_fix import find_best_result_file
from core.data_fetcher import get_crypto_data_merged, get_current_price
from lines import (
    auto_discover_percentage_change,
    find_swing_points,
    find_support_resistance_lines,
    predict_next_move,
)
from chart import generate_chart





def get_trade_signal_for_latest(df: pd.DataFrame, strategy: Strategy, params: dict):
    """
    Get trade signal for the latest data point using the existing Strategy class.
    This replaces the duplicated get_trade_signal function.
    """
    try:
        # Generate signals for the entire dataset
        long_entry, short_entry, long_exit, short_exit = strategy.generate_signals(df, params)
        
        # Check the latest signals
        if not long_entry.empty and long_entry.iloc[-1]:
            return "LONG"
        elif not short_entry.empty and short_entry.iloc[-1]:
            return "SHORT"
        else:
            return "HOLD"
    except Exception as e:
        logging.error(f"Error generating trade signal: {e}")
        return "HOLD"

def run_backtest_using_existing_system(df: pd.DataFrame, strategy_name: str, params: dict, config: dict, initial_capital: float = 10000.0):
    """
    Run backtest using the existing Backtester class instead of duplicated code.
    """
    try:
        if isinstance(config, dict):
            config = Config(**config)
        # Get strategy configuration
        if strategy_name not in strategy_configs:
            logging.error(f"Strategy {strategy_name} not found in configurations")
            return None
        
        strategy_config = strategy_configs[strategy_name]
        
        # Create strategy and backtester instances
        indicators = Indicators()
        strategy = Strategy(indicators, strategy_config)
        backtester = Backtester(df, strategy, config)
        backtester.initial_capital = initial_capital
        
        # Ensure required parameters exist
        params['spread_percentage'] = params.get('spread_percentage', 0.01)
        params['slippage_percentage'] = params.get('slippage_percentage', 0.001)

        # Run the backtest
        result = backtester.run_backtest(params)
        
        if result is None:
            logging.warning("Backtest returned None - possibly due to Cython not being available")
            return None
        
        return result
        
    except Exception as e:
        logging.error(f"Error running backtest: {e}")
        return None

def create_default_params():
    """Create default parameters using indicator defaults."""
    return {
        'short_sma_period': indicator_defaults.get('short_sma_period', 20),
        'long_sma_period': indicator_defaults.get('long_sma_period', 50),
        'short_ema_period': indicator_defaults.get('short_ema_period', 12),
        'long_ema_period': indicator_defaults.get('long_ema_period', 26),
        'rsi_oversold': indicator_defaults.get('rsi_oversold', 30),
        'rsi_overbought': indicator_defaults.get('rsi_overbought', 70),
        'atr_period': indicator_defaults.get('atr_period', 14),
        'atr_multiple': indicator_defaults.get('atr_multiple', 2.0),
        'fixed_stop_loss_percentage': indicator_defaults.get('fixed_stop_loss_percentage', 0.02),
        'take_profit_multiple': indicator_defaults.get('take_profit_multiple', 2.0),
        'macd_fast_period': indicator_defaults.get('macd_fast_period', 12),
        'macd_slow_period': indicator_defaults.get('macd_slow_period', 26),
        'macd_signal_period': indicator_defaults.get('macd_signal_period', 9),
        'spread_percentage': indicator_defaults.get('spread_percentage', 0.01),
        'slippage_percentage': indicator_defaults.get('slippage_percentage', 0.001)
    }

def load_best_parameters_from_results(crypto_id):
    """Load best parameters from existing backtest results."""
    try:
        # Try to find the best result file
        best_file = find_best_result_file(crypto_id)
        if best_file and os.path.exists(best_file):
            with open(best_file, 'r') as f:
                data = json.load(f)
            
            # Extract parameters from the best result
            if 'best_params' in data:
                return data['best_params']
            elif 'params' in data:
                return data['params']
        
        logging.info(f"No best parameters found for {crypto_id}, using defaults")
        return create_default_params()
        
    except Exception as e:
        logging.error(f"Error loading best parameters: {e}")
        return create_default_params()

def get_best_strategy_for_crypto(crypto_id):
    """Get the best strategy for a cryptocurrency from existing results."""
    try:
        best_file = find_best_result_file(crypto_id)
        if best_file and os.path.exists(best_file):
            with open(best_file, 'r') as f:
                data = json.load(f)
            
            if 'strategy' in data:
                return data['strategy']
            elif 'best_strategy' in data:
                return data['best_strategy']
        
        # Default to EMA_Only if no best strategy found
        logging.info(f"No best strategy found for {crypto_id}, using EMA_Only")
        return "EMA_Only"
        
    except Exception as e:
        logging.error(f"Error loading best strategy: {e}")
        return "EMA_Only"

def _convert_to_json_serializable(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {key: _convert_to_json_serializable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_convert_to_json_serializable(item) for item in obj]
    return obj

def optimize_crypto_with_existing_system(crypto_id, config: dict, timeframe=DEFAULT_TIMEFRAME, interval=DEFAULT_INTERVAL, 
                                      use_best_params=True, strategy_name=None, strategy_params: dict = None):
    """
    Analyze cryptocurrency using existing backtester system components.
    This replaces the large duplicated analysis function.
    """
    logging.info(f"Analyzing {crypto_id} using existing system components...")
    
    try:
        if isinstance(config, dict):
            config = Config(**config)
        # Get data - use the correct function signature
        df = get_crypto_data_merged(crypto_id, timeframe, config)
        if df is None or df.empty:
            logging.error(f"No data available for {crypto_id}")
            return None
        
        # Add 'price' column for compatibility with some functions that expect it
        df['price'] = df['close']
        
        if df.empty:
            logging.error(f"No valid data for {crypto_id}")
            return None
        
        # Determine strategy to use
        if strategy_name is None:
            strategy_name = get_best_strategy_for_crypto(crypto_id)
        
        # Load parameters
        if use_best_params:
            params = load_best_parameters_from_results(crypto_id)
        else:
            params = create_default_params()
        
        # Merge with provided strategy_params, if any
        if strategy_params:
            params.update(strategy_params)
        
        # Create strategy instance
        if strategy_name not in strategy_configs:
            logging.error(f"Strategy {strategy_name} not found")
            return None
        
        strategy_config = strategy_configs[strategy_name]
        indicators = Indicators()
        strategy = Strategy(indicators, strategy_config)
        
        # Get current trade signal
        current_signal = get_trade_signal_for_latest(df, strategy, params)
        
        # Run backtest to get performance metrics
        backtest_result = run_backtest_using_existing_system(df, strategy_name, params, config)
        
        # Get current price
        current_price = get_current_price(crypto_id)
        
        # Analyze support/resistance lines (keeping this unique functionality)
        try:
            # First discover optimal percentage change
            first_timestamp = df.index[0]
            optimal_percentage_change = auto_discover_percentage_change(df, first_timestamp)
            
            if optimal_percentage_change is None:
                logging.warning("Optimal percentage change could not be determined. Using default.")
                optimal_percentage_change = 0.005
            
            # Find swing points
            swing_highs_df, swing_lows_df = find_swing_points(df, percentage_change=optimal_percentage_change, min_bars_confirmation=2)
            
            # Find support and resistance lines
            resistance_lines = find_support_resistance_lines(swing_highs_df, 'resistance', first_timestamp)
            support_lines = find_support_resistance_lines(swing_lows_df, 'support', first_timestamp)
            
            # Find active lines (simplified version)
            latest_price = df['close'].iloc[-1]
            latest_price_point = df.iloc[-1]
            latest_relative_timestamp = (latest_price_point.name.timestamp() - first_timestamp.timestamp())
            
            active_resistance = []
            active_support = []
            
            # Find active resistance lines
            for r_line in resistance_lines:
                r_y_at_latest_time = r_line['slope'] * latest_relative_timestamp + r_line['intercept']
                if abs(r_y_at_latest_time - latest_price) / latest_price <= 0.05:  # Within 5%
                    r_line['current_price'] = r_y_at_latest_time
                    active_resistance.append(r_line)
            
            # Find active support lines
            for s_line in support_lines:
                s_y_at_latest_time = s_line['slope'] * latest_relative_timestamp + s_line['intercept']
                if abs(s_y_at_latest_time - latest_price) / latest_price <= 0.05:  # Within 5%
                    s_line['current_price'] = s_y_at_latest_time
                    active_support.append(s_line)
                    
        except Exception as e:
            logging.warning(f"Error in support/resistance analysis: {e}")
            active_resistance = []
            active_support = []
        
        # Predict next move using existing function
        try:
            next_move_prediction = predict_next_move(df, latest_price_point, active_resistance, active_support, first_timestamp)
        except Exception as e:
            logging.warning(f"Error in next move prediction: {e}")
            next_move_prediction = None
        
        # Compile results
        analysis_result = {
            'crypto_id': crypto_id,
            'current_price': current_price,
            'latest_data_price': latest_price,
            'current_signal': current_signal,
            'strategy_used': strategy_name,
            'parameters_used': params,
            'backtest_result': backtest_result,
            'active_resistance_lines': active_resistance,
            'active_support_lines': active_support,
            'next_move_prediction': next_move_prediction,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return _convert_to_json_serializable(analysis_result)
        
    except Exception as e:
        logging.error(f"Error analyzing {crypto_id}: {e}")
        return None


def run_continuous_analysis(crypto_id, config, interval_minutes=60, strategy_name=None, result_manager=None):
    """Run continuous analysis using existing system components."""
    logging.info(f"Starting continuous analysis for {crypto_id} (interval: {interval_minutes} minutes)")
    
    while True:
        try:
            # Run analysis
            result = optimize_crypto_with_existing_system(crypto_id, config, strategy_name=strategy_name)
            
            if result:
                # Save result
                result_manager.save_analysis_result(result['crypto_id'], result)
                
                # Log key information
                logging.info(f"Analysis complete for {crypto_id}:")
                logging.info(f"  Current Signal: {result['current_signal']}")
                logging.info(f"  Strategy: {result['strategy_used']}")
                logging.info(f"  Current Price: ${result['current_price']:.2f}")
                
                if result['backtest_result']:
                    backtest = result['backtest_result']
                    if isinstance(backtest, dict):
                        profit = backtest.get('total_profit_percentage', 0)
                        trades = backtest.get('num_trades', 0)
                        win_rate = backtest.get('win_rate', 0)
                        logging.info(f"  Backtest Performance: {profit:.2f}% profit, {trades} trades, {win_rate:.1f}% win rate")
                
                # Log active support/resistance
                if result['active_resistance_lines']:
                    logging.info(f"  Active Resistance: {len(result['active_resistance_lines'])} lines")
                if result['active_support_lines']:
                    logging.info(f"  Active Support: {len(result['active_support_lines'])} lines")
            
            # Wait for next interval
            logging.info(f"Waiting {interval_minutes} minutes for next analysis...")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            logging.info("Continuous analysis stopped by user")
            break
        except Exception as e:
            logging.error(f"Error in continuous analysis: {e}")
            logging.info(f"Retrying in {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)

def main():
    """Main function with refactored logic using existing components."""
    config = Config()
    setup_logging(config)
    pd.set_option('display.float_format', '{:f}'.format)
    parser = argparse.ArgumentParser(description='Refactored Crypto Pricer - Uses existing backtester components')
    
    parser.add_argument('--crypto', type=str, required=True, help='Cryptocurrency ID (e.g., bitcoin)')
    parser.add_argument('--timeframe', type=int, default=DEFAULT_TIMEFRAME, help='Timeframe in days')
    parser.add_argument('--interval', type=str, default=DEFAULT_INTERVAL, help='Data interval')
    parser.add_argument('--strategy', type=str, help='Strategy to use (default: auto-detect best)')
    parser.add_argument('--continuous', action='store_true', help='Run continuous analysis')
    parser.add_argument('--interval-minutes', type=int, default=60, help='Interval for continuous analysis in minutes')
    parser.add_argument('--use-default-params', action='store_true', help='Use default parameters instead of best found')
    parser.add_argument('--output-dir', type=str, default='live_results', help='Output directory for results')
    parser.add_argument('--generate-chart', action='store_true', help='Generate chart after analysis')
    
    args = parser.parse_args()
    
    # Initialize Config and ResultManager
    result_manager = ResultManager(config)

    logging.info("=== Refactored Crypto Pricer Started ===")
    logging.info(f"Using existing backtester components to eliminate code duplication")
    logging.info(f"Analyzing: {args.crypto}")
    logging.info(f"Strategy: {args.strategy or 'auto-detect'}")
    logging.info(f"Timeframe: {args.timeframe} days")
    logging.info(f"Interval: {args.interval}")
    
    try:
        if args.continuous:
            # Run continuous analysis
            run_continuous_analysis(
                args.crypto, 
                config,
                args.interval_minutes, 
                args.strategy,
                result_manager # Pass result_manager
            )
        else:
            # Run single analysis
            result = optimize_crypto_with_existing_system(
                args.crypto,
                config,
                args.timeframe,
                args.interval,
                use_best_params=not args.use_default_params,
                strategy_name=args.strategy
            )
            
            if result:
                # Save result using ResultManager
                filepath = result_manager.save_analysis_result(result['crypto_id'], result)
                
                # Display results
                print(f"\n=== Analysis Results for {args.crypto.upper()} ===")
                print(f"Current Price: ${result['current_price']:.2f}")
                print(f"Trade Signal: {result['current_signal']}")
                print(f"Strategy Used: {result['strategy_used']}")
                
                if result['backtest_result']:
                    backtest = result['backtest_result']
                    if isinstance(backtest, dict):
                        print(f"\nBacktest Performance:")
                        print(f"  Total Profit: {backtest.get('total_profit_percentage', 0):.2f}%")
                        print(f"  Number of Trades: {backtest.get('total_trades', 0)}")
                        print(f"  Win Rate: {backtest.get('win_rate', 0):.1f}%")
                        print(f"  Sharpe Ratio: {backtest.get('sharpe_ratio', 0):.2f}")
                
                print(f"\nSupport/Resistance Analysis:")
                print(f"  Active Resistance Lines: {len(result['active_resistance_lines'])}")
                print(f"  Active Support Lines: {len(result['active_support_lines'])}")
                
                if result['next_move_prediction']:
                    pred = result['next_move_prediction']
                    print(f"\nNext Move Prediction:")
                    print(f"  Prediction Score: {pred.get('prediction_score', 'N/A')}")
                    print(f"  Reasons:")
                    for reason in pred.get('reasons', []):
                        print(f"  - {reason}")
                    print(f"  Prediction: {pred.get('direction', 'Unknown')}")
                    print(f"  Confidence: {pred.get('confidence', 0):.1f}%")
                
                print(f"\nResults saved to: {filepath}")
                
                # Generate chart if requested
                if args.generate_chart:
                    try:
                        # Get data for charting
                        df = get_crypto_data_merged(args.crypto, args.timeframe, config)
                        if df is not None and not df.empty:
                            df['price'] = df['close']  # Add price column for compatibility
                            
                            chart_path = generate_chart(
                                df, 
                                result['active_resistance_lines'], 
                                result['active_support_lines'], 
                                result['active_resistance_lines'], # Pass active_resistance
                                result['active_support_lines'], # Pass active_support
                                args.crypto,
                                os.path.join(config.DATA_DIR, "charts", f"{args.crypto}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png") # Use centralized config
                            )
                            print(f"Chart saved to: {chart_path}")
                    except Exception as e:
                        logging.error(f"Error generating chart: {e}")
                
            else:
                print(f"Failed to analyze {args.crypto}")
                return 1
    
    except KeyboardInterrupt:
        logging.info("Analysis interrupted by user")
        return 0
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1
    
    logging.info("=== Analysis Complete ===")
    return 0

if __name__ == "__main__":
    exit(main())


# Example usage:
# python pricer.py --crypto bitcoin --strategy EMA_Only --use-default-params
# python pricer.py --crypto ethereum --continuous --interval-minutes 30
# python pricer.py --crypto solana --generate-chart