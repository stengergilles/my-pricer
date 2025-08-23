#!/usr/bin/env python3

import requests
import json
import logging
from datetime import datetime
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def get_volatile_cryptos():
    """
    Get the most volatile cryptocurrencies from CoinGecko.
    Returns top gainers and losers separately.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 250,  # Get more coins to find volatile ones
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Filter out coins with None price change and very low market cap
        valid_coins = [
            coin for coin in data 
            if coin.get('price_change_percentage_24h') is not None 
            and coin.get('market_cap', 0) > 1000000  # At least $1M market cap
            and coin.get('current_price', 0) > 0.000001  # Avoid dust coins
        ]
        
        # Separate gainers and losers
        gainers = [coin for coin in valid_coins if coin['price_change_percentage_24h'] > 0]
        losers = [coin for coin in valid_coins if coin['price_change_percentage_24h'] < 0]
        
        # Sort by percentage change
        gainers.sort(key=lambda x: x['price_change_percentage_24h'], reverse=True)
        losers.sort(key=lambda x: x['price_change_percentage_24h'])
        
        print("🚀 TOP 10 GAINERS (24h):")
        print("-" * 60)
        for i, coin in enumerate(gainers[:10], 1):
            change = coin['price_change_percentage_24h']
            price = coin['current_price']
            mcap = coin['market_cap'] / 1e6  # Convert to millions
            print(f"{i:2d}. {coin['id']:<20} {change:+7.2f}% | ${price:>10.6f} | ${mcap:>6.1f}M")
        
        print("\n📉 TOP 10 LOSERS (24h):")
        print("-" * 60)
        for i, coin in enumerate(losers[:10], 1):
            change = coin['price_change_percentage_24h']
            price = coin['current_price']
            mcap = coin['market_cap'] / 1e6
            print(f"{i:2d}. {coin['id']:<20} {change:+7.2f}% | ${price:>10.6f} | ${mcap:>6.1f}M")
        
        # Return top 5 most volatile (mix of gainers and losers)
        top_volatile = []
        
        # Add top 3 gainers and top 2 losers
        if len(gainers) >= 3:
            top_volatile.extend(gainers[:3])
        if len(losers) >= 2:
            top_volatile.extend(losers[:2])
        
        # If we don't have enough, fill with most volatile overall
        if len(top_volatile) < 5:
            all_volatile = sorted(valid_coins, 
                                key=lambda x: abs(x['price_change_percentage_24h']), 
                                reverse=True)
            for coin in all_volatile:
                if coin not in top_volatile and len(top_volatile) < 5:
                    top_volatile.append(coin)
        
        print(f"\n🎯 SELECTED FOR OPTIMIZATION:")
        print("-" * 60)
        for i, coin in enumerate(top_volatile, 1):
            change = coin['price_change_percentage_24h']
            print(f"{i}. {coin['id']:<20} {change:+7.2f}%")
        
        return [coin['id'] for coin in top_volatile]
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko: {e}")
        return []

if __name__ == "__main__":
    volatile_cryptos = get_volatile_cryptos()
    
    if volatile_cryptos:
        print(f"\nCrypto IDs for optimization: {volatile_cryptos}")
        
        # Save to file for easy access
        results_dir = PROJECT_ROOT / "data" / "results"
        os.makedirs(results_dir, exist_ok=True)
        volatile_cryptos_file = results_dir / "volatile_cryptos.json"
        with open(volatile_cryptos_file, 'w') as f:
            json.dump({
                'timestamp': str(datetime.now()),
                'crypto_ids': volatile_cryptos
            }, f, indent=2)
        print(f"Saved to {volatile_cryptos_file}")
    else:
        print("Failed to fetch volatile cryptocurrencies.")
