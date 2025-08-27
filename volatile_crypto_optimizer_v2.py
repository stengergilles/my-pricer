#!/usr/bin/env python3
"""
Simplified volatile crypto optimizer using unified core.
Replaces the original volatile_crypto_optimizer.py with cleaner architecture.
"""

import argparse
import logging
import sys
from core.trading_engine import TradingEngine
from core.logger_config import setup_logging

def main():
    parser = argparse.ArgumentParser(description='Batch optimization for volatile cryptocurrencies')
    parser.add_argument('--strategy', required=True, help='Trading strategy name')
    parser.add_argument('--n-trials', type=int, default=30, help='Number of trials per crypto')
    parser.add_argument('--top-count', type=int, default=10, help='Number of top volatile cryptos to optimize')
    parser.add_argument('--min-volatility', type=float, default=5.0, help='Minimum volatility threshold (percent)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Initialize trading engine
    engine = TradingEngine()
    
    # Validate strategy
    available_strategies = [s['name'] for s in engine.get_strategies()]
    if args.strategy not in available_strategies:
        print(f"Error: Unknown strategy '{args.strategy}'")
        print(f"Available strategies: {', '.join(available_strategies)}")
        sys.exit(1)
    
    # Get volatile cryptos first
    print(f"Discovering volatile cryptocurrencies (min volatility: {args.min_volatility}%)")
    volatile_cryptos = engine.get_volatile_cryptos(
        min_volatility=args.min_volatility,
        limit=100
    )
    
    if not volatile_cryptos:
        print("No volatile cryptocurrencies found!")
        sys.exit(1)
    
    selected_cryptos = volatile_cryptos[:args.top_count]
    print(f"\nSelected {len(selected_cryptos)} cryptos for optimization:")
    for crypto in selected_cryptos:
        print(f"  {crypto['symbol']}: {crypto['price_change_percentage_24h']:.2f}%")
    
    # Run batch optimization
    print(f"\nStarting batch optimization with {args.strategy}")
    print(f"Trials per crypto: {args.n_trials}")
    
    try:
        result = engine.run_volatile_optimization(
            strategy_name=args.strategy,
            n_trials=args.n_trials,
            top_count=args.top_count,
            min_volatility=args.min_volatility
        )
        
        if result.get('success', True):
            print(f"\nBatch optimization completed successfully!")
            print(f"Total cryptos: {result.get('total_cryptos', 0)}")
            print(f"Successful optimizations: {result.get('successful_optimizations', 0)}")
            print(f"Failed optimizations: {result.get('failed_optimizations', 0)}")
            print(f"Total time: {result.get('total_time', 0):.2f} seconds")
            
            # Show best overall result
            best_overall = result.get('best_overall')
            if best_overall:
                crypto_info = best_overall.get('crypto_info', {})
                print(f"\nBest overall result:")
                print(f"  Crypto: {crypto_info.get('symbol', 'Unknown')} ({best_overall.get('crypto')})")
                print(f"  Profit: {best_overall.get('best_value', 'N/A')}%")
                print(f"  Parameters: {best_overall.get('best_params', {})}")
        else:
            print(f"Batch optimization failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nBatch optimization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Batch optimization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
