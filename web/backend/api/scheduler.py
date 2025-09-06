from flask import request, jsonify
from flask_restful import Resource
from core.scheduler import get_scheduler # Keep for now, might remove later if engine fully encapsulates
from pricer import optimize_crypto_with_existing_system
from web.backend.auth.middleware import requires_auth
from core.trading_engine import TradingEngine # Import TradingEngine
from core.optimize_cryptos_job import run_optimize_cryptos_job # Import the new job function

# Note: If analyze_crypto_with_existing_system needs to be part of the engine,
# this mapping might need to be adjusted or moved.
schedulable_functions = {
    'optimize_crypto': optimize_crypto_with_existing_system,
    'optimize_cryptos_job': run_optimize_cryptos_job # Add the new job
}

class ScheduleJobAPI(Resource):
    def __init__(self, engine):
        super().__init__() # Call parent constructor without args/kwargs
        self.engine = engine
        self.scheduler = self.engine.get_scheduler() # Assuming engine provides scheduler access

    @requires_auth('create:jobs')
    def post(self):
        data = request.get_json()
        func_path = data.get('function')
        trigger = data.get('trigger')
        trigger_args = data.get('trigger_args')
        func_args = data.get('func_args', [])
        func_kwargs = data.get('func_kwargs', {})

        if func_path not in schedulable_functions:
            return jsonify({'error': 'Function not allowed'}), 400

        # Special handling for 'optimize_cryptos_job' to pass its specific kwargs
        if func_path == 'optimize_cryptos_job':
            job_func = schedulable_functions[func_path]
            # Pass func_kwargs directly to the job function
            job = self.scheduler.add_job(
                func=job_func,
                trigger=trigger,
                kwargs=func_kwargs, # Pass func_kwargs directly
                args=func_args,
                **trigger_args,
            )
        else:
            # Existing logic for other functions
            job = self.scheduler.add_job(
                func=schedulable_functions[func_path],
                trigger=trigger,
                kwargs={'config': self.engine.config, **func_kwargs},
                args=func_args,
                **trigger_args,
            )

        return jsonify({'job_id': job.id})

class JobsAPI(Resource):
    def __init__(self, engine):
        super().__init__() # Call parent constructor without args/kwargs
        self.engine = engine
        self.scheduler = self.engine.get_scheduler() # Assuming engine provides scheduler access

    @requires_auth('read:jobs')
    def get(self):
        jobs = self.scheduler.get_jobs()
        job_list = []
        for job in jobs:
            job_list.append({
                'id': job.id,
                'name': job.name,
                'trigger': str(job.trigger),
                'next_run_time': str(job.next_run_time)
            })
        return jsonify(job_list)

class JobAPI(Resource):
    def __init__(self, engine):
        super().__init__() # Call parent constructor without args/kwargs
        self.engine = engine
        self.scheduler = self.engine.get_scheduler() # Assuming engine provides scheduler access

    @requires_auth('read:jobs')
    def get(self, job_id):
        job = self.scheduler.get_job(job_id)
        if job:
            return jsonify({
                'id': job.id,
                'name': job.name,
                'trigger': str(job.trigger),
                'next_run_time': str(job.next_run_time)
            })
        return jsonify({'error': 'Job not found'}), 404

    @requires_auth('manage:jobs')
    def post(self, job_id):
        data = request.get_json()
        action = data.get('action')

        if action == 'pause':
            self.scheduler.pause_job(job_id)
            return jsonify({'status': 'paused'})
        elif action == 'resume':
            self.scheduler.resume_job(job_id)
            return jsonify({'status': 'resumed'})
        else:
            return jsonify({'error': 'Invalid action'}), 400

    @requires_auth('manage:jobs')
    def delete(self, job_id):
        self.scheduler.remove_job(job_id)
        return jsonify({'status': 'removed'})

class JobLogsAPI(Resource):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.scheduler = self.engine.get_scheduler()

    @requires_auth('read:jobs')
    def get(self, job_id):
        # For now, return a placeholder. Actual log retrieval needs a more robust logging setup.
        logs = self.scheduler.get_job_logs(job_id)
        return jsonify({'job_id': job_id, 'logs': logs})
