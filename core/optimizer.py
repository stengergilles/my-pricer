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
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import job_status_manager # Added import

from .backtester_wrapper import BacktesterWrapper # New import
from .data_fetcher import DataFetcher # New import

from .exceptions import JobStopRequestedError, CoinGeckoRateLimitError # New import

class JobStopCallback:
    """Optuna callback that checks for job stop requests."""
    def __init__(self, job_id, logger):
        self.job_id = job_id
        self.logger = logger
    
    def __call__(self, study, trial):
        if self.job_id and job_status_manager.is_job_stop_requested(self.job_id):
            self.logger.info(f"Job {self.job_id} stop requested. Stopping Optuna study.")
            study.stop()

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
from .result_manager import ResultManager
from .app_config import Config
from config import DEFAULT_TIMEFRAME, DEFAULT_INTERVAL

class BayesianOptimizer:
    """
    Unified Bayesian optimization for trading strategies.
    Handles both single crypto and batch optimization.
    """
    
    def __init__(self, 
                 results_dir: str = "backtest_results",
                 backtester_path: str = None, # This might become obsolete
                 seed: int = 42,
                 logger: logging.Logger = None,
                 data_fetcher: Optional[DataFetcher] = None): # Added data_fetcher parameter
        """
        Initialize optimizer.
        
        Args:
            results_dir: Directory to store optimization results
            backtester_path: Path to backtester script
            seed: Random seed for reproducibility
            logger: Optional logger instance
            data_fetcher: Optional DataFetcher instance for shared data access
        """
        self.results_dir = results_dir
        # self.backtester_path = backtester_path or str(Path(__file__).parent.parent / "backtester.py") # Obsolete
        self.seed = seed
        self.logger = logger or logging.getLogger(__name__)
        self.data_fetcher = data_fetcher # Store the data_fetcher
        
        # Initialize components
        self.config = Config()
        self.param_manager = ParameterManager()
        self.crypto_discovery = CryptoDiscovery(results_dir, data_fetcher=self.data_fetcher)
        self.result_manager = ResultManager(self.config)
        self.backtester_wrapper = BacktesterWrapper(self.config, data_fetcher=self.data_fetcher) # Initialize BacktesterWrapper
        
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
                             job_id: str = None,
                             data: pd.DataFrame = None) -> Dict[str, Any]:
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
            job_id: Optional job ID for process tracking
            data: Pre-fetched data (optional)
            
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
            return self._objective_function(trial, crypto, strategy, job_id, data)
        
        # Run optimization
        start_time = time.time()
        try:
            stopper = RateLimitStopper(self.logger)
            callbacks = [stopper]
            
            # Add job stop callback if job_id is provided
            if job_id:
                job_stop_callback = JobStopCallback(job_id, self.logger)
                callbacks.append(job_stop_callback)
            
            study.optimize(objective, n_trials=n_trials, timeout=timeout, callbacks=callbacks)
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
        best_trial = study.best_trial
        backtest_result = best_trial.user_attrs.get("backtest_result") if best_trial else None

        results = {
            'crypto': crypto,
            'strategy': strategy,
            'n_trials': len(study.trials),
            'best_value': study.best_value if study.best_trial else None,
            'best_params': study.best_params if study.best_trial else {},
            'optimization_time': end_time - start_time,
            'timestamp': datetime.now().isoformat(),
            'study_name': study_name,
            'backtest_result': backtest_result,
            'source': 'optimized', # Add source for optimized backtests
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
                                job_id: str = None) -> Dict[str, Any]:
        """
        Optimize parameters for multiple volatile cryptocurrencies.
        
        Args:
            strategy: Trading strategy name
            n_trials: Number of trials per crypto
            top_count: Number of top volatile cryptos to optimize
            min_volatility: Minimum volatility threshold
            max_workers: Maximum parallel workers
            job_id: Optional job ID for process tracking
            
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

        # Pre-fetch data for all selected cryptos
        self.logger.info(f"Pre-fetching data for {len(selected_cryptos)} cryptos...")
        prefetched_data = {}
        for crypto in selected_cryptos:
            crypto_id = crypto['id']
            try:
                df = self.data_fetcher.get_crypto_data_merged(crypto_id, days=int(DEFAULT_TIMEFRAME))
                if df is not None and not df.empty:
                    prefetched_data[crypto_id] = df
                    self.logger.info(f"Successfully pre-fetched data for {crypto_id}")
                else:
                    self.logger.warning(f"Could not pre-fetch data for {crypto_id}")
            except Exception as e:
                self.logger.error(f"Error pre-fetching data for {crypto_id}: {e}")

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
                    break # Exit the loop if stop is requested
                
                crypto_id = crypto['id']
                crypto_data = prefetched_data.get(crypto_id)

                if crypto_data is None:
                    self.logger.warning(f"Skipping optimization for {crypto_id} because pre-fetched data is missing.")
                    continue

                future = executor.submit(
                    self.optimize_single_crypto, 
                    crypto_id, 
                    strategy, 
                    n_trials,
                    job_id=job_id,
                    data=crypto_data
                )
                future_to_crypto[future] = crypto
            
            # If stop was requested during submission, cancel all futures and exit
            if stop_batch_optimization:
                for future in future_to_crypto:
                    future.cancel()
                if job_id:
                    job_status_manager.update_job_status(job_id, 'stopped', 'Optimization stopped by user.')
                return []
            
            # Collect results
            for future in as_completed(future_to_crypto):
                if job_id and job_status_manager.is_job_stop_requested(job_id):
                    self.logger.info(f"Job {job_id} stop requested. Cancelling remaining futures.")
                    # Cancel all remaining futures
                    for remaining_future in future_to_crypto:
                        if not remaining_future.done():
                            remaining_future.cancel()
                    stop_batch_optimization = True
                    break # Exit the loop if stop is requested

                crypto = future_to_crypto[future]
                try:
                    result = future.result()
                    result['crypto_info'] = crypto  # Add crypto metadata
                    results.append(result)
                    
                    # Save the backtest result
                    if result.get('backtest_result'):
                        self.result_manager.save_backtest_result(
                            crypto_id=result['crypto'],
                            strategy_name=result['strategy'],
                            result=result['backtest_result']
                        )

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
    
    def _objective_function(self, trial, crypto: str, strategy: str, job_id: str, data: pd.DataFrame = None) -> float:
        """
        Objective function for Optuna optimization.
        
        Args:
            trial: Optuna trial object
            crypto: Cryptocurrency identifier
            strategy: Trading strategy name
            job_id: The ID of the parent job (for process tracking)
            data: Pre-fetched data (optional)
            
        Returns:
            Objective value (profit percentage)
        """
        # Check for job stop request at the beginning of each trial
        if job_id and job_status_manager.is_job_stop_requested(job_id):
            self.logger.info(f"Job {job_id} stop requested. Terminating trial {trial.number}.")
            raise JobStopRequestedError(f"Job {job_id} stop requested. Terminating trial.")

        # Get parameter suggestions
        params = self.param_manager.suggest_parameters(trial, strategy)
        self.logger.info(f"Trial {trial.number}: Testing params {params}")
        
        try:
            # Run backtest using the BacktesterWrapper
            backtest_result = self.backtester_wrapper.run_single_backtest(
                crypto=crypto,
                strategy=strategy,
                parameters=params,
                timeframe=DEFAULT_TIMEFRAME, # Use a fixed timeframe for optimization
                interval=DEFAULT_INTERVAL, # Use a fixed interval for optimization
                data=data
            )
            
            if backtest_result and backtest_result.get('success'):
                profit_percentage = backtest_result.get('total_profit_percentage', -100.0)
                
                # Store the full backtest result in the trial's user attributes
                trial.set_user_attr("backtest_result", backtest_result)
                
                self.logger.info(f"Trial {trial.number} completed. Profit: {profit_percentage}%")
                return profit_percentage
            else:
                error_message = backtest_result.get('error', 'Unknown error') if backtest_result else 'No result'
                self.logger.warning(f"Backtest failed for trial {trial.number}: {error_message}")
                if "CoinGecko API rate limit exceeded" in error_message:
                    raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded. Optimization stopped.")
                return -100.0 # Penalty for failed runs
                
        except CoinGeckoRateLimitError as e:
            self.logger.error(f"CoinGecko API rate limit exceeded during trial {trial.number}: {e}")
            trial.set_user_attr("rate_limit_hit", True)
            raise # Re-raise to be caught by the RateLimitStopper callback
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during backtester execution for trial {trial.number}: {e}", exc_info=True)
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

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r') as f:
                # Check if file is empty
                if os.fstat(f.fileno()).st_size == 0:
                    self.logger.warning(f"Optimization results file is empty: {filepath}")
                    return None
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {filepath}: {e}")
            return None
        except OSError as e:
            self.logger.error(f"Error reading file {filepath}: {e}")
            return None
    
    def get_all_results(self) -> List[Dict]:
        """Get all optimization results from the results directory."""
        results = []
        available_strategies = self.param_manager.get_available_strategies()
        
        try:
            for filename in os.listdir(self.results_dir):
                if filename.startswith('best_params_') and filename.endswith('.json'):
                    filepath = os.path.join(self.results_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            result = json.load(f)
                            
                            # --- Data Validation and Correction ---
                            strategy = result.get('strategy')
                            
                            # 1. Try to correct known typos
                            if isinstance(strategy, str):
                                if strategy.lower() == 'emea':
                                    strategy = 'EMA_Only'
                                    result['strategy'] = strategy # Correct in memory
                            
                            # 2. If strategy is invalid or blank, try to infer from filename
                            if not strategy or strategy not in available_strategies:
                                try:
                                    # Filename format: best_params_{crypto}_{strategy}.json
                                    parts = filename.replace('best_params_', '').replace('.json', '').split('_')
                                    if len(parts) > 1:
                                        strategy_from_filename = parts[1]
                                        if strategy_from_filename in available_strategies:
                                            self.logger.warning(f"Correcting strategy for {filename}. Was '{strategy}', now '{strategy_from_filename}'.")
                                            result['strategy'] = strategy_from_filename
                                except Exception as e:
                                    self.logger.error(f"Could not infer strategy from filename {filename}: {e}")

                            # 3. Only append if the strategy is now valid
                            if result.get('strategy') in available_strategies:
                                results.append(result)
                            else:
                                self.logger.warning(f"Skipping {filename} due to invalid or missing strategy: '{result.get('strategy')}'")

                    except (OSError, json.JSONDecodeError) as e:
                        self.logger.warning(f"Could not load or parse {filename}: {e}")
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