#!/usr/bin/env python3
"""
Main Test Runner for Crypto Trading System

This script provides a unified interface to run all types of tests:
- Unit tests
- Integration tests  
- Performance tests
- Regression tests

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --performance      # Run only performance tests
    python run_tests.py --regression       # Run only regression tests
    python run_tests.py --capture          # Capture golden standards
    python run_tests.py --quick            # Run quick test suite
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path

def run_command(cmd, description, timeout=300):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            timeout=timeout
        )
        end_time = time.time()
        
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} PASSED ({duration:.1f}s)")
            return True
        else:
            print(f"❌ {description} FAILED (return code: {result.returncode}, {duration:.1f}s)")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} TIMED OUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"💥 {description} ERROR: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Runner for Crypto Trading System")
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--functional', action='store_true', help='Run functional tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--regression', action='store_true', help='Run regression tests')
    parser.add_argument('--capture', action='store_true', help='Capture golden standards')
    parser.add_argument('--quick', action='store_true', help='Run quick test suite')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # If no specific test type is specified, run all except regression (which can be flaky)
    if not any([args.unit, args.integration, args.functional, args.performance, args.regression, args.capture, args.quick]):
        run_all = True
    else:
        run_all = False
    
    print("🧪 Crypto Trading System Test Runner")
    print(f"📁 Working directory: {Path.cwd()}")
    print(f"🐍 Python version: {sys.version}")
    
    results = []
    
    # Capture golden standards if requested
    if args.capture or run_all:
        success = run_command(
            [sys.executable, "tests/test_runner.py", "--capture"],
            "Capturing Golden Standards",
            timeout=600  # 10 minutes for capture
        )
        results.append(("Golden Standards Capture", success))
    
    # Quick tests (basic functionality)
    if args.quick:
        cmd = [sys.executable, "-m", "unittest", "tests.test_unit.TestConfiguration"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Quick Configuration Tests")
        results.append(("Quick Tests", success))
        
        cmd = [sys.executable, "-m", "unittest", "tests.test_integration.TestSystemIntegration.test_python_syntax_all_files"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Quick Syntax Tests")
        results.append(("Syntax Tests", success))
    
    # Unit tests
    if args.unit or run_all:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_unit.py"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Unit Tests")
        results.append(("Unit Tests", success))
    
    # Integration tests
    if args.integration or run_all:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_integration.py"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Integration Tests", timeout=600)
        results.append(("Integration Tests", success))
    
    # Functional tests
    if args.functional or run_all:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_functional.py"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Functional Tests", timeout=600)
        results.append(("Functional Tests", success))
    
    # Performance tests
    if args.performance or run_all:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_performance.py"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Performance Tests")
        results.append(("Performance Tests", success))
    
    # Regression tests (optional, can be flaky due to external dependencies)
    if args.regression:
        success = run_command(
            [sys.executable, "tests/test_runner.py", "--test"],
            "Regression Tests",
            timeout=600  # 10 minutes for regression tests
        )
        results.append(("Regression Tests", success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")
    
    print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED!")
        exit_code = 0
    else:
        print(f"💥 {failed_tests} test(s) failed!")
        exit_code = 1
    
    # Additional information
    print(f"\n💡 Tips:")
    print(f"   - Run 'python run_tests.py --capture' to update golden standards after intentional changes")
    print(f"   - Run 'python run_tests.py --quick' for fast feedback during development")
    print(f"   - Check 'tests/test_results/' for detailed failure analysis")
    print(f"   - Use '--verbose' flag for detailed test output")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
