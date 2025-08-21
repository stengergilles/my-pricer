import subprocess
import re
import os
import json
import argparse
import time
from datetime import datetime
import pprint

# --- Helper Functions for Config Modification ---
def get_param_sets_from_config():
    config_path = "config.py"
    with open(config_path, 'r') as f:
        config_content = f.read()
        
    param_sets_match = re.search(r"(param_sets = \{.*\}\n)", config_content, re.DOTALL)
    if not param_sets_match:
        raise ValueError("Could not find 'param_sets' in config.py")
    
    param_sets_full_str = param_sets_match.group(1) # This is the full string including "param_sets = " and trailing newline
    param_sets_dict_str = param_sets_full_str.replace("param_sets = ", "", 1).strip() # Extract just the dict string
    
    # Safely evaluate the string as a Python dictionary
    # WARNING: Using eval is generally unsafe with untrusted input.
    # Here, we control the input (config.py), so it's acceptable.
    param_sets_dict = eval(param_sets_dict_str) 
    
    return param_sets_dict, param_sets_full_str, config_content # Return the full string for replacement

def update_param_sets_in_config(new_param_sets_dict, old_param_sets_str, original_config_content):
    config_path = "config.py"
    
    # Use pprint to convert the dictionary back to a Python-compatible string
    # This handles tuples correctly and provides indentation.
    new_param_sets_dict_formatted_str = pprint.pformat(new_param_sets_dict, indent=4, width=120)
    
    # Replace the old param_sets string with the new one in the original content
    # The old_param_sets_str includes "param_sets = { ... }\n"
    # The new_param_sets_dict_formatted_str is just "{ ... }"
    # So we need to reconstruct the full string for replacement.
    new_param_sets_full_str = f"param_sets = {new_param_sets_dict_formatted_str}\n"

    modified_config_content = original_config_content.replace(old_param_sets_str, new_param_sets_full_str)
    
    with open(config_path, 'w') as f:
        f.write(modified_config_content)
    print(f"Updated config.py with new parameter ranges.")

# --- Main Adaptive Backtest Logic ---
def run_backtest_and_capture_warnings(crypto_id, strategy, param_set, num_samples):
    command = [
        "python", "backtester.py",
        "--crypto", crypto_id,
        "--strategy", strategy,
        "--param-set", param_set,
        "--num-samples", str(num_samples)
    ]
    
    process = subprocess.run(command, capture_output=True, text=True)
    
    warnings = []
    warning_pattern = re.compile(r"WARNING: Optimal parameter '(\w+)' \(([\d.]+)\) is at the boundary of its search range \(([\d.]+), ([\d.]+)\)\. Consider expanding this range in config.py\.")
    
    for line in process.stdout.splitlines() + process.stderr.splitlines():
        match = warning_pattern.search(line)
        if match:
            param_name, best_value_str, start_str, stop_str = match.groups()
            warnings.append({
                'param_name': param_name,
                'best_value': float(best_value_str),
                'start': float(start_str),
                'stop': float(stop_str)
            })
            
    return warnings, process.stdout, process.stderr

