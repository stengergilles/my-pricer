#!/usr/bin/env python3
"""
Simplified Bayesian optimization script using unified core.
Replaces the original optimize_bayesian.py with cleaner architecture.
"""

import argparse
import logging
import sys
from core.trading_engine import TradingEngine
from core.logger_config import setup_logging
from core.app_config import Config

def main():
    parser = argparse.ArgumentParser(description='Bayesian optimization for crypto trading strategies')
    parser.add_argument('--crypto', required=True, help='Cryptocurrency ID (e.g., bitcoin)')
    parser.add_argument('--strategy', required=True, help='Trading strategy name')
    parser.add_argument('--n-trials', type=int, default=50, help='Number of optimization trials')
    parser.add_argument('--timeout', type=int, help='Timeout in seconds (optional)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    config_obj = Config()
    setup_logging(config_obj)
    
    # Initialize trading engine
    engine = TradingEngine()
    
    # Validate strategy
    available_strategies = [s['name'] for s in engine.get_strategies()]
    if args.strategy not in available_strategies:
        print(f"Error: Unknown strategy '{args.strategy}'")
        print(f"Available strategies: {', '.join(available_strategies)}")
        sys.exit(1)
    
    # Run optimization
    print(f"Starting optimization for {args.crypto} with {args.strategy}")
    print(f"Trials: {args.n_trials}, Timeout: {args.timeout or 'None'}")
    
    try:
        result = engine.run_optimization(
            crypto_id=args.crypto,
            strategy_name=args.strategy,
            n_trials=args.n_trials,
            timeout=args.timeout
        )
        
        if result.get('success', True):
            print(f"\nOptimization completed successfully!")
            print(f"Best value: {result.get('best_value', 'N/A')}")
            print(f"Best parameters: {result.get('best_params', {})}")
            print(f"Total trials: {result.get('n_trials', 0)}")
            print(f"Optimization time: {result.get('optimization_time', 0):.2f} seconds")
        else:
            print(f"Optimization failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOptimization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Optimization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
