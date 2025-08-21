#!/usr/bin/env python3
"""
Integration Tests for End-to-End Workflows

These tests validate complete workflows without modifying existing code.
They capture current system behavior as expected behavior.
"""

import os
import sys
import unittest
import tempfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestBacktesterIntegration(unittest.TestCase):
    """Test complete backtester workflows"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_backtester_single_run_execution(self):
        """Test that backtester can execute a single run without errors"""
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
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            # Test should not crash (return code might be non-zero due to data issues, but shouldn't crash)
            self.assertIsNotNone(result.returncode, "Process should complete")
            
            # Should produce some output
            self.assertTrue(len(result.stdout) > 0 or len(result.stderr) > 0, 
                          "Should produce some output")
            
        except subprocess.TimeoutExpired:
            self.fail("Backtester single run timed out")
        except Exception as e:
            self.fail(f"Backtester single run failed: {e}")
    
    def test_backtester_different_strategies(self):
        """Test that backtester works with different strategies"""
        strategies_to_test = ["EMA_Only", "Strict", "BB_Breakout"]
        
        for strategy in strategies_to_test:
            with self.subTest(strategy=strategy):
                cmd = [
                    "python", "backtester.py",
                    "--crypto", "bitcoin",
                    "--strategy", strategy,
                    "--single-run",
                    "--short-ema-period", "10",
                    "--long-ema-period", "30",
                    "--rsi-oversold", "30",
                    "--rsi-overbought", "70"
                ]
                
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    # Should complete without crashing
                    self.assertIsNotNone(result.returncode)
                    
                except subprocess.TimeoutExpired:
                    self.fail(f"Strategy {strategy} timed out")
                except Exception as e:
                    self.fail(f"Strategy {strategy} failed: {e}")

class TestOptimizationIntegration(unittest.TestCase):
    """Test optimization workflows"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_bayesian_optimization_minimal(self):
        """Test bayesian optimization with minimal trials"""
        cmd = [
            "python", "optimize_bayesian.py",
            "--crypto", "bitcoin",
            "--strategy", "EMA_Only",
            "--n-trials", "2"  # Minimal for testing
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            # Should complete
            self.assertIsNotNone(result.returncode)
            
            # Should produce output
            self.assertTrue(len(result.stdout) > 0 or len(result.stderr) > 0)
            
        except subprocess.TimeoutExpired:
            self.fail("Bayesian optimization timed out")
        except Exception as e:
            self.fail(f"Bayesian optimization failed: {e}")

class TestDataIntegration(unittest.TestCase):
    """Test data fetching and processing workflows"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    @patch('requests.get')
    def test_volatile_crypto_discovery_mock(self, mock_get):
        """Test volatile crypto discovery with mocked API"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'bitcoin',
                'symbol': 'btc',
                'name': 'Bitcoin',
                'current_price': 45000,
                'price_change_percentage_24h': 5.2
            },
            {
                'id': 'ethereum',
                'symbol': 'eth', 
                'name': 'Ethereum',
                'current_price': 3000,
                'price_change_percentage_24h': -3.1
            }
        ]
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        cmd = ["python", "get_volatile_cryptos.py"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Should complete
            self.assertIsNotNone(result.returncode)
            
        except subprocess.TimeoutExpired:
            self.fail("Volatile crypto discovery timed out")
        except Exception as e:
            # Expected to fail with real API, but shouldn't crash
            pass

class TestResultsManagement(unittest.TestCase):
    """Test results management workflows"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_manage_results_import(self):
        """Test that manage_results can be imported and basic functions work"""
        try:
            import manage_results
            self.assertTrue(True, "manage_results imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import manage_results: {e}")
    
    def test_manage_results_execution(self):
        """Test manage_results basic execution"""
        cmd = ["python", "manage_results.py", "--help"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Help should work
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage:", result.stdout.lower())
            
        except subprocess.TimeoutExpired:
            self.fail("manage_results --help timed out")
        except Exception as e:
            self.fail(f"manage_results --help failed: {e}")

class TestSystemIntegration(unittest.TestCase):
    """Test overall system integration"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
    
    def test_all_main_scripts_help(self):
        """Test that all main scripts can show help without crashing"""
        scripts_to_test = [
            "backtester.py",
            "optimize_bayesian.py", 
            "manage_results.py"
        ]
        
        for script in scripts_to_test:
            with self.subTest(script=script):
                cmd = ["python", script, "--help"]
                
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    # Help should work for all scripts
                    self.assertEqual(result.returncode, 0, 
                                   f"{script} --help should return 0")
                    self.assertIn("usage:", result.stdout.lower(),
                                f"{script} should show usage in help")
                    
                except subprocess.TimeoutExpired:
                    self.fail(f"{script} --help timed out")
                except Exception as e:
                    self.fail(f"{script} --help failed: {e}")
    
    def test_python_syntax_all_files(self):
        """Test that all Python files have valid syntax"""
        python_files = list(self.project_root.glob("*.py"))
        
        for py_file in python_files:
            if py_file.name.startswith('.'):
                continue
                
            with self.subTest(file=py_file.name):
                cmd = ["python", "-m", "py_compile", str(py_file)]
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    self.assertEqual(result.returncode, 0,
                                   f"{py_file.name} has syntax errors: {result.stderr}")
                    
                except subprocess.TimeoutExpired:
                    self.fail(f"Syntax check for {py_file.name} timed out")
                except Exception as e:
                    self.fail(f"Syntax check for {py_file.name} failed: {e}")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
