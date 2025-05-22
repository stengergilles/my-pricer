import subprocess
import sys

def test_cli_monitor_help_runs():
    # Replace "stock_monitoring_app.cli" with your actual CLI entry point/module if different
    result = subprocess.run([sys.executable, "-m", "stock_monitoring_app.cli.monitor", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()
