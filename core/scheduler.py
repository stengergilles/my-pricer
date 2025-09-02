import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import create_engine
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from core.app_config import Config

# Configure logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

class Scheduler:
    def __init__(self, app_config: Config, db_connection):
        self.app_config = app_config
        self.scheduler = BackgroundScheduler(jobstores=self._get_jobstores(db_connection))

    def _get_jobstores(self, db_connection):
        # Use a creator function to pass the pre-opened sqlite3.Connection
        engine = create_engine('sqlite:///', creator=lambda: db_connection)
        return {
            'default': SQLAlchemyJobStore(engine=engine)
        }

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def add_job(self, func, trigger, **kwargs):
        return self.scheduler.add_job(func, trigger, **kwargs)

    def get_jobs(self):
        return self.scheduler.get_jobs()

    def get_job(self, job_id):
        return self.scheduler.get_job(job_id)

    def pause_job(self, job_id):
        self.scheduler.pause_job(job_id)

    def resume_job(self, job_id):
        self.scheduler.resume_job(job_id)

    def remove_job(self, job_id):
        self.scheduler.remove_job(job_id)

    def add_listener(self, callback, mask):
        self.scheduler.add_listener(callback, mask)

def job_listener(event):
    if event.exception:
        logging.error(f'Job {event.job_id} failed with exception: {event.exception}')
    else:
        logging.info(f'Job {event.job_id} executed successfully')

# Initialize scheduler
scheduler = None

def init_scheduler(app_config: Config, db_connection):
    global scheduler
    if scheduler is None:
        scheduler = Scheduler(app_config, db_connection)
        scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        scheduler.start()
    return scheduler

def get_scheduler():
    global scheduler
    if scheduler is None:
        raise Exception("Scheduler not initialized")
    return scheduler