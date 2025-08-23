import optuna
import subprocess
import json
import argparse
import re
import numpy as np
import os
from pathlib import Path # Added this import
import random # Added this import

SEED = 42 # Define a fixed seed for reproducibility

# Calculate the project root dynamically
PROJECT_ROOT = Path(__file__).resolve().parent # Assuming optimize_bayesian.py is in the project root

def objective(trial, crypto, strategy):
    # Calculate maximum periods based on available data
    # With 7 days of data at 30min intervals: 7 * 24 * 2 = 336 data points
    # Leave some buffer for indicator calculations
    max_data_points = 300  # Conservative estimate
    
    # Define the search space with realistic bounds
    short_sma_period = trial.suggest_int('short_sma_period', 5, 50)
    long_sma_period = trial.suggest_int('long_sma_period', short_sma_period + 5, min(200, max_data_points // 2))
    
    short_ema_period = trial.suggest_int('short_ema_period', 5, 30)
    long_ema_period = trial.suggest_int('long_ema_period', short_ema_period + 1, min(100, max_data_points // 3))
    
    # RSI bounds - ensure overbought > oversold
    rsi_oversold = trial.suggest_int('rsi_oversold', 5, 35)
    rsi_overbought = trial.suggest_int('rsi_overbought', rsi_oversold + 20, 95)
    
    # MACD bounds - ensure fast < slow and all fit within data
    macd_fast_period = trial.suggest_int('macd_fast_period', 5, 25)
    macd_slow_period = trial.suggest_int('macd_slow_period', macd_fast_period + 5, min(50, max_data_points // 6))
    macd_signal_period = trial.suggest_int('macd_signal_period', 5, 20)
    
    # ATR bounds
    atr_period = trial.suggest_int('atr_period', 5, min(30, max_data_points // 10))

    params = {
        '--short-sma-period': short_sma_period,
        '--long-sma-period': long_sma_period,
        '--short-ema-period': short_ema_period,
        '--long-ema-period': long_ema_period,
        '--rsi-oversold': rsi_oversold,
        '--rsi-overbought': rsi_overbought,
        '--atr-period': atr_period,
        '--atr-multiple': trial.suggest_float('atr_multiple', 1.0, 5.0),
        '--fixed-stop-loss-percentage': trial.suggest_float('fixed_stop_loss_percentage', 0.005, 0.05),
        '--take-profit-multiple': trial.suggest_float('take_profit_multiple', 1.0, 5.0),
        '--macd-fast-period': macd_fast_period,
        '--macd-slow-period': macd_slow_period,
        '--macd-signal-period': macd_signal_period,
    }

    # Construct the command
    command = [
        'python', 'backtester.py',
        '--crypto', crypto,
        '--strategy', strategy,
        '--single-run'
    ]
    for param, value in params.items():
        command.extend([param, str(value)])

    # Run the backtester
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        output = process.stdout
        
        # Find the machine-readable output
        match = re.search(r"OPTIMIZER_RESULTS:(.*)", output)
        if match:
            results_json = match.group(1)
            results = json.loads(results_json)
            total_profit_loss = results.get('total_profit_loss', -1000000.0)
            
            # Additional penalty for strategies with very few trades
            total_trades = results.get('total_trades', 0)
            if total_trades < 2:  # Reduced from 5 to 2 - be less strict
                total_profit_loss -= 50.0  # Reduced penalty
            elif total_trades < 5:
                total_profit_loss -= 10.0  # Small penalty for few trades
                
            return total_profit_loss
        else:
            # No results found, this was a bad run
            return -1000000.0

    except subprocess.CalledProcessError as e:
        # The backtester script failed for some reason
        print(f"Backtester failed with error:\n{e.stderr}")
        return -1000000.0
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return -1000000.0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bayesian Optimizer for Crypto Backtester')
    parser.add_argument('--crypto', required=True, help='Cryptocurrency ID (e.g., ethereum)')
    parser.add_argument('--strategy', required=True, help='The trading strategy to use')
    parser.add_argument('--n-trials', type=int, default=100, help='Number of optimization trials to run.')
    args = parser.parse_args()

    # Set random seeds for reproducibility
    optuna.set_random_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)

    # Create a study object and optimize the function.
    study = optuna.create_study(direction='maximize')
    study.optimize(lambda trial: objective(trial, args.crypto, args.strategy), n_trials=args.n_trials)

    print("\n--- Optimization Finished ---")
    print(f"Number of finished trials: {len(study.trials)}")

    print("Best trial:")
    trial = study.best_trial

    print(f"  Value (Total Profit/Loss): {trial.value}")

    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")
        
    # Save best parameters to file
    best_params_dir = PROJECT_ROOT / "data" / "results" # Use PROJECT_ROOT for results directory
    os.makedirs(best_params_dir, exist_ok=True) # Ensure the directory exists
    best_params_file = best_params_dir / f"best_params_{args.crypto}_{args.strategy}_bayesian.json"
    with open(best_params_file, 'w') as f:
        json.dump({
            'best_profit_loss': trial.value,
            'best_params': trial.params,
            'n_trials': args.n_trials
        }, f, indent=2)
    print(f"\nBest parameters saved to: {best_params_file}")