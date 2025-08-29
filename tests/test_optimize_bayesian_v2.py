import unittest
import subprocess
import os

class TestOptimizeBayesianV2(unittest.TestCase):

    def test_optimize_bayesian_v2_script_runs_successfully(self):
        # Define the path to the script
        script_path = os.path.join(os.path.dirname(__file__), '..', 'optimize_bayesian_v2.py')
        
        # Define the command to run the script
        command = [
            'python',
            script_path,
            '--crypto', 'bitcoin',
            '--strategy', 'EMA_Only',
            '--n-trials', '1' # Use a small number of trials for quick test
        ]

        # Run the script as a subprocess
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        # Assert that the script exited successfully
        self.assertEqual(result.returncode, 0, f"Script exited with error code {result.returncode}. Stderr: {result.stderr}")

        # Assert that the success message is in stdout
        self.assertIn("Optimization completed successfully!", result.stdout)
        self.assertIn("Best value:", result.stdout)
        self.assertIn("Best parameters:", result.stdout)

    def test_optimize_bayesian_v2_script_handles_invalid_strategy(self):
        # Define the path to the script
        script_path = os.path.join(os.path.dirname(__file__), '..', 'optimize_bayesian_v2.py')
        
        # Define the command to run the script with an invalid strategy
        command = [
            'python',
            script_path,
            '--crypto', 'bitcoin',
            '--strategy', 'INVALID_STRATEGY',
            '--n-trials', '1'
        ]

        # Run the script as a subprocess
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        # Assert that the script exited with a non-zero error code
        self.assertNotEqual(result.returncode, 0, f"Script unexpectedly exited with code 0. Stderr: {result.stderr}")

        # Assert that the error message for invalid strategy is in stdout
        self.assertIn("Error: Unknown strategy 'INVALID_STRATEGY'", result.stdout)

if __name__ == '__main__':
    unittest.main()
