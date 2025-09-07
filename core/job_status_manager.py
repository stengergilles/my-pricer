import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Define the directory for job status files relative to the project root
# Assuming this file is in core/, so project root is one level up
PROJECT_ROOT = Path(__file__).parent.parent
JOB_STATUS_DIR = PROJECT_ROOT / "web" / "data" / "job_status"

def _get_status_filepath(job_id: str) -> Path:
    """Returns the full path to a job's status file."""
    return JOB_STATUS_DIR / f"{job_id}.json"

def update_job_status(job_id: str, status: str, message: str = None, progress: float = None, log_path: str = None):
    """
    Updates the status of a job by writing to its dedicated JSON file.
    """
    os.makedirs(JOB_STATUS_DIR, exist_ok=True)
    filepath = _get_status_filepath(job_id)
    
    # Try to read existing data to preserve fields like 'log_path'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                job_status = json.load(f)
            except json.JSONDecodeError:
                job_status = {} # Start fresh if file is corrupted
    else:
        job_status = {}

    # Update status fields
    job_status.update({
        "job_id": job_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    })

    if message is not None:
        job_status["message"] = message
    if progress is not None:
        job_status["progress"] = progress
    if log_path is not None:
        job_status["log_path"] = log_path

    try:
        with open(filepath, 'w') as f:
            json.dump(job_status, f, indent=2)
        logger.info(f"Job {job_id} status updated to: {status}")
    except Exception as e:
        logger.error(f"Failed to update status for job {job_id}: {e}")

def get_job_status(job_id: str) -> dict:
    """
    Retrieves the status of a job from its JSON file.
    Returns a dictionary with status information, or a default 'unknown' status if not found.
    """
    filepath = _get_status_filepath(job_id)
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read status for job {job_id}: {e}")
            return {"job_id": job_id, "status": "error", "message": f"Failed to read status file: {e}"}
    else:
        return {"job_id": job_id, "status": "unknown", "message": "Status file not found."}