import json
import os
import argparse
from datetime import datetime

def compare_performance(crypto_id, param_set):
    print(f"--- Comparing Backtest vs. Live Performance for {crypto_id} ({param_set}) ---")

    # --- 1. Load Backtest Results ---
    backtest_filename = os.path.join("backtest_results", f"best_params_{crypto_id}_1_30m_{param_set}.json") # Assuming 1_30m from config.py
    backtest_data = None
    if os.path.exists(backtest_filename):
        try:
            with open(backtest_filename, 'r') as f:
                loaded_json = json.load(f)
                backtest_data = loaded_json.get('results')
            print(f"Loaded backtest results from: {backtest_filename}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from backtest file: {backtest_filename}")
    else:
        print(f"Backtest results not found at: {backtest_filename}")

    # --- 2. Load Latest Live Results ---
    live_results_base_dir = os.path.join("live_results", crypto_id)
    latest_live_data = None
    latest_timestamp = None
    latest_live_filename = None

    if os.path.exists(live_results_base_dir):
        for run_dir in sorted(os.listdir(live_results_base_dir), reverse=True): # Sort to get latest
            full_run_dir = os.path.join(live_results_base_dir, run_dir)
            if os.path.isdir(full_run_dir):
                live_filename = os.path.join(full_run_dir, "results.json")
                if os.path.exists(live_filename):
                    try:
                        with open(live_filename, 'r') as f:
                            live_data = json.load(f)
                        # Extract timestamp from directory name (e.g., 20250820_072215_to_...)
                        try:
                            dir_start_time_str = run_dir.split('_to_')[0]
                            current_timestamp = datetime.strptime(dir_start_time_str, "%Y%m%d_%H%M%S")
                            if latest_timestamp is None or current_timestamp > latest_timestamp:
                                latest_timestamp = current_timestamp
                                latest_live_data = live_data
                                latest_live_filename = live_filename
                        except ValueError:
                            print(f"Warning: Could not parse timestamp from directory name: {run_dir}")
                            continue
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from live results file: {live_filename}")
    
    if latest_live_data:
        print(f"Loaded latest live results from: {latest_live_filename}")
    else:
        print(f"No live results found for {crypto_id}.")

    # --- 3. Compare and Report ---
    print("\n--- Comparison ---")
    if backtest_data and latest_live_data:
        print(f"{'Metric':<20} {'Backtest':>15} {'Live':>15}")
        print("-" * 50)
        
        metrics = [
            ('total_profit_loss', 'Total P/L'),
            ('num_trades', 'Total Trades'),
            ('win_rate', 'Win Rate (%)'),
            ('final_capital', 'Final Capital')
        ]

        for key, display_name in metrics:
            bt_val = backtest_data.get(key, 'N/A')
            live_val = latest_live_data.get(key, 'N/A')
            
            # Format percentages
            if 'Win Rate' in display_name and isinstance(bt_val, (int, float)) and isinstance(live_val, (int, float)):
                print(f"{display_name:<20} {bt_val:>15.2f} {live_val:>15.2f}")
            elif isinstance(bt_val, (int, float)) and isinstance(live_val, (int, float)):
                print(f"{display_name:<20} {bt_val:>15.2f} {live_val:>15.2f}")
            else:
                print(f"{display_name:<20} {str(bt_val):>15} {str(live_val):>15}")

        # Qualitative assessment
        print("\n--- Qualitative Assessment ---")
        bt_profit = backtest_data.get('total_profit_loss', 0)
        live_profit = latest_live_data.get('total_profit_loss', 0)
        
        if live_profit >= bt_profit * 0.8: # Within 80% of backtest profit
            print("Live performance is reasonably close to backtest performance (within 80% of P/L).")
        elif live_profit > 0 and bt_profit > 0:
            print("Live performance is positive but significantly lower than backtest performance.")
        elif live_profit <= 0 and bt_profit > 0:
            print("Live performance is negative, while backtest was profitable. Potential overfitting or major discrepancy.")
        elif live_profit <= 0 and bt_profit <= 0:
            print("Both live and backtest performance are not profitable.")
        else:
            print("Comparison inconclusive due to missing data or unusual results.")

    else:
        print("Cannot perform full comparison: Missing either backtest or live results.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compare Backtest and Live Performance')
    parser.add_argument('--crypto', required=True, help='Cryptocurrency ID (e.g., ethereum)')
    parser.add_argument('--param-set', required=True, help='Parameter set used for backtest (e.g., tiny)')
    args = parser.parse_args()

    compare_performance(args.crypto, args.param_set)
