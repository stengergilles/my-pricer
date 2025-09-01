
from flask import Blueprint, request, jsonify
from core.scheduler import get_scheduler
from core.app_config import Config
from pricer import analyze_crypto_with_existing_system

schedulable_functions = {
    'analyze_crypto': analyze_crypto_with_existing_system
}

scheduler_bp = Blueprint('scheduler_bp', __name__)

@scheduler_bp.route('/schedule', methods=['POST'])
def schedule_job():
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

@scheduler_bp.route('/jobs', methods=['GET'])
def get_jobs():
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

@scheduler_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
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

@scheduler_bp.route('/jobs/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    scheduler = get_scheduler()
    scheduler.pause_job(job_id)
    return jsonify({'status': 'paused'})

@scheduler_bp.route('/jobs/<job_id>/resume', methods=['POST'])
def resume_job(job_id):
    scheduler = get_scheduler()
    scheduler.resume_job(job_id)
    return jsonify({'status': 'resumed'})

@scheduler_bp.route('/jobs/<job_id>', methods=['DELETE'])
def remove_job(job_id):
    scheduler = get_scheduler()
    scheduler.remove_job(job_id)
    return jsonify({'status': 'removed'})