def adaptive_backtest(crypto_id, strategy, param_set, max_retries=3, expansion_factor=2, num_samples=1000, reset_param_set=None):
    print(f"--- Starting Adaptive Backtest for {crypto_id} ({strategy}, {param_set}) ---")
    print(f"Max retries: {max_retries}, Expansion factor: {expansion_factor}, Num samples: {num_samples}")
    print("WARNING: This script will modify your config.py file. It might alter formatting or remove comments within the 'param_sets' dictionary.")
    
    if reset_param_set:
        print(f"--- Resetting --param-set '{param_set}' for '{crypto_id}' using template from 'default_sets.{reset_param_set}' ---")
        param_sets_dict, param_sets_full_str, original_config_content = get_param_sets_from_config()

        if 'default_sets' not in param_sets_dict or reset_param_set not in param_sets_dict['default_sets']:
            print(f"Error: Template '{reset_param_set}' not found in 'default_sets' in config.py.")
            return False

        if crypto_id not in param_sets_dict:
            param_sets_dict[crypto_id] = {}
            print(f"Created new entry for crypto '{crypto_id}' in param_sets.")

        # Copy the template
        param_sets_dict[crypto_id][param_set] = param_sets_dict['default_sets'][reset_param_set]
        
        # Save the updated config
        update_param_sets_in_config(param_sets_dict, param_sets_full_str, original_config_content)
        print(f"Successfully reset '{param_set}' for '{crypto_id}'. Exiting.")
        return True # Exit after resetting

    target_param_ranges = None # Initialize here
    
    for attempt in range(1, max_retries + 1):
        print(f"\n--- Attempt {attempt}/{max_retries} ---")
        
        # Get current param_sets from config.py
        param_sets_dict, param_sets_full_str, original_config_content = get_param_sets_from_config()

        changes_made_to_config_for_creation = False
        # Check if the target param_set exists for the crypto, if not, create it
        if crypto_id not in param_sets_dict:
            param_sets_dict[crypto_id] = {}
            print(f"Created new entry for crypto '{crypto_id}' in param_sets.")
            changes_made_to_config_for_creation = True
        
        if param_set not in param_sets_dict[crypto_id]:
            # Copy from 'default_sets' -> 'tiny' as a template
            if 'default_sets' in param_sets_dict and 'tiny' in param_sets_dict['default_sets']:
                param_sets_dict[crypto_id][param_set] = param_sets_dict['default_sets']['tiny']
                print(f"Created param set '{param_set}' for '{crypto_id}' by copying from 'default_sets.tiny'.")
                changes_made_to_config_for_creation = True
            else:
                print(f"Error: Cannot create param set '{param_set}' for '{crypto_id}'. 'default_sets.tiny' not found as template.")
                return False # Cannot proceed without a template

        if changes_made_to_config_for_creation:
            update_param_sets_in_config(param_sets_dict, param_sets_full_str, original_config_content)
            time.sleep(1) # Give a moment for file system to update

        # Run backtest and capture warnings
        warnings, stdout, stderr = run_backtest_and_capture_warnings(crypto_id, strategy, param_set, num_samples)
        
        print("\n--- Backtest Output ---")
        print(stdout)
        if stderr:
            print("--- Backtest Errors ---")
            print(stderr)
        
        if not warnings:
            print("No boundary warnings found. Optimal parameters are within the search space.")
            print("Adaptive backtest completed successfully.")
            return True
        else:
            print(f"Found {len(warnings)} boundary warnings. Expanding ranges...")
            
            # Get current param_sets from config.py
            param_sets_dict, param_sets_str, original_config_content = get_param_sets_from_config()
            
            # Navigate to the specific param_set to modify
            target_param_ranges = None
            if 'default_sets' in param_sets_dict and param_set in param_sets_dict['default_sets']:
                target_param_ranges = param_sets_dict['default_sets'][param_set]
            elif 'bitcoin' in param_sets_dict and param_set in param_sets_dict['bitcoin']:
                target_param_ranges = param_sets_dict['bitcoin'][param_set]
            elif 'ethereum' in param_sets_dict and param_set in param_sets_dict['ethereum']:
                target_param_ranges = param_sets_dict['ethereum'][param_set]
            else:
                print(f"Error: Could not find param_set '{param_set}' in config.py. Cannot adapt.")
                return False

            changes_made = False
            # Define bounds for specific parameters
            bounded_params = {
                'rsi_overbought': (0, 100),
                'rsi_oversold': (0, 100),
                # Add other bounded parameters here if necessary, e.g.,
                # 'fixed_stop_loss_percentage': (0, 1.0),
                # 'take_profit_multiple': (0, 100.0), # Example, adjust max as needed
            }

            for warning in warnings:
                param_name = warning['param_name']
                best_value = warning['best_value']
                current_start = warning['start']
                current_stop = warning['stop']
                
                range_key = f"{param_name}_range"
                
                if range_key in target_param_ranges:
                    old_start, old_stop, old_step = target_param_ranges[range_key]
                    
                    new_start = old_start
                    new_stop = old_stop
                    
                    # Expand based on which boundary was hit
                    epsilon = 1e-9 # For floating point comparison
                    if abs(best_value - current_start) < epsilon: # Hit lower boundary
                        if param_name == 'fixed_stop_loss_percentage' and best_value == 0 and current_start == 0:
                            # Do not expand lower bound if it's fixed_stop_loss_percentage and already at 0
                            print(f"  Not expanding lower bound for '{param_name}' as it's already at 0.")
                        elif old_step > 0:
                            new_start = old_start - (old_step * expansion_factor)
                            if new_start < 0 and old_start >= 0: # Don't go negative if original was non-negative
                                new_start = 0
                            print(f"  Expanding '{param_name}' lower bound from {old_start} to {new_start}")
                            changes_made = True
                    
                    # (old_stop - old_step) is the last value in the range for np.arange
                    if abs(best_value - (current_stop - old_step)) < epsilon: # Hit upper boundary
                        if old_step > 0:
                            new_stop = old_stop + (old_step * expansion_factor)
                            print(f"  Expanding '{param_name}' upper bound from {old_stop} to {new_stop}")
                            changes_made = True
                    
                    if changes_made:
                        # Round to avoid floating point inaccuracies
                        new_start = round(new_start, 4)
                        new_stop = round(new_stop, 4)

                        # Apply bounds if parameter is constrained
                        if param_name in bounded_params:
                            min_bound, max_bound = bounded_params[param_name]
                            new_start = max(new_start, min_bound)
                            new_stop = min(new_stop, max_bound)

                        target_param_ranges[range_key] = (new_start, new_stop, old_step)
                        
            if changes_made:
                # Update the param_sets_dict with the modified target_param_ranges
                # This is already done by direct modification of target_param_ranges
                
                # Save the updated param_sets_dict back to config.py
                update_param_sets_in_config(param_sets_dict, param_sets_str, original_config_content)
                print("Ranges expanded. Retrying backtest...")
                time.sleep(1) # Give a moment before next run
            else:
                print("No changes made to ranges, but warnings were present. This should not happen if warnings were parsed correctly.")
                return False # Something went wrong, or no relevant ranges found

    print("\nAdaptive backtest finished after max retries. Check final results and warnings.")
    return False # Did not complete successfully within max retries

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Adaptive Backtester')
    parser.add_argument('--crypto', required=True, help='Cryptocurrency ID (e.g., ethereum)')
    parser.add_argument('--strategy', required=True, help='The trading strategy to use (e.g., Combined_Trigger_Verifier)')
    parser.add_argument('--param-set', required=True, help='The parameter set to use (e.g., tiny)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of times to retry backtest and expand ranges.')
    parser.add_argument('--expansion-factor', type=float, default=2, help='Factor by which to expand the range (e.g., 2 means expand by 2*step).')
    parser.add_argument('--num-samples', type=int, default=1000, help='Number of random samples for the backtest (for random search).')
    parser.add_argument('--reset-param-set', type=str, help='If provided, reset the specified --param-set for --crypto by copying from this default_sets template (e.g., "tiny", "small").')
    
    args = parser.parse_args()
    
    adaptive_backtest(args.crypto, args.strategy, args.param_set, args.max_retries, args.expansion_factor, args.num_samples, args.reset_param_set)