"""
Unified Bayesian optimization engine.
Consolidates logic from optimize_bayesian.py and volatile_crypto_optimizer.py.
"""

import optuna
import optuna.exceptions
import subprocess
import json
import logging
import os
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import job_status_manager # Added import

class JobStopRequestedError(Exception):
    """Custom exception to signal that a job stop has been requested."""
    pass

class CoinGeckoRateLimitError(Exception):
    """Custom exception for CoinGecko API rate limit errors."""
    pass

class RateLimitStopper:
    """Optuna callback to stop optimization on CoinGecko rate limit errors."""
    def __init__(self, logger):
        self.logger = logger

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        if trial.state == optuna.trial.TrialState.FAIL and isinstance(trial.exception, CoinGeckoRateLimitError):
            self.logger.error(f"Stopping optimization due to CoinGecko API rate limit: {trial.exception}")
            raise optuna.exceptions.OptunaError("CoinGecko API rate limit encountered. Stopping optimization.")

from .parameter_manager import ParameterManager
from .crypto_discovery import CryptoDiscovery

class BayesianOptimizer:
    """
    Unified Bayesian optimization for trading strategies.
    Handles both single crypto and batch optimization.
    """
    
    def __init__(self, 
                 results_dir: str = "backtest_results",
                 backtester_path: str = None,
                 seed: int = 42,
                 logger: logging.Logger = None):
        """
        Initialize optimizer.
        
        Args:
            results_dir: Directory to store optimization results
            backtester_path: Path to backtester script
            seed: Random seed for reproducibility
            logger: Optional logger instance
        """
        self.results_dir = results_dir
        # Resolve backtester_path to an absolute path relative to the project root
        # Assuming the project root is the parent of 'core' directory
        project_root = Path(__file__).parent.parent
        self.backtester_path = backtester_path or str(project_root / "backtester.py")
        self.seed = seed
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.param_manager = ParameterManager()
        self.crypto_discovery = CryptoDiscovery(results_dir)
        
        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)
        
        # Set random seeds
        random.seed(seed)
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    def optimize_single_crypto(self, 
                             crypto: str, 
                             strategy: str, 
                             n_trials: int = 50,
                             timeout: Optional[int] = None,
                             job_id: str = None) -> Dict[str, Any]: # Added job_id
        if timeout is not None:
            try:
                timeout = int(timeout) # Ensure timeout is an integer
            except ValueError:
                self.logger.error(f"Invalid timeout value: {timeout}. Must be an integer.")
                raise
        """
        Optimize parameters for a single cryptocurrency and strategy.
        
        Args:
            crypto: Cryptocurrency identifier
            strategy: Trading strategy name
            n_trials: Number of optimization trials
            timeout: Timeout in seconds (optional)
            job_id: Optional job ID for process tracking # Added job_id doc
            
        Returns:
            Optimization results dictionary
        """
        self.logger.info(f"Starting optimization: {crypto} with {strategy} ({n_trials} trials)")
        
        # Validate strategy
        if strategy not in self.param_manager.get_available_strategies():
            self.logger.error(f"Unknown strategy: {strategy}")
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Create study
        study_name = f"{crypto}_{strategy}_{int(time.time())}"
        study = optuna.create_study(
            direction='maximize',
            study_name=study_name,
            sampler=optuna.samplers.TPESampler(seed=self.seed)
        )
        
        # Define objective function
        def objective(trial):
            return self._objective_function(trial, crypto, strategy, job_id) # Added job_id
        
        # Run optimization
        start_time = time.time()
        try:
            stopper = RateLimitStopper(self.logger)
            study.optimize(objective, n_trials=n_trials, timeout=timeout, callbacks=[stopper])
        except KeyboardInterrupt:
            self.logger.warning("Optimization interrupted by user")
            raise # Re-raise to stop the study
        except JobStopRequestedError as e: # Catch our custom stop exception
            self.logger.info(f"Optimization for {crypto} stopped by user request: {e}")
            raise optuna.exceptions.OptunaError("Optimization stopped by user request.") # Stop the Optuna study
        except CoinGeckoRateLimitError as e:
            self.logger.error(f"Optimization stopped due to rate limit: {e}")
            raise # Re-raise the exception to propagate it
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}", exc_info=True)
            raise
        
        end_time = time.time()

        # Check if optimization stopped due to rate limit
        consecutive_rate_limit_failures = 0
        for t in reversed(study.trials):
            if t.state == optuna.trial.TrialState.FAIL and math.isnan(t.value) and t.user_attrs.get("rate_limit_hit"):
                consecutive_rate_limit_failures += 1
            else:
                break

        if consecutive_rate_limit_failures >= 3: # Stop after 3 consecutive rate limit failures
            self.logger.error("Optimization stopped due to persistent CoinGecko API rate limit.")
            return {
                'crypto': crypto,
                'strategy': strategy,
                'error': "Optimization stopped due to persistent CoinGecko API rate limit.",
                'timestamp': datetime.now().isoformat(),
                'n_trials': len(study.trials),
                'best_value': None,
                'best_params': {},
                'optimization_time': end_time - start_time,
                'study_name': study_name,
                'all_trials': []
            }
        
        # Compile results
        results = {
            'crypto': crypto,
            'strategy': strategy,
            'n_trials': len(study.trials),
            'best_value': study.best_value if study.best_trial else None,
            'best_params': study.best_params if study.best_trial else {},
            'optimization_time': end_time - start_time,
            'timestamp': datetime.now().isoformat(),
            'study_name': study_name,
            'all_trials': [
                {
                    'number': trial.number,
                    'value': trial.value,
                    'params': trial.params,
                    'state': trial.state.name
                }
                for trial in study.trials
            ]
        }
        
        # Save results
        self._save_optimization_results(results)
        
        self.logger.info(f"Optimization completed. Best value: {results['best_value']}")
        return results
    
    def optimize_volatile_cryptos(self, 
                                strategy: str, 
                                n_trials: int = 30,
                                top_count: int = 10,
                                min_volatility: float = 5.0,
                                max_workers: int = 3,
                                job_id: str = None) -> Dict[str, Any]: # Added job_id
        """
        Optimize parameters for multiple volatile cryptocurrencies.
        
        Args:
            strategy: Trading strategy name
            n_trials: Number of trials per crypto
            top_count: Number of top volatile cryptos to optimize
            min_volatility: Minimum volatility threshold
            max_workers: Maximum parallel workers
            job_id: Optional job ID for process tracking # Added job_id doc
            
        Returns:
            Batch optimization results
        """
        self.logger.info(f"Starting batch optimization: {strategy} on top {top_count} volatile cryptos")
        
        # Get volatile cryptocurrencies
        self.logger.info(f"Discovering volatile cryptos with min volatility: {min_volatility}")
        volatile_cryptos = self.crypto_discovery.get_volatile_cryptos(min_volatility=min_volatility)
        
        if not volatile_cryptos:
            self.logger.warning("No volatile cryptocurrencies found")
            raise ValueError("No volatile cryptocurrencies found")
        
        # Select top cryptos
        selected_cryptos = volatile_cryptos[:top_count]
        
        self.logger.info(f"Selected {len(selected_cryptos)} cryptos for optimization")
        for crypto in selected_cryptos:
            self.logger.info(f"  {crypto['symbol']}: {crypto['price_change_percentage_24h']:.2f}%")
        
        # Run parallel optimization
        results = []
        start_time = time.time()
        has_errors = False # Initialize error flag
        stop_batch_optimization = False # Initialize stop flag
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_crypto = {}
            for crypto in selected_cryptos:
                if job_id and job_status_manager.is_job_stop_requested(job_id):
                    self.logger.info(f"Job {job_id} stop requested. Stopping submission of new tasks.")
                    stop_batch_optimization = True
                    executor.shutdown(wait=False, cancel_futures=True)
                    break # Exit the loop if stop is requested
                
                future = executor.submit(
                    self.optimize_single_crypto, 
                    crypto['id'], 
                    strategy, 
                    n_trials,
                    job_id=job_id
                )
                future_to_crypto[future] = crypto
            
            # Collect results
            for future in as_completed(future_to_crypto):
                if job_id and job_status_manager.is_job_stop_requested(job_id):
                    self.logger.info(f"Job {job_id} stop requested. Stopping collection of results.")
                    stop_batch_optimization = True
                    executor.shutdown(wait=False, cancel_futures=True)
                    break # Exit the loop if stop is requested

                crypto = future_to_crypto[future]
                try:
                    result = future.result()
                    result['crypto_info'] = crypto  # Add crypto metadata
                    results.append(result)
                    
                    self.logger.info(f"Completed {crypto['symbol']}: {result['best_value']}")
                    
                except optuna.exceptions.OptunaError as e: # Catch OptunaError for job stop
                    self.logger.info(f"Optimization for {crypto['symbol']} stopped due to OptunaError: {e}")
                    # Set a flag to indicate that the batch optimization should stop
                    stop_batch_optimization = True
                    # Shut down the executor immediately
                    executor.shutdown(wait=False, cancel_futures=True)
                    break # Break out of the loop for this job
                except Exception as e:
                    self.logger.error(f"Failed to optimize {crypto['symbol']}: {e}", exc_info=True)
                    results.append({
                        'crypto': crypto['id'],
                        'crypto_info': crypto,
                        'strategy': strategy,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    has_errors = True # Set error flag
        
        end_time = time.time()

        if job_id and stop_batch_optimization:
            job_status_manager.update_job_status(job_id, 'stopped', 'Batch optimization stopped by user request.')
            self.logger.info(f"Batch optimization for job {job_id} stopped by user request.")
            return # Exit early if stopped
        
        # Compile batch results
        batch_results = {
            'strategy': strategy,
            'n_trials_per_crypto': n_trials,
            'total_cryptos': len(selected_cryptos),
            'successful_optimizations': len([r for r in results if 'best_value' in r]),
            'failed_optimizations': len([r for r in results if 'error' in r]),
            'total_time': end_time - start_time,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'best_overall': self._find_best_result(results)
        }
        
        # Save batch results
        self._save_batch_results(batch_results)
        
        # Update job status based on whether errors occurred
        if job_id: # Only update if job_id is provided
            if has_errors:
                job_status_manager.update_job_status(job_id, 'failed', 'Optimization completed with errors.')
                self.logger.info(f"Batch optimization completed with errors for job {job_id}.")
            else:
                job_status_manager.update_job_status(job_id, 'completed', 'Batch optimization completed successfully.')
                self.logger.info(f"Batch optimization completed successfully for job {job_id}.")
        
        self.logger.info(f"Batch optimization completed. Best overall: {batch_results['best_overall']}")
        return batch_results
    
    def _objective_function(self, trial, crypto: str, strategy: str, job_id: str) -> float: # Added job_id
        """
        Objective function for Optuna optimization.
        
        Args:
            trial: Optuna trial object
            crypto: Cryptocurrency identifier
            strategy: Trading strategy name
            job_id: The ID of the parent job (for process tracking) # Added job_id doc
            
        Returns:
            Objective value (profit percentage)
        """
        # Get parameter suggestions
        params = self.param_manager.suggest_parameters(trial, strategy)
        self.logger.info(f"Trial {trial.number}: Testing params {params}")
        
        # Format parameters for CLI
        cli_args = self.param_manager.format_cli_params(params)
        
        # Build command
        cmd = [
            'python', self.backtester_path,
            '--crypto', crypto,
            '--strategy', strategy,
            '--single-run'
        ] + cli_args
        
        process = None # Initialize process to None
        try:
            # Run backtester using Popen to get process object
            self.logger.info(f"Running backtester for trial {trial.number}: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.abspath(self.backtester_path))
            )
            
            # Register the process PID with the job status manager
            job_status_manager.register_job_process(job_id, process.pid)
            self.logger.info(f"Registered backtester process PID {process.pid} for job {job_id}.")

            stdout_data = []
            stderr_data = []
            timeout_seconds = 300 # 5 minute timeout
            start_time = time.time()

            while process.poll() is None: # While process is still running
                if job_status_manager.is_job_stop_requested(job_id):
                    self.logger.warning(f"Stop requested for job {job_id}. Terminating backtester process {process.pid}.")
                    process.terminate() # Send SIGTERM
                    time.sleep(1) # Give it a moment to terminate
                    if process.poll() is None:
                        process.kill() # Send SIGKILL if not terminated
                    raise JobStopRequestedError(f"Job {job_id} stop requested. Terminating trial.") # Raise custom exception

                # Read output without blocking indefinitely
                try:
                    stdout_line = process.stdout.readline()
                    if stdout_line:
                        stdout_data.append(stdout_line)
                    stderr_line = process.stderr.readline()
                    if stderr_line:
                        stderr_data.append(stderr_line)
                except Exception as e:
                    self.logger.error(f"Error reading process output: {e}")

                if time.time() - start_time > timeout_seconds:
                    self.logger.warning(f"Backtester timeout for {crypto} {strategy} in trial {trial.number}. Terminating process {process.pid}.")
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    raise subprocess.TimeoutExpired(cmd, timeout_seconds)
                time.sleep(0.1) # Small delay to prevent busy-waiting

            # Collect any remaining output after process exits
            remaining_stdout, remaining_stderr = process.communicate()
            stdout_data.append(remaining_stdout)
            stderr_data.append(remaining_stderr)

            output = "".join(stdout_data)
            error_output = "".join(stderr_data)
            
            if process.returncode != 0:
                # Check if the error is due to CoinGecko rate limit
                if "CoinGecko API rate limit exceeded" in error_output:
                    self.logger.error(f"CoinGecko API rate limit exceeded during trial {trial.number}")
                    raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded. Optimization stopped.")
                
                self.logger.warning(f"Backtester failed for trial {trial.number}: {error_output}")
                return -100.0  # Penalty for failed runs
            
            # Parse output for profit percentage (JSON format)
            try:
                # Extract JSON part from output
                json_start = output.find("OPTIMIZER_RESULTS:")
                if json_start != -1:
                    json_str = output[json_start + len("OPTIMIZER_RESULTS:"):]
                    results_data = json.loads(json_str)
                    
                    if "total_profit_percentage" in results_data:
                        profit_percentage = float(results_data["total_profit_percentage"])
                        self.logger.info(f"Trial {trial.number} completed. Profit: {profit_percentage}%")
                        return profit_percentage
                    else:
                        self.logger.warning(f"JSON output missing 'total_profit_percentage' in trial {trial.number}: {output}")
                        return -100.0
                else:
                    self.logger.warning(f"Could not find OPTIMIZER_RESULTS: prefix in output for trial {trial.number}. Full stdout: {output}. Stderr: {error_output}")
                    return -100.0
            except json.JSONDecodeError as e:
                self.logger.warning(f"Could not parse JSON from output in trial {trial.number}: {output}. Error: {e}")
                return -100.0
            except Exception as e:
                self.logger.warning(f"An unexpected error occurred while parsing output in trial {trial.number}: {output}. Error: {e}")
                return -100.0
                
        except subprocess.TimeoutExpired:
                self.logger.warning(f"Backtester timeout for {crypto} {strategy} in trial {trial.number}")
                return -100.0
        except Exception as e: # Catch all other exceptions
            self.logger.error(f"An unexpected error occurred during backtester execution for trial {trial.number}: {e}", exc_info=True)
            return -100.0
        finally:
            if process and process.poll() is None: # If process is still running, terminate it
                self.logger.warning(f"Backtester process {process.pid} still running in finally block. Terminating.")
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
            if process and process.pid: # Unregister PID if process was started
                job_status_manager.unregister_job_process(job_id, process.pid)
                self.logger.info(f"Unregistered backtester process PID {process.pid} for job {job_id}.")

        # If we reach here, it means backtester ran successfully but profit was not parsed
        self.logger.warning(f"Could not parse profit from output in trial {trial.number}. Full stdout: {output}. Stderr: {error_output}")
        return -100.0
    
    def _find_best_result(self, results: List[Dict]) -> Optional[Dict]:
        """Find the best result from a list of optimization results."""
        valid_results = [r for r in results if 'best_value' in r and r['best_value'] is not None]
        
        if not valid_results:
            return None
        
        return max(valid_results, key=lambda x: x['best_value'])
    
    def _save_optimization_results(self, results: Dict[str, Any]) -> None:
        """Save single optimization results to file."""
        filename = f"best_params_{results['crypto']}_{results['strategy']}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {filepath}")
        except OSError as e:
            self.logger.error(f"Error saving results: {e}")
    
    def _save_batch_results(self, results: Dict[str, Any]) -> None:
        """Save batch optimization results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"volatile_optimization_results_{results['strategy']}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Batch results saved to {filepath}")
        except OSError as e:
            self.logger.error(f"Error saving batch results: {e}")
    
    def load_optimization_results(self, crypto: str, strategy: str) -> Optional[Dict]:
        """Load optimization results for a specific crypto/strategy pair."""
        filename = f"best_params_{crypto}_{strategy}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.warning(f"Could not load results for {crypto}/{strategy}: {e}")
            return None
    
    def get_all_results(self) -> List[Dict]:
        """Get all optimization results from the results directory."""
        results = []
        
        try:
            for filename in os.listdir(self.results_dir):
                if filename.startswith('best_params_') and filename.endswith('.json'):
                    filepath = os.path.join(self.results_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            result = json.load(f)
                            results.append(result)
                    except (OSError, json.JSONDecodeError) as e:
                        self.logger.warning(f"Could not load {filename}: {e}")
        except OSError as e:
            self.logger.error(f"Error reading results directory: {e}")
        
        return results
    
    def get_top_results(self, limit: int = 10) -> List[Dict]:
        """Get top optimization results by performance."""
        all_results = self.get_all_results()
        
        # Filter valid results and sort by best value
        valid_results = [r for r in all_results if r.get('best_value') is not None]
        valid_results.sort(key=lambda x: x['best_value'], reverse=True)
        
        return valid_results[:limit]
