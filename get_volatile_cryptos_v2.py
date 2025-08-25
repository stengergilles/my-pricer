#!/usr/bin/env python3
"""
Simplified volatile crypto discovery using unified core.
Replaces the original get_volatile_cryptos.py with cleaner architecture.
"""

import argparse
import json
import sys
from core.trading_engine import TradingEngine

def main():
    parser = argparse.ArgumentParser(description='Discover volatile cryptocurrencies')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of cryptos to fetch')
    parser.add_argument('--min-volatility', type=float, default=5.0, help='Minimum volatility threshold (percent)')
    parser.add_argument('--top-movers', type=int, help='Show top N gainers and losers')
    parser.add_argument('--search', help='Search for specific crypto by name/symbol')
    parser.add_argument('--output', choices=['json', 'table'], default='table', help='Output format')
    
    args = parser.parse_args()
    
    # Initialize trading engine
    engine = TradingEngine()
    
    try:
        if args.search:
            # Search for specific crypto
            results = engine.search_cryptos(args.search, limit=10)
            
            if args.output == 'json':
                print(json.dumps(results, indent=2))
            else:
                print(f"\nSearch results for '{args.search}':")
                print("-" * 60)
                for crypto in results:
                    print(f"{crypto.get('symbol', 'N/A'):>8} | {crypto.get('name', 'N/A'):<30} | {crypto.get('id', 'N/A')}")
        
        elif args.top_movers:
            # Get top movers
            movers = engine.get_top_movers(count=args.top_movers)
            
            if args.output == 'json':
                print(json.dumps(movers, indent=2))
            else:
                print(f"\nTop {args.top_movers} Gainers:")
                print("-" * 60)
                for crypto in movers.get('gainers', []):
                    change = crypto.get('price_change_percentage_24h', 0)
                    print(f"{crypto.get('symbol', 'N/A'):>8} | {change:>8.2f}% | {crypto.get('name', 'N/A')}")
                
                print(f"\nTop {args.top_movers} Losers:")
                print("-" * 60)
                for crypto in movers.get('losers', []):
                    change = crypto.get('price_change_percentage_24h', 0)
                    print(f"{crypto.get('symbol', 'N/A'):>8} | {change:>8.2f}% | {crypto.get('name', 'N/A')}")
        
        else:
            # Get volatile cryptos
            volatile_cryptos = engine.get_volatile_cryptos(
                min_volatility=args.min_volatility,
                limit=args.limit
            )
            
            if not volatile_cryptos:
                print("No volatile cryptocurrencies found!")
                sys.exit(1)
            
            if args.output == 'json':
                print(json.dumps(volatile_cryptos, indent=2))
            else:
                print(f"\nVolatile Cryptocurrencies (min {args.min_volatility}% change):")
                print("-" * 80)
                print(f"{'Symbol':>8} | {'Change %':>10} | {'Price':>12} | {'Name'}")
                print("-" * 80)
                
                for crypto in volatile_cryptos:
                    symbol = crypto.get('symbol', 'N/A')
                    change = crypto.get('price_change_percentage_24h', 0)
                    price = crypto.get('current_price', 0)
                    name = crypto.get('name', 'N/A')[:30]
                    
                    print(f"{symbol:>8} | {change:>9.2f}% | ${price:>10.4f} | {name}")
                
                print(f"\nTotal: {len(volatile_cryptos)} cryptocurrencies")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
