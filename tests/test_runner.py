#!/usr/bin/env python3
"""
Regression Testing Framework for Crypto Trading System

This framework captures the current behavior of the system as "golden standards"
and detects any regressions after code changes. It does NOT modify existing code.

Usage:
    python tests/test_runner.py --capture    # Capture current behavior as golden standards
    python tests/test_runner.py --test       # Run regression tests against golden standards
    python tests/test_runner.py --all        # Run all tests
"""

import os
import sys
import json
import subprocess
import hashlib
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class RegressionTester:
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.golden_dir = self.test_dir / "golden_standards"
        self.results_dir = self.test_dir / "test_results"
        self.golden_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.test_dir / "test_runner.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def capture_golden_standards(self):
        """Capture current system behavior as golden standards"""
        self.logger.info("🔄 Capturing golden standards...")
        
        # Test cases that represent core functionality
        test_cases = [
            {
                "name": "backtester_bitcoin_ema_only",
                "command": [
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
            },
            {
                "name": "backtester_ethereum_strict",
                "command": [
                    "python", "backtester.py",
                    "--crypto", "ethereum",
                    "--strategy", "Strict",
                    "--single-run",
                    "--short-sma-period", "20",
                    "--long-sma-period", "50",
                    "--rsi-oversold", "25",
                    "--rsi-overbought", "75",
                    "--atr-period", "14",
                    "--atr-multiple", "1.5",
                    "--fixed-stop-loss-percentage", "0.03",
                    "--take-profit-multiple", "3.0",
                    "--macd-fast-period", "12",
                    "--macd-slow-period", "26",
                    "--macd-signal-period", "9"
                ]
            },
            {
                "name": "volatile_cryptos_discovery",
                "command": ["python", "get_volatile_cryptos.py"]
            },
            {
                "name": "bayesian_optimization_sample",
                "command": [
                    "python", "optimize_bayesian.py",
                    "--crypto", "bitcoin",
                    "--strategy", "EMA_Only",
                    "--n-trials", "3"  # Small number for testing
                ]
            }
        ]
        
        for test_case in test_cases:
            self._capture_test_case(test_case)
            
        self.logger.info("✅ Golden standards captured successfully")
        
    def _capture_test_case(self, test_case):
        """Capture a single test case"""
        self.logger.info(f"📸 Capturing: {test_case['name']}")
        
        try:
            # Run the command and capture output
            result = subprocess.run(
                test_case['command'],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self.test_dir.parent
            )
            
            # Normalize outputs before storing
            stdout_normalized = self._normalize_output(result.stdout)
            stderr_normalized = self._normalize_output(result.stderr)
            
            # Create golden standard record
            golden_record = {
                "name": test_case['name'],
                "command": test_case['command'],
                "return_code": result.returncode,
                "stdout": stdout_normalized,
                "stderr": stderr_normalized,
                "captured_at": datetime.now().isoformat(),
                "stdout_hash": hashlib.md5(stdout_normalized.encode()).hexdigest(),
                "stderr_hash": hashlib.md5(stderr_normalized.encode()).hexdigest()
            }
            
            # Save golden standard
            golden_file = self.golden_dir / f"{test_case['name']}.json"
            with open(golden_file, 'w') as f:
                json.dump(golden_record, f, indent=2)
                
            self.logger.info(f"✅ Captured: {test_case['name']} (return_code: {result.returncode})")
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ Timeout: {test_case['name']}")
        except Exception as e:
            self.logger.error(f"❌ Error capturing {test_case['name']}: {e}")
    
    def run_regression_tests(self):
        """Run regression tests against golden standards"""
        self.logger.info("🧪 Running regression tests...")
        
        golden_files = list(self.golden_dir.glob("*.json"))
        if not golden_files:
            self.logger.error("❌ No golden standards found. Run --capture first.")
            return False
            
        all_passed = True
        results = []
        
        for golden_file in golden_files:
            passed = self._test_against_golden(golden_file)
            all_passed = all_passed and passed
            results.append({
                "test": golden_file.stem,
                "passed": passed,
                "timestamp": datetime.now().isoformat()
            })
        
        # Save test results
        results_file = self.results_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": len(results),
                    "passed": sum(1 for r in results if r["passed"]),
                    "failed": sum(1 for r in results if not r["passed"]),
                    "all_passed": all_passed
                },
                "results": results
            }, f, indent=2)
        
        if all_passed:
            self.logger.info("✅ All regression tests passed!")
        else:
            self.logger.error("❌ Some regression tests failed!")
            
        return all_passed
    
    def _normalize_output(self, output):
        """Normalize output by removing timestamps and other variable elements"""
        import re
        
        # Remove timestamps
        output = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', 'TIMESTAMP', output)
        
        # Remove specific log messages that contain variable data
        output = re.sub(r'--- cython import error:.*---', '--- cython import error: NORMALIZED ---', output)
        
        # Remove trial-specific information from Optuna
        output = re.sub(r'Trial \d+ finished with value:', 'Trial X finished with value:', output)
        output = re.sub(r'Best trial: \d+', 'Best trial: X', output)
        
        # Remove specific profit values that may vary slightly
        output = re.sub(r'Profit: [-+]?\d+\.\d+%', 'Profit: X.XX%', output)
        
        # Remove memory addresses and object IDs
        output = re.sub(r'0x[0-9a-fA-F]+', '0xNORMALIZED', output)
        
        return output
    
    def _test_against_golden(self, golden_file):
        """Test current behavior against a golden standard"""
        with open(golden_file, 'r') as f:
            golden = json.load(f)
            
        test_name = golden['name']
        self.logger.info(f"🧪 Testing: {test_name}")
        
        try:
            # Run the same command
            result = subprocess.run(
                golden['command'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.test_dir.parent
            )
            
            # Compare results with normalization
            differences = []
            
            if result.returncode != golden['return_code']:
                differences.append(f"Return code: expected {golden['return_code']}, got {result.returncode}")
            
            # Normalize outputs before comparison
            current_stdout_normalized = self._normalize_output(result.stdout)
            golden_stdout_normalized = self._normalize_output(golden['stdout'])
            
            current_stderr_normalized = self._normalize_output(result.stderr)
            golden_stderr_normalized = self._normalize_output(golden['stderr'])
            
            current_stdout_hash = hashlib.md5(current_stdout_normalized.encode()).hexdigest()
            golden_stdout_hash = hashlib.md5(golden_stdout_normalized.encode()).hexdigest()
            
            current_stderr_hash = hashlib.md5(current_stderr_normalized.encode()).hexdigest()
            golden_stderr_hash = hashlib.md5(golden_stderr_normalized.encode()).hexdigest()
            
            if current_stdout_hash != golden_stdout_hash:
                differences.append("STDOUT output differs from golden standard (after normalization)")
            
            if current_stderr_hash != golden_stderr_hash:
                differences.append("STDERR output differs from golden standard (after normalization)")
            
            if differences:
                self.logger.error(f"❌ {test_name} FAILED:")
                for diff in differences:
                    self.logger.error(f"   - {diff}")
                
                # Save detailed diff for analysis
                diff_file = self.results_dir / f"{test_name}_diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(diff_file, 'w') as f:
                    json.dump({
                        "test_name": test_name,
                        "differences": differences,
                        "golden": {
                            "return_code": golden['return_code'],
                            "stdout_normalized": golden_stdout_normalized,
                            "stderr_normalized": golden_stderr_normalized,
                            "stdout_hash": golden_stdout_hash,
                            "stderr_hash": golden_stderr_hash
                        },
                        "current": {
                            "return_code": result.returncode,
                            "stdout_normalized": current_stdout_normalized,
                            "stderr_normalized": current_stderr_normalized,
                            "stdout_hash": current_stdout_hash,
                            "stderr_hash": current_stderr_hash
                        }
                    }, f, indent=2)
                
                return False
            else:
                self.logger.info(f"✅ {test_name} PASSED")
                return True
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ {test_name} TIMEOUT")
            return False
        except Exception as e:
            self.logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        self.logger.info("🚀 Running comprehensive test suite...")
        
        # Test 1: Module imports
        import_success = self._test_imports()
        
        # Test 2: Configuration validation
        config_success = self._test_configurations()
        
        # Test 3: Regression tests
        regression_success = self.run_regression_tests()
        
        all_success = import_success and config_success and regression_success
        
        if all_success:
            self.logger.info("🎉 All tests passed!")
        else:
            self.logger.error("💥 Some tests failed!")
            
        return all_success
    
    def _test_imports(self):
        """Test that all modules can be imported"""
        self.logger.info("📦 Testing module imports...")
        
        modules_to_test = [
            'backtester',
            'config',
            'data',
            'indicators',
            'strategy',
            'optimize_bayesian',
            'get_volatile_cryptos',
            'manage_results'
        ]
        
        failed_imports = []
        
        for module in modules_to_test:
            try:
                __import__(module)
                self.logger.info(f"✅ Import: {module}")
            except Exception as e:
                self.logger.error(f"❌ Import failed: {module} - {e}")
                failed_imports.append(module)
        
        if failed_imports:
            self.logger.error(f"❌ Failed to import: {failed_imports}")
            return False
        else:
            self.logger.info("✅ All modules imported successfully")
            return True
    
    def _test_configurations(self):
        """Test configuration validity"""
        self.logger.info("⚙️ Testing configurations...")
        
        try:
            from config import strategy_configs, param_sets, indicator_defaults
            
            # Validate strategy configs
            if not strategy_configs:
                self.logger.error("❌ No strategy configurations found")
                return False
            
            # Check that all strategies have required fields
            required_fields = ['long_entry', 'short_entry', 'long_exit', 'short_exit']
            for strategy_name, config in strategy_configs.items():
                for field in required_fields:
                    if field not in config:
                        self.logger.error(f"❌ Strategy {strategy_name} missing field: {field}")
                        return False
            
            self.logger.info(f"✅ Validated {len(strategy_configs)} strategy configurations")
            self.logger.info(f"✅ Found {len(param_sets)} parameter sets")
            self.logger.info(f"✅ Found {len(indicator_defaults)} indicator defaults")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Configuration test failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Regression Testing Framework")
    parser.add_argument('--capture', action='store_true', help='Capture golden standards')
    parser.add_argument('--test', action='store_true', help='Run regression tests')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    tester = RegressionTester()
    
    if args.capture:
        tester.capture_golden_standards()
    elif args.test:
        success = tester.run_regression_tests()
        sys.exit(0 if success else 1)
    elif args.all:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
