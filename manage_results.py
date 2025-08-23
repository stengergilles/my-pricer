#!/usr/bin/env python3

import os
import json
import glob
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_BASE_DIR = PROJECT_ROOT / "data" / "results"

def list_backtest_results():
    """
    List and organize all backtest results in the backtest_results folder.
    """
    
    results_dir = RESULTS_BASE_DIR # Use the defined base directory
    
    if not os.path.exists(results_dir):
        print(f"❌ Results directory '{results_dir}' not found.")
        return
    
    print("📊 BACKTEST RESULTS SUMMARY")
    print("=" * 60)
    
    # Get all result files
    bayesian_files = glob.glob(str(results_dir / "best_params_*_bayesian.json"))
    volatile_files = glob.glob(str(results_dir / "volatile_optimization_results_*.json"))
    crypto_files = glob.glob(str(results_dir / "volatile_cryptos.json"))
    
    # Display Bayesian optimization results
    if bayesian_files:
        print("\n🎯 BAYESIAN OPTIMIZATION RESULTS:")
        print("-" * 40)
        
        for file_path in sorted(bayesian_files):
            filename = os.path.basename(file_path)
            # Parse filename: best_params_crypto_strategy_bayesian.json
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 4:
                crypto = parts[2]
                strategy = parts[3]
                
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    profit = data.get('best_profit_loss', 0)
                    trials = data.get('n_trials', 0)
                    
                    print(f"  📈 {crypto.upper()} ({strategy}): {profit:+.2f} profit ({trials} trials)")
                    
                except Exception as e:
                    print(f"  ❌ Error reading {filename}: {e}")
    
    # Display volatile crypto optimization results
    if volatile_files:
        print("\n🚀 VOLATILE CRYPTO OPTIMIZATION RESULTS:")
        print("-" * 40)
        
        for file_path in sorted(volatile_files, reverse=True):  # Most recent first
            filename = os.path.basename(file_path)
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', 'Unknown')
                strategy = data.get('strategy', 'Unknown')
                results = data.get('results', [])
                
                print(f"\n  📅 {timestamp} ({strategy} strategy):")
                
                # Show top results
                successful_results = [r for r in results if r.get('best_value') is not None and r.get('best_value') > -1000000]
                if successful_results:
                    successful_results.sort(key=lambda x: x['best_value'], reverse=True)
                    for result in successful_results[:3]:  # Top 3
                        crypto = result['crypto_id']
                        profit = result['best_value']
                        print(f"    🏆 {crypto.upper()}: {profit:+.2f} profit")
                else:
                    print(f"    ❌ No profitable results found")
                    
            except Exception as e:
                print(f"  ❌ Error reading {filename}: {e}")
    
    # Display volatile crypto lists
    if crypto_files:
        print("\n📋 LATEST VOLATILE CRYPTOS:")
        print("-" * 40)
        
        try:
            with open(crypto_files[0], 'r') as f:
                data = json.load(f)
            
            timestamp = data.get('timestamp', 'Unknown')
            crypto_ids = data.get('crypto_ids', [])
            
            print(f"  📅 Last updated: {timestamp}")
            print(f"  🎯 Selected cryptos: {', '.join(crypto_ids)}")
            
        except Exception as e:
            print(f"  ❌ Error reading volatile cryptos: {e}")
    
    # Summary statistics
    print(f"\n📊 SUMMARY:")
    print(f"  • Bayesian results: {len(bayesian_files)} files")
    print(f"  • Volatile optimizations: {len(volatile_files)} files")
    print(f"  • Crypto lists: {len(crypto_files)} files")
    print(f"  • Total files: {len(bayesian_files) + len(volatile_files) + len(crypto_files)}")

def clean_old_results(days_old=7):
    """
    Clean up old result files older than specified days.
    """
    
    results_dir = RESULTS_BASE_DIR # Use the defined base directory
    
    if not os.path.exists(results_dir):
        print(f"❌ Results directory '{results_dir}' not found.")
        return
    
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    
    all_files = glob.glob(str(results_dir / "*"))
    old_files = []
    
    for file_path in all_files:
        if os.path.getmtime(file_path) < cutoff_time:
            old_files.append(file_path)
    
    if old_files:
        print(f"🗑️  Found {len(old_files)} files older than {days_old} days:")
        for file_path in old_files:
            print(f"  • {os.path.basename(file_path)}")
        
        confirm = input(f"\nDelete these files? (y/N): ")
        if confirm.lower() == 'y':
            for file_path in old_files:
                os.remove(file_path)
                print(f"  ✅ Deleted {os.path.basename(file_path)}")
        else:
            print("  ❌ Cleanup cancelled")
    else:
        print(f"✅ No files older than {days_old} days found")

def show_best_performers():
    """
    Show the best performing strategies across all results.
    """
    
    results_dir = RESULTS_BASE_DIR # Use the defined base directory
    
    if not os.path.exists(results_dir):
        print(f"❌ Results directory '{results_dir}' not found.")
        return
    
    print("🏆 TOP PERFORMING STRATEGIES")
    print("=" * 60)
    
    all_results = []
    
    # Collect all Bayesian results
    bayesian_files = glob.glob(str(results_dir / "best_params_*_bayesian.json"))
    for file_path in bayesian_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            filename = os.path.basename(file_path)
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 4:
                crypto = parts[2]
                strategy = parts[3]
                profit = data.get('best_profit_loss', 0)
                
                all_results.append({
                    'crypto': crypto,
                    'strategy': strategy,
                    'profit': profit,
                    'type': 'Bayesian',
                    'file': filename
                })
        except:
            continue
    
    # Collect volatile optimization results
    volatile_files = glob.glob(str(results_dir / "volatile_optimization_results_*.json"))
    for file_path in volatile_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            strategy = data.get('strategy', 'Unknown')
            
            for result in results:
                if result.get('best_value') is not None and result.get('best_value') > -1000000:
                    all_results.append({
                        'crypto': result['crypto_id'],
                        'strategy': strategy,
                        'profit': result['best_value'],
                        'type': 'Volatile',
                        'file': os.path.basename(file_path)
                    })
        except:
            continue
    
    # Sort by profit and show top performers
    all_results.sort(key=lambda x: x['profit'], reverse=True)
    
    if all_results:
        print("🥇 TOP 10 STRATEGIES:")
        print("-" * 40)
        
        for i, result in enumerate(all_results[:10], 1):
            crypto = result['crypto'].upper()
            strategy = result['strategy']
            profit = result['profit']
            opt_type = result['type']
            
            print(f"{i:2d}. {crypto:<12} {strategy:<20} {profit:+8.2f} ({opt_type})")
    else:
        print("❌ No results found")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage backtest results')
    parser.add_argument('--list', action='store_true', help='List all results')
    parser.add_argument('--clean', type=int, metavar='DAYS', help='Clean files older than DAYS')
    parser.add_argument('--top', action='store_true', help='Show top performing strategies')
    
    args = parser.parse_args()
    
    if args.list:
        list_backtest_results()
    elif args.clean:
        clean_old_results(args.clean)
    elif args.top:
        show_best_performers()
    else:
        # Default: show list
        list_backtest_results()
