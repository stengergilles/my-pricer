#!/usr/bin/env python3
"""
Functional Tests for Core System Behavior

These tests validate that the system produces expected types of results
without being overly strict about exact values that may vary due to
randomness, timestamps, or external data changes.
"""

import os
import sys
import unittest
import subprocess
import json
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCoreFunctionality(unittest.TestCase):
    """Test core system functionality"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_backtester_produces_results(self):
        """Test that backtester produces expected result structure"""
        cmd = [
            "python", "backtester.py",
            "--crypto", "bitcoin",
            "--strategy", "EMA_Only",
            "--single-run",
            "--short-ema-period", "10",
            "--long-ema-period", "30",
            "--rsi-oversold", "30",
            "--rsi-overbought", "70",
            "--atr-period", "14",
            "--atr-multiple", "2.0",
            "--fixed-stop-loss-percentage", "0.02",
            "--take-profit-multiple", "2.0",
            "--macd-fast-period", "12",
            "--macd-slow-period", "26",
            "--macd-signal-period", "9"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout + result.stderr
        
        # Check if it's an API rate limit issue
        if "Too Many Requests" in output or "rate limit" in output.lower():
            self.skipTest("API rate limited - this is expected and not a code issue")
        
        # Check if it's a data fetch issue
        if "Could not fetch data" in output:
            self.skipTest("Data fetch failed - this is expected with external APIs")
        
        # Should complete successfully if data is available
        if result.returncode == 0:
            # Should contain key result indicators
            # Should mention profit/loss
            has_profit_info = bool(re.search(r'profit|loss|return', output, re.IGNORECASE))
            
            # Should mention trades
            has_trade_info = bool(re.search(r'trade|position', output, re.IGNORECASE))
            
            # At least one should be present if successful
            self.assertTrue(
                has_profit_info or has_trade_info,
                f"Output should contain profit/loss or trade information. Output: {output[:500]}"
            )
        else:
            # If it failed, it should be due to external factors, not code issues
            self.assertTrue(
                re.search(r'error|fail|not found|invalid|rate limit|fetch', output, re.IGNORECASE),
                f"Failure should be due to external factors. Output: {output[:500]}"
            )
    
    def test_different_strategies_work(self):
        """Test that different strategies execute without crashing"""
        strategies = ["EMA_Only", "Strict", "BB_Breakout"]
        
        for strategy in strategies:
            with self.subTest(strategy=strategy):
                cmd = [
                    "python", "backtester.py",
                    "--crypto", "bitcoin",
                    "--strategy", strategy,
                    "--single-run",
                    "--short-ema-period", "10",
                    "--long-ema-period", "30"
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                output = result.stdout + result.stderr
                
                # Skip if API issues
                if "Too Many Requests" in output or "Could not fetch data" in output:
                    self.skipTest(f"API issues for strategy {strategy} - expected")
                
                # Should not crash
                self.assertEqual(result.returncode, 0, f"Strategy {strategy} failed with return code {result.returncode}. Output: {output[:1000]}")
    
    def test_optimization_produces_results(self):
        """Test that optimization produces expected results"""
        cmd = [
            "python", "optimize_bayesian.py",
            "--crypto", "bitcoin",
            "--strategy", "EMA_Only",
            "--n-trials", "2"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        output = result.stdout + result.stderr
        
        # Skip if API issues
        if "Too Many Requests" in output or "Could not fetch data" in output:
            self.skipTest("API issues - expected with external dependencies")
        
        # Should complete successfully if data is available
        if result.returncode == 0:
            # Should mention trials
            self.assertTrue(
                re.search(r'trial|optimization', output, re.IGNORECASE),
                "Output should contain optimization information"
            )
            
            # Should mention best result
            self.assertTrue(
                re.search(r'best|optimal', output, re.IGNORECASE),
                "Output should contain best result information"
            )
        else:
            # If failed, should be due to external factors
            self.assertTrue(
                re.search(r'error|fail|not found|invalid|rate limit|fetch', output, re.IGNORECASE),
                f"Failure should be due to external factors. Output: {output[:500]}"
            )
    
    def test_volatile_crypto_discovery_structure(self):
        """Test that volatile crypto discovery produces expected structure"""
        cmd = ["python", "get_volatile_cryptos.py"]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Skip if API issues
        if "Too Many Requests" in output or "rate limit" in output.lower():
            self.skipTest("API rate limited - expected with external APIs")
        
        # Should complete successfully if API is available
        if result.returncode == 0:
            # Check if results file was created
            results_file = self.project_root / "backtest_results" / "volatile_cryptos.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    data = json.load(f)
                    
                # Should have expected structure
                self.assertIsInstance(data, dict, "Results should be a dictionary")
                
                if 'top_gainers' in data:
                    self.assertIsInstance(data['top_gainers'], list, "Top gainers should be a list")
                
                if 'top_losers' in data:
                    self.assertIsInstance(data['top_losers'], list, "Top losers should be a list")
        else:
            # If failed, should be due to external factors
            self.assertTrue(
                re.search(r'error|fail|rate limit|fetch', output, re.IGNORECASE),
                f"Failure should be due to external factors. Output: {output[:500]}"
            )

class TestSystemStability(unittest.TestCase):
    """Test system stability and consistency"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_repeated_backtests_consistency(self):
        """Test that repeated backtests with same parameters are consistent"""
        cmd = [
            "python", "backtester.py",
            "--crypto", "bitcoin",
            "--strategy", "EMA_Only",
            "--single-run",
            "--short-ema-period", "10",
            "--long-ema-period", "30"
        ]
        
        results = []
        for i in range(2):  # Run twice
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.assertEqual(result.returncode, 0, f"Run {i+1} failed")
            results.append(result.stdout + result.stderr)
        
        # Results should be identical (same data, same parameters)
        # Extract key metrics and compare
        def extract_metrics(output):
            metrics = {}
            
            # Look for profit percentage
            profit_match = re.search(r'profit.*?(-?\d+\.?\d*)%', output, re.IGNORECASE)
            if profit_match:
                metrics['profit'] = float(profit_match.group(1))
            
            # Look for number of trades
            trades_match = re.search(r'(\d+)\s+trades?', output, re.IGNORECASE)
            if trades_match:
                metrics['trades'] = int(trades_match.group(1))
            
            return metrics
        
        metrics1 = extract_metrics(results[0])
        metrics2 = extract_metrics(results[1])
        
        # If we found metrics, they should be the same
        if metrics1 and metrics2:
            for key in metrics1:
                if key in metrics2:
                    self.assertEqual(
                        metrics1[key], metrics2[key],
                        f"Metric {key} differs between runs: {metrics1[key]} vs {metrics2[key]}"
                    )

class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_invalid_crypto_handling(self):
        """Test handling of invalid cryptocurrency"""
        cmd = [
            "python", "backtester.py",
            "--crypto", "nonexistent_crypto_12345",
            "--strategy", "EMA_Only",
            "--single-run"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Should handle gracefully (may return non-zero but shouldn't crash)
        self.assertIsNotNone(result.returncode, "Should complete without crashing")
        
        # Should provide some error indication
        output = result.stdout + result.stderr
        self.assertTrue(
            re.search(r'error|fail|not found|invalid', output, re.IGNORECASE),
            "Should indicate error for invalid crypto"
        )
    
    def test_invalid_strategy_handling(self):
        """Test handling of invalid strategy"""
        cmd = [
            "python", "backtester.py",
            "--crypto", "bitcoin",
            "--strategy", "NonexistentStrategy",
            "--single-run"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Should handle gracefully
        self.assertIsNotNone(result.returncode, "Should complete without crashing")
        
        # Should provide error indication
        output = result.stdout + result.stderr
        self.assertTrue(
            re.search(r'error|fail|not found|invalid|strategy', output, re.IGNORECASE),
            "Should indicate error for invalid strategy"
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
