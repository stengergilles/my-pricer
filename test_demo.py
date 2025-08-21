#!/usr/bin/env python3
"""
Demo script to show how the testing framework detects regressions

This script demonstrates the testing framework by:
1. Running tests to establish baseline
2. Making a small change to code
3. Running tests again to detect the regression
4. Restoring the original code
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return result"""
    print(f"\n🔄 {description}")
    print("-" * 50)
    
    result = subprocess.run(cmd, cwd=Path.cwd())
    
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
    else:
        print(f"❌ {description} - FAILED")
    
    return result.returncode == 0

def main():
    print("🧪 Testing Framework Regression Detection Demo")
    print("=" * 60)
    
    # Step 1: Run baseline tests
    print("\n📋 Step 1: Running baseline tests")
    success = run_command(["python", "run_tests.py", "--quick"], "Quick baseline tests")
    
    if not success:
        print("❌ Baseline tests failed. Please fix issues first.")
        return
    
    # Step 2: Make a small change to demonstrate regression detection
    print("\n📋 Step 2: Making a small change to demonstrate regression detection")
    
    # Create a backup of a file we'll modify
    config_file = Path("config.py")
    backup_file = Path("config.py.backup")
    
    if not config_file.exists():
        print("❌ config.py not found")
        return
    
    # Backup original
    shutil.copy2(config_file, backup_file)
    print(f"✅ Backed up {config_file} to {backup_file}")
    
    try:
        # Make a small change (add a comment)
        with open(config_file, 'r') as f:
            content = f.read()
        
        modified_content = "# DEMO CHANGE - This line added by test demo\n" + content
        
        with open(config_file, 'w') as f:
            f.write(modified_content)
        
        print(f"✅ Added demo comment to {config_file}")
        
        # Step 3: Run tests again to see if they still pass
        print("\n📋 Step 3: Running tests after change")
        success = run_command(["python", "run_tests.py", "--quick"], "Tests after change")
        
        if success:
            print("✅ Tests still pass - change was non-breaking")
        else:
            print("❌ Tests failed - change introduced regression")
        
        # Step 4: Demonstrate regression test (if we had captured golden standards)
        print("\n📋 Step 4: Testing regression detection")
        print("ℹ️  In a real scenario, if you had captured golden standards")
        print("   and made a breaking change, regression tests would detect it.")
        
    finally:
        # Step 5: Restore original file
        print("\n📋 Step 5: Restoring original file")
        if backup_file.exists():
            shutil.copy2(backup_file, config_file)
            backup_file.unlink()
            print(f"✅ Restored {config_file} from backup")
        
        # Verify restoration
        print("\n📋 Step 6: Verifying restoration")
        success = run_command(["python", "run_tests.py", "--quick"], "Tests after restoration")
        
        if success:
            print("✅ Tests pass after restoration - system is back to baseline")
        else:
            print("❌ Tests still fail - there may be an issue")
    
    print("\n🎉 Demo completed!")
    print("\n💡 Key takeaways:")
    print("   - The testing framework can detect when changes break functionality")
    print("   - Quick tests provide fast feedback during development")
    print("   - Golden standards capture expected behavior for regression testing")
    print("   - Tests are designed to be non-invasive to your existing code")

if __name__ == "__main__":
    main()
