"""
Unified Bayesian optimization engine.
Consolidates logic from optimize_bayesian.py and volatile_crypto_optimizer.py.
"""

import optuna
import subprocess
import json
import logging
import os
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

class CoinGeckoRateLimitError(Exception):
    """Custom exception for CoinGecko API rate limit errors."""
    pass

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
                 seed: int = 42):
        """
        Initialize optimizer.
        
        Args:
            results_dir: Directory to store optimization results
            backtester_path: Path to backtester script
            seed: Random seed for reproducibility
        """
        self.results_dir = results_dir
        self.backtester_path = backtester_path or "backtester.py"
        self.seed = seed
        self.logger = logging.getLogger(__name__)
        
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
                             timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Optimize parameters for a single cryptocurrency and strategy.
        
        Args:
            crypto: Cryptocurrency identifier
            strategy: Trading strategy name
            n_trials: Number of optimization trials
            timeout: Timeout in seconds (optional)
            
        Returns:
            Optimization results dictionary
        """
        self.logger.info(f"Starting optimization: {crypto} with {strategy} ({n_trials} trials)")
        
        # Validate strategy
        if strategy not in self.param_manager.get_available_strategies():
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
            return self._objective_function(trial, crypto, strategy)
        
        # Run optimization
        start_time = time.time()
        try:
            study.optimize(objective, n_trials=n_trials, timeout=timeout)
        except KeyboardInterrupt:
            self.logger.warning("Optimization interrupted by user")
        except CoinGeckoRateLimitError as e:
            self.logger.error(f"Optimization stopped due to rate limit: {e}")
            # Return an empty result or a result indicating failure
            return {
                'crypto': crypto,
                'strategy': strategy,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'n_trials': 0,
                'best_value': None,
                'best_params': {},
                'optimization_time': 0,
                'study_name': study_name,
                'all_trials': []
            }
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            raise
        
        end_time = time.time()
        
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
                                max_workers: int = 3) -> Dict[str, Any]:
        """
        Optimize parameters for multiple volatile cryptocurrencies.
        
        Args:
            strategy: Trading strategy name
            n_trials: Number of trials per crypto
            top_count: Number of top volatile cryptos to optimize
            min_volatility: Minimum volatility threshold
            max_workers: Maximum parallel workers
            
        Returns:
            Batch optimization results
        """
        self.logger.info(f"Starting batch optimization: {strategy} on top {top_count} volatile cryptos")
        
        # Get volatile cryptocurrencies
        volatile_cryptos = self.crypto_discovery.get_volatile_cryptos(min_volatility=min_volatility)
        
        if not volatile_cryptos:
            raise ValueError("No volatile cryptocurrencies found")
        
        # Select top cryptos
        selected_cryptos = volatile_cryptos[:top_count]
        
        self.logger.info(f"Selected {len(selected_cryptos)} cryptos for optimization")
        for crypto in selected_cryptos:
            self.logger.info(f"  {crypto['symbol']}: {crypto['price_change_percentage_24h']:.2f}%")
        
        # Run parallel optimization
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit optimization tasks
            future_to_crypto = {
                executor.submit(
                    self.optimize_single_crypto, 
                    crypto['id'], 
                    strategy, 
                    n_trials
                ): crypto
                for crypto in selected_cryptos
            }
            
            # Collect results
            for future in as_completed(future_to_crypto):
                crypto = future_to_crypto[future]
                try:
                    result = future.result()
                    result['crypto_info'] = crypto  # Add crypto metadata
                    results.append(result)
                    
                    self.logger.info(f"Completed {crypto['symbol']}: {result['best_value']}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to optimize {crypto['symbol']}: {e}")
                    results.append({
                        'crypto': crypto['id'],
                        'crypto_info': crypto,
                        'strategy': strategy,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
        
        end_time = time.time()
        
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
        
        self.logger.info(f"Batch optimization completed. Best overall: {batch_results['best_overall']}")
        return batch_results
    
    def _objective_function(self, trial, crypto: str, strategy: str) -> float:
        """
        Objective function for Optuna optimization.
        
        Args:
            trial: Optuna trial object
            crypto: Cryptocurrency identifier
            strategy: Trading strategy name
            
        Returns:
            Objective value (profit percentage)
        """
        # Get parameter suggestions
        params = self.param_manager.suggest_parameters(trial, strategy)
        
        # Format parameters for CLI
        cli_args = self.param_manager.format_cli_params(params)
        
        # Build command
        cmd = [
            'python', self.backtester_path,
            '--crypto', crypto,
            '--strategy', strategy,
            '--single-run'
        ] + cli_args
        
        try:
            # Run backtester
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=os.path.dirname(os.path.abspath(self.backtester_path))
            )
            
            if result.returncode != 0:
                # Check if the error is due to CoinGecko rate limit
                if "CoinGecko API rate limit exceeded" in result.stderr:
                    raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded. Optimization stopped.")
                
                self.logger.warning(f"Backtester failed: {result.stderr}")
                return -100.0  # Penalty for failed runs
            
            # Parse output for profit percentage (JSON format)
            output = result.stdout
            
            try:
                # Extract JSON part from output
                json_start = output.find("OPTIMIZER_RESULTS:")
                if json_start != -1:
                    json_str = output[json_start + len("OPTIMIZER_RESULTS:"):]
                    results_data = json.loads(json_str)
                    
                    if "total_profit_percentage" in results_data:
                        profit_percentage = float(results_data["total_profit_percentage"])
                        return profit_percentage
                    else:
                        self.logger.warning(f"JSON output missing 'total_profit_percentage': {output}")
                        return -100.0
                else:
                    self.logger.warning(f"Could not find OPTIMIZER_RESULTS: prefix in output. Full stdout: {output}. Stderr: {result.stderr}")
                    return -100.0
            except json.JSONDecodeError as e:
                self.logger.warning(f"Could not parse JSON from output: {output}. Error: {e}")
                return -100.0
            except Exception as e:
                self.logger.warning(f"An unexpected error occurred while parsing output: {output}. Error: {e}")
                return -100.0
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Backtester timeout for {crypto} {strategy}")
            return -100.0
        except Exception as e:
            if isinstance(e, CoinGeckoRateLimitError):
                raise e  # Re-raise CoinGeckoRateLimitError to stop optimization
            self.logger.error(f"Error running backtester: {e}")
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
