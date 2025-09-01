
import unittest
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web', 'backend'))

# Set testing environment variables before importing Flask app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SKIP_AUTH'] = 'true'

# Import Flask app and components
try:
    from web.backend.app import app
    from core.app_config import Config
    from core.scheduler import init_scheduler, get_scheduler
    from pricer import analyze_crypto_with_existing_system
    FLASK_APP_AVAILABLE = True
except ImportError as e:
    print(f"Flask app not available: {e}")
    FLASK_APP_AVAILABLE = False

class TestSchedulerAPI(unittest.TestCase):
    """Integration tests for the scheduler API."""

    def setUp(self):
        """Set up test client and initialize scheduler."""
        if not FLASK_APP_AVAILABLE:
            self.skipTest("Flask app not available")

        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')

        self.config = Config()
        self.config.DB_URI = f'sqlite:///{self.db_path}'

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = self.config.DB_URI

        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        self.scheduler = init_scheduler(self.config)

        # Remove all existing jobs to ensure a clean state for each test
        for job in self.scheduler.get_jobs():
            job.remove()

    def tearDown(self):
        """Clean up the scheduler and temporary database."""
        if FLASK_APP_AVAILABLE and self.scheduler.scheduler.running:
            self.scheduler.shutdown()
            self.app_context.pop()
        shutil.rmtree(self.temp_dir)

    @patch('pricer.get_crypto_data_merged')
    def test_schedule_job(self, mock_get_crypto_data):
        """Test scheduling a new job."""
        mock_get_crypto_data.return_value = MagicMock()
        config_dict = {
            'DB_URI': self.config.DB_URI,
            'DATA_DIR': self.config.DATA_DIR,
            'RESULTS_DIR': self.config.RESULTS_DIR,
            'CACHE_DIR': self.config.CACHE_DIR,
            'LOGS_DIR': self.config.LOGS_DIR
        }
        response = self.client.post('/api/scheduler/schedule', json={
            'function': 'analyze_crypto',
            'trigger': 'interval',
            'trigger_args': {'seconds': 10},
            'func_args': ['bitcoin', config_dict]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('job_id', data)

    @patch('pricer.get_crypto_data_merged')
    def test_get_jobs(self, mock_get_crypto_data):
        """Test getting the list of scheduled jobs."""
        mock_get_crypto_data.return_value = MagicMock()
        config_dict = {
            'DB_URI': self.config.DB_URI,
            'DATA_DIR': self.config.DATA_DIR,
            'RESULTS_DIR': self.config.RESULTS_DIR,
            'CACHE_DIR': self.config.CACHE_DIR,
            'LOGS_DIR': self.config.LOGS_DIR
        }
        # First, schedule a job
        self.client.post('/api/scheduler/schedule', json={
            'function': 'analyze_crypto',
            'trigger': 'interval',
            'trigger_args': {'seconds': 10},
            'func_args': ['bitcoin', config_dict]
        })

        # Now, get the list of jobs
        response = self.client.get('/api/scheduler/jobs')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn('id', data[0])
        self.assertIn('name', data[0])

if __name__ == '__main__':
    unittest.main(verbosity=2)
