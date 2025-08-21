#!/usr/bin/env python3

import requests
import json
import subprocess
import argparse
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_top_volatile_cryptos(limit=50):
    """
    Fetch top volatile cryptocurrencies from CoinGecko based on 24h price change.
    Returns both top gainers and top losers.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Filter out coins with None price change
        valid_coins = [coin for coin in data if coin.get('price_change_percentage_24h') is not None]
        
        # Sort by absolute price change to get most volatile
        volatile_coins = sorted(valid_coins, 
                              key=lambda x: abs(x.get('price_change_percentage_24h', 0)), 
                              reverse=True)
        
        logging.info(f"Fetched {len(volatile_coins)} coins from CoinGecko")
        return volatile_coins
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from CoinGecko: {e}")
        return []

def select_top_volatile(coins, count=5):
    """
    Select top volatile coins, mixing gainers and losers.
    """
    if not coins:
        return []
    
    # Separate gainers and losers
    gainers = [coin for coin in coins if coin.get('price_change_percentage_24h', 0) > 0]
    losers = [coin for coin in coins if coin.get('price_change_percentage_24h', 0) < 0]
    
    # Sort gainers by highest gain, losers by biggest loss
    gainers.sort(key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)
    losers.sort(key=lambda x: x.get('price_change_percentage_24h', 0))
    
    selected = []
    
    # Alternate between gainers and losers to get variety
    gainer_idx = 0
    loser_idx = 0
    
    for i in range(count):
        if i % 2 == 0 and gainer_idx < len(gainers):
            # Pick a gainer
            selected.append(gainers[gainer_idx])
            gainer_idx += 1
        elif loser_idx < len(losers):
            # Pick a loser
            selected.append(losers[loser_idx])
            loser_idx += 1
        elif gainer_idx < len(gainers):
            # Fallback to gainers if no more losers
            selected.append(gainers[gainer_idx])
            gainer_idx += 1
    
    return selected

def run_bayesian_optimization(crypto_id, strategy, n_trials=50):
    """
    Run Bayesian optimization for a specific crypto and strategy.
    """
    logging.info(f"Starting Bayesian optimization for {crypto_id} with strategy {strategy}")
    
    command = [
        'python', 'optimize_bayesian.py',
        '--crypto', crypto_id,
        '--strategy', strategy,
        '--n-trials', str(n_trials)
    ]
    
    try:
        start_time = time.time()
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        end_time = time.time()
        
        logging.info(f"Optimization completed for {crypto_id} in {end_time - start_time:.1f} seconds")
        
        # Extract best result from output
        output_lines = result.stdout.split('\n')
        best_value = None
        best_params = {}
        
        for i, line in enumerate(output_lines):
            if "Value (Total Profit/Loss):" in line:
                try:
                    best_value = float(line.split(':')[1].strip())
                except:
                    pass
            elif "Params:" in line and i + 1 < len(output_lines):
                # Parse parameters from following lines
                j = i + 1
                while j < len(output_lines) and output_lines[j].strip().startswith('    '):
                    param_line = output_lines[j].strip()
                    if ':' in param_line:
                        key, value = param_line.split(':', 1)
                        try:
                            best_params[key.strip()] = float(value.strip())
                        except:
                            best_params[key.strip()] = value.strip()
                    j += 1
                break
        
        return {
            'crypto_id': crypto_id,
            'strategy': strategy,
            'best_value': best_value,
            'best_params': best_params,
            'execution_time': end_time - start_time,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Optimization failed for {crypto_id}: {e}")
        return {
            'crypto_id': crypto_id,
            'strategy': strategy,
            'best_value': None,
            'error': str(e),
            'stderr': e.stderr if hasattr(e, 'stderr') else ''
        }

def main():
    parser = argparse.ArgumentParser(description='Optimize volatile cryptocurrencies')
    parser.add_argument('--strategy', default='EMA_Only', 
                       help='Trading strategy to use (default: EMA_Only)')
    parser.add_argument('--n-trials', type=int, default=30,
                       help='Number of Bayesian optimization trials per crypto (default: 30)')
    parser.add_argument('--top-count', type=int, default=5,
                       help='Number of top volatile cryptos to optimize (default: 5)')
    parser.add_argument('--market-cap-limit', type=int, default=100,
                       help='Number of top market cap coins to consider (default: 100)')
    
    args = parser.parse_args()
    
    logging.info("=== Volatile Crypto Optimizer Started ===")
    logging.info(f"Strategy: {args.strategy}")
    logging.info(f"Trials per crypto: {args.n_trials}")
    logging.info(f"Top volatile count: {args.top_count}")
    
    # Step 1: Get volatile cryptocurrencies
    logging.info("Fetching volatile cryptocurrencies from CoinGecko...")
    all_coins = get_top_volatile_cryptos(args.market_cap_limit)
    
    if not all_coins:
        logging.error("Failed to fetch cryptocurrency data. Exiting.")
        return
    
    # Step 2: Select top volatile ones
    selected_coins = select_top_volatile(all_coins, args.top_count)
    
    logging.info("Selected volatile cryptocurrencies:")
    for coin in selected_coins:
        change = coin.get('price_change_percentage_24h', 0)
        logging.info(f"  {coin['id']}: {change:+.2f}% (${coin.get('current_price', 0):.4f})")
    
    # Step 3: Run optimization for each selected crypto
    results = []
    total_start_time = time.time()
    
    for i, coin in enumerate(selected_coins, 1):
        crypto_id = coin['id']
        change = coin.get('price_change_percentage_24h', 0)
        
        logging.info(f"\n--- Optimizing {i}/{len(selected_coins)}: {crypto_id} ({change:+.2f}%) ---")
        
        result = run_bayesian_optimization(crypto_id, args.strategy, args.n_trials)
        results.append(result)
        
        # Add a small delay to be nice to APIs
        time.sleep(2)
    
    total_end_time = time.time()
    
    # Step 4: Summary and results
    logging.info("\n" + "="*60)
    logging.info("OPTIMIZATION RESULTS SUMMARY")
    logging.info("="*60)
    
    # Sort results by best value (highest profit)
    successful_results = [r for r in results if r.get('best_value') is not None]
    successful_results.sort(key=lambda x: x['best_value'], reverse=True)
    
    if successful_results:
        logging.info("Top performing cryptocurrencies:")
        for i, result in enumerate(successful_results, 1):
            logging.info(f"{i}. {result['crypto_id']}: {result['best_value']:.2f} profit/loss")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"backtest_results/volatile_optimization_results_{timestamp}.json"
    
    summary = {
        'timestamp': timestamp,
        'strategy': args.strategy,
        'n_trials': args.n_trials,
        'top_count': args.top_count,
        'total_execution_time': total_end_time - total_start_time,
        'selected_coins': [{'id': coin['id'], 'change_24h': coin.get('price_change_percentage_24h')} 
                          for coin in selected_coins],
        'results': results
    }
    
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(f"\nDetailed results saved to: {results_file}")
    logging.info(f"Total execution time: {total_end_time - total_start_time:.1f} seconds")
    
    if successful_results:
        best_crypto = successful_results[0]
        logging.info(f"\nBest performing crypto: {best_crypto['crypto_id']} with {best_crypto['best_value']:.2f} profit/loss")
        
        # Show best parameters for the top performer
        if best_crypto.get('best_params'):
            logging.info("Best parameters:")
            for param, value in best_crypto['best_params'].items():
                if isinstance(value, float):
                    logging.info(f"  {param}: {value:.4f}")
                else:
                    logging.info(f"  {param}: {value}")

if __name__ == "__main__":
    main()
