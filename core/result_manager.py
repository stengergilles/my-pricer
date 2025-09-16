"""
Result storage and retrieval manager.
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from core.app_config import Config

logger = logging.getLogger(__name__)

class ResultManager:
    """Manages storage and retrieval of analysis and backtest results."""
    
    def __init__(self, config: Config):
        self.config = config
        self.results_dir = self.config.RESULTS_DIR
        os.makedirs(self.results_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__) # Add this line
        self.logger.info(f"ResultManager initialized. Results directory: {self.results_dir}")
    
    def save_analysis_result(self, crypto_id: str, result_data: Dict[str, Any]) -> str:
        logger.info(f"Attempting to save analysis result for crypto_id: {crypto_id}")
        crypto_id = crypto_id.replace(' ', '-').lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analysis_{crypto_id}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        logger.info(f"Generated filepath for analysis result: {filepath}")
        
        try:
            with open(filepath, 'w') as f:
                json.dump(result_data, f, indent=2, default=str)
            logger.info(f"Successfully saved analysis result to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save analysis result to {filepath}: {e}")
            raise # Re-raise to propagate the error
    
    
    
    def get_crypto_status(self, crypto_id: str) -> Dict[str, Any]:
        """
        Checks if a cryptocurrency has existing optimization results.
        This is a placeholder and needs proper implementation based on actual optimization results.
        """
        has_optimization_results = False
        # Check if any analysis result files exist for the crypto_id
        pattern = f"analysis_{crypto_id}_*.json"
        files = glob.glob(os.path.join(self.results_dir, pattern))
        if files:
            has_optimization_results = True

        return {
            'crypto_id': crypto_id,
            'has_config_params': False,  # Placeholder: needs actual check for config params
            'has_optimization_results': has_optimization_results
        }

    
    def save_backtest_result(self, crypto_id: str, strategy_name: str, result: Dict[str, Any]) -> str:
        """Save backtest result to file."""
        crypto_id = crypto_id.replace(' ', '-').lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_{crypto_id}_{strategy_name}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        return filepath
    
    def get_analysis_history(self, crypto_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get analysis history."""
        if crypto_id:
            crypto_id = crypto_id.replace(' ', '-').lower()
        pattern = f"analysis_{crypto_id}_*.json" if crypto_id else "analysis_*.json"
        files = glob.glob(os.path.join(self.results_dir, pattern))
        files.sort(reverse=True)  # Most recent first
        
        results = []
        for filepath in files[:limit]:
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    result['file_path'] = filepath
                    results.append(result)
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        
        return results
    
    def get_backtest_history(self, 
                           crypto_id: Optional[str] = None,
                           strategy_name: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get backtest history."""
        if crypto_id:
            crypto_id = crypto_id.replace(' ', '-').lower()
        
        if crypto_id and strategy_name:
            pattern = f"backtest_{crypto_id}_{strategy_name}_*.json"
        elif crypto_id:
            pattern = f"backtest_{crypto_id}_*.json"
        elif strategy_name:
            pattern = f"backtest_*_{strategy_name}_*.json"
        else:
            pattern = "backtest_*.json"
        
        files = glob.glob(os.path.join(self.results_dir, pattern))
        self.logger.debug(f"get_backtest_history: Searching for pattern '{pattern}'. Found files: {files}")
        files.sort(reverse=True)  # Most recent first
        
        results = []
        for filepath in files[:limit]:
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    result['file_path'] = filepath
                    results.append(result)
                    self.logger.debug(f"get_backtest_history: Successfully loaded {filepath}. Content: {result}")
            except Exception as e:
                self.logger.error(f"get_backtest_history: Error loading {filepath}: {e}")
        
        return results
    
    def get_optimization_history(self, 
                           crypto_id: Optional[str] = None,
                           strategy_name: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get optimization history."""
        if crypto_id and strategy_name:
            pattern = f"best_params_{crypto_id}_{strategy_name}.json"
        elif crypto_id:
            pattern = f"best_params_{crypto_id}_*.json"
        elif strategy_name:
            pattern = f"best_params_*_{strategy_name}.json"
        else:
            pattern = "best_params_*.json"
        
        files = glob.glob(os.path.join(self.results_dir, pattern))
        files.sort(reverse=True)  # Most recent first
        
        results = []
        for filepath in files[:limit]:
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    result['file_path'] = filepath
                    results.append(result)
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        
        return results

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get specific analysis by ID."""
        files = glob.glob(os.path.join(self.results_dir, "analysis_*.json"))
        
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    if result.get('analysis_id') == analysis_id:
                        result['file_path'] = filepath
                        return result
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        
        return None
    
    def get_backtest_by_id(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """Get specific backtest by ID."""
        files = glob.glob(os.path.join(self.results_dir, "backtest_*.json"))
        
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    if result.get('backtest_id') == backtest_id:
                        result['file_path'] = filepath
                        return result
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        
        return None

    def get_profitable_backtest_results(self, crypto_id: str, fiat_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all profitable backtest results for a given crypto and fiat pair.
        A backtest result is considered profitable if its 'net_profit' is positive.
        """
        crypto_id = crypto_id.replace(' ', '-').lower()
        fiat_id = fiat_id.replace(' ', '-').lower() # Assuming fiat_id is also part of the filename pattern if needed

        # Get all backtest history for the crypto_id
        # The pattern needs to be flexible enough to catch all strategies for the crypto_id
        pattern = f"backtest_{crypto_id}_*.json"
        files = glob.glob(os.path.join(self.results_dir, pattern))
        
        profitable_results = []
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    # Check if the result is for the correct fiat_id (if applicable in the result content)
                    # And if it's profitable
                    if result.get('net_profit', 0) > 0: # Assuming 'net_profit' is a key in the result
                        profitable_results.append(result)
            except Exception as e:
                self.logger.error(f"Error loading backtest result from {filepath}: {e}")
        
        return profitable_results
