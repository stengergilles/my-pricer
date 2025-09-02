from flask import request, jsonify
from flask_restful import Resource
from core.scheduler import get_scheduler
from pricer import analyze_crypto_with_existing_system

schedulable_functions = {
    'analyze_crypto': analyze_crypto_with_existing_system
}

class ScheduleJobAPI(Resource):
    def post(self):
        data = request.get_json()
        func_path = data.get('function')
        trigger = data.get('trigger')
        trigger_args = data.get('trigger_args')
        func_args = data.get('func_args', [])
        func_kwargs = data.get('func_kwargs', {})

        if func_path not in schedulable_functions:
            return jsonify({'error': 'Function not allowed'}), 400

        scheduler = get_scheduler()
        job = scheduler.add_job(
            func=schedulable_functions[func_path],
            trigger=trigger,
            **trigger_args,
            args=func_args,
            kwargs=func_kwargs
        )

        return jsonify({'job_id': job.id})

class JobsAPI(Resource):
    def get(self):
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
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
    def get(self, job_id):
        scheduler = get_scheduler()
        job = scheduler.get_job(job_id)
        if job:
            return jsonify({
                'id': job.id,
                'name': job.name,
                'trigger': str(job.trigger),
                'next_run_time': str(job.next_run_time)
            })
        return jsonify({'error': 'Job not found'}), 404

    def post(self, job_id):
        scheduler = get_scheduler()
        data = request.get_json()
        action = data.get('action')

        if action == 'pause':
            scheduler.pause_job(job_id)
            return jsonify({'status': 'paused'})
        elif action == 'resume':
            scheduler.resume_job(job_id)
            return jsonify({'status': 'resumed'})
        else:
            return jsonify({'error': 'Invalid action'}), 400

    def delete(self, job_id):
        scheduler = get_scheduler()
        scheduler.remove_job(job_id)
        return jsonify({'status': 'removed'})