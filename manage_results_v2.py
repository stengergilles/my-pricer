#!/usr/bin/env python3
"""
Simplified results management using unified core.
Replaces the original manage_results.py with cleaner architecture.
"""

import argparse
import json
import sys
from core.trading_engine import TradingEngine

from core.logger_config import setup_logging

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Manage optimization and backtest results')
    parser.add_argument('--top', type=int, default=10, help='Show top N results')
    parser.add_argument('--crypto', help='Filter by specific crypto')
    parser.add_argument('--strategy', help='Filter by specific strategy')
    parser.add_argument('--list', action='store_true', help='List all results')
    parser.add_argument('--output', choices=['json', 'table'], default='table', help='Output format')
    
    args = parser.parse_args()
    
    # Initialize trading engine
    engine = TradingEngine()
    
    try:
        if args.list:
            # Get all results
            results = engine.get_all_results()
            
            # Apply filters
            if args.crypto:
                results = [r for r in results if r.get('crypto') == args.crypto]
            if args.strategy:
                results = [r for r in results if r.get('strategy') == args.strategy]
            
            if args.output == 'json':
                print(json.dumps(results, indent=2))
            else:
                print(f"\nAll Results ({len(results)} total):")
                print("-" * 100)
                print(f"{'Crypto':>12} | {'Strategy':>20} | {'Profit %':>10} | {'Trials':>8} | {'Date'}")
                print("-" * 100)
                
                for result in results:
                    crypto = result.get('crypto', 'N/A')[:12]
                    strategy = result.get('strategy', 'N/A')[:20]
                    profit = result.get('best_value', 0)
                    trials = result.get('n_trials', 0)
                    timestamp = result.get('timestamp', 'N/A')[:10]
                    
                    print(f"{crypto:>12} | {strategy:>20} | {profit:>9.2f}% | {trials:>8} | {timestamp}")
        
        else:
            # Get top results
            results = engine.get_top_results(limit=args.top)
            
            # Apply filters
            if args.crypto:
                results = [r for r in results if r.get('crypto') == args.crypto]
            if args.strategy:
                results = [r for r in results if r.get('strategy') == args.strategy]
            
            if not results:
                print("No results found matching the criteria.")
                sys.exit(0)
            
            if args.output == 'json':
                print(json.dumps(results, indent=2))
            else:
                print(f"\nTop {len(results)} Results:")
                print("-" * 120)
                print(f"{'Rank':>4} | {'Crypto':>12} | {'Strategy':>20} | {'Profit %':>10} | {'Trials':>8} | {'Best Parameters'}")
                print("-" * 120)
                
                for i, result in enumerate(results, 1):
                    crypto = result.get('crypto', 'N/A')[:12]
                    strategy = result.get('strategy', 'N/A')[:20]
                    profit = result.get('best_value', 0)
                    trials = result.get('n_trials', 0)
                    
                    # Format best parameters
                    best_params = result.get('best_params', {})
                    params_str = ', '.join([f"{k}={v}" for k, v in list(best_params.items())[:3]])
                    if len(best_params) > 3:
                        params_str += "..."
                    
                    print(f"{i:>4} | {crypto:>12} | {strategy:>20} | {profit:>9.2f}% | {trials:>8} | {params_str}")
                
                # Show detailed info for top result
                if results:
                    top_result = results[0]
                    print(f"\nTop Result Details:")
                    print(f"Crypto: {top_result.get('crypto')}")
                    print(f"Strategy: {top_result.get('strategy')}")
                    print(f"Profit: {top_result.get('best_value')}%")
                    print(f"Optimization Time: {top_result.get('optimization_time', 0):.2f} seconds")
                    print(f"Best Parameters:")
                    for param, value in top_result.get('best_params', {}).items():
                        print(f"  {param}: {value}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
