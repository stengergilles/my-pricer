"""
Result storage and retrieval manager.
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Optional, Any

class ResultManager:
    """Manages storage and retrieval of analysis and backtest results."""
    
    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
    
    def save_analysis_result(self, crypto_id: str, result: Dict[str, Any]) -> str:
        """Save analysis result to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analysis_{crypto_id}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        return filepath
    
    def save_backtest_result(self, crypto_id: str, strategy_name: str, result: Dict[str, Any]) -> str:
        """Save backtest result to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_{crypto_id}_{strategy_name}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        return filepath
    
    def get_analysis_history(self, crypto_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get analysis history."""
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
        if crypto_id and strategy_name:
            pattern = f"backtest_{crypto_id}_{strategy_name}_*.json"
        elif crypto_id:
            pattern = f"backtest_{crypto_id}_*.json"
        elif strategy_name:
            pattern = f"backtest_*_{strategy_name}_*.json"
        else:
            pattern = "backtest_*.json"
        
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
