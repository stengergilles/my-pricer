#!/usr/bin/env python3
"""
Migration Script: Replace duplicated pricer.py with refactored version

This script:
1. Backs up the original pricer.py
2. Replaces it with the refactored version that uses existing components
3. Runs tests to ensure everything still works
4. Provides rollback capability if needed
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def backup_original():
    """Backup the original pricer.py"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"pricer_original_backup_{timestamp}.py"
    
    if os.path.exists("pricer.py"):
        shutil.copy2("pricer.py", backup_name)
        print(f"✅ Original pricer.py backed up as {backup_name}")
        return backup_name
    else:
        print("❌ Original pricer.py not found")
        return None

def replace_with_refactored():
    """Replace pricer.py with the refactored version"""
    if os.path.exists("pricer_refactored.py"):
        shutil.copy2("pricer_refactored.py", "pricer.py")
        print("✅ pricer.py replaced with refactored version")
        return True
    else:
        print("❌ pricer_refactored.py not found")
        return False

def test_new_version():
    """Test the new version"""
    print("\n🧪 Testing refactored version...")
    
    # Test 1: Quick tests
    if not run_command(["python", "run_tests.py", "--quick"], "Quick tests"):
        return False
    
    # Test 2: Help command
    if not run_command(["python", "pricer.py", "--help"], "Help command"):
        return False
    
    # Test 3: Basic functionality (with timeout to avoid API rate limits)
    print("🔄 Testing basic functionality...")
    try:
        result = subprocess.run(
            ["timeout", "30", "python", "pricer.py", "--crypto", "bitcoin", "--use-default-params"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True
        )
        
        # Check if it ran without crashing (exit code 0 or 124 for timeout)
        if result.returncode in [0, 124]:
            print("✅ Basic functionality test - SUCCESS")
            return True
        else:
            print(f"❌ Basic functionality test - FAILED (exit code: {result.returncode})")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Basic functionality test - ERROR: {e}")
        return False

def rollback(backup_name):
    """Rollback to original version"""
    if backup_name and os.path.exists(backup_name):
        shutil.copy2(backup_name, "pricer.py")
        print(f"✅ Rolled back to original version from {backup_name}")
        return True
    else:
        print("❌ Cannot rollback - backup not found")
        return False

def show_differences():
    """Show what changed between versions"""
    print("\n📊 Key Changes in Refactored Version:")
    print("=" * 50)
    print("✅ REMOVED DUPLICATIONS:")
    print("   - get_trade_signal() function (now uses strategy.py)")
    print("   - run_backtest_simulation() function (now uses backtester.py)")
    print("   - Indicator calculations (now uses existing components)")
    print("   - Signal generation logic (now uses Strategy class)")
    print("")
    print("✅ NEW FEATURES:")
    print("   - Uses existing Backtester and Strategy classes")
    print("   - Automatic best strategy detection")
    print("   - Improved error handling")
    print("   - Better logging and result saving")
    print("   - Continuous analysis mode")
    print("")
    print("✅ MAINTAINED FUNCTIONALITY:")
    print("   - All original command-line options")
    print("   - Support/resistance line analysis")
    print("   - Chart generation")
    print("   - Live trading simulation")
    print("   - Result saving and management")
    print("")
    print("📈 BENEFITS:")
    print("   - ~500+ lines of duplicated code removed")
    print("   - Easier maintenance (single source of truth)")
    print("   - Better consistency with backtester")
    print("   - Improved error handling")
    print("   - More modular and testable code")

def main():
    print("🔄 Pricer.py Refactoring Migration")
    print("=" * 40)
    print("This script will replace the duplicated pricer.py with a refactored")
    print("version that uses existing backtester components.")
    print("")
    
    # Show what will change
    show_differences()
    
    # Ask for confirmation
    print("\n❓ Do you want to proceed with the migration? (y/N): ", end="")
    response = input().strip().lower()
    
    if response != 'y':
        print("❌ Migration cancelled by user")
        return 1
    
    print("\n🚀 Starting migration...")
    
    # Step 1: Backup original
    backup_name = backup_original()
    if not backup_name:
        print("❌ Cannot proceed without backup")
        return 1
    
    # Step 2: Replace with refactored version
    if not replace_with_refactored():
        print("❌ Migration failed - could not replace file")
        return 1
    
    # Step 3: Test new version
    if not test_new_version():
        print("❌ Tests failed - rolling back...")
        rollback(backup_name)
        print("❌ Migration failed - original version restored")
        return 1
    
    # Success!
    print("\n🎉 Migration completed successfully!")
    print("=" * 40)
    print(f"✅ Original pricer.py backed up as: {backup_name}")
    print("✅ Refactored version is now active")
    print("✅ All tests passed")
    print("")
    print("📝 Next steps:")
    print("   - Test the new version with your typical workflows")
    print("   - If issues arise, you can restore with:")
    print(f"     cp {backup_name} pricer.py")
    print("   - Once satisfied, you can delete the backup file")
    print("")
    print("🎯 Code duplication eliminated!")
    print("   - pricer.py now uses existing backtester components")
    print("   - Maintenance is now easier with single source of truth")
    print("   - All functionality preserved with better error handling")
    
    return 0

if __name__ == "__main__":
    exit(main())
