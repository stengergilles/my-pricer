import json
import os
import logging
from pathlib import Path
from datetime import datetime
import signal # Added import

logger = logging.getLogger(__name__)

# Define the directory for job status files relative to the project root
# Assuming this file is in core/, so project root is one level up
PROJECT_ROOT = Path(__file__).parent.parent
JOB_STATUS_DIR = PROJECT_ROOT / "data" / "job_status"

def _get_status_filepath(job_id: str) -> Path:
    """Returns the full path to a job's status file."""
    return JOB_STATUS_DIR / f"{job_id}.json"

def update_job_status(job_id: str, status: str, message: str = None, progress: float = None, log_path: str = None):
    """
    Updates the status of a job by writing to its dedicated JSON file.
    """
    os.makedirs(JOB_STATUS_DIR, exist_ok=True)
    filepath = _get_status_filepath(job_id)
    
    # Try to read existing data to preserve fields like 'log_path' and 'pids'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                content = f.read().strip()
                if content:
                    job_status = json.loads(content)
                else:
                    job_status = {}
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

    # Ensure stop_requested and pids are always present
    if "stop_requested" not in job_status:
        job_status["stop_requested"] = False
    if "pids" not in job_status: # Initialize pids list
        job_status["pids"] = []

    try:
        # Write to a temporary file first
        temp_filepath = str(filepath) + ".tmp"
        with open(temp_filepath, 'w') as f:
            json.dump(job_status, f, indent=2)
        # Atomically rename the temporary file to the final destination
        os.replace(temp_filepath, filepath)
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
        for attempt in range(3):
            try:
                with open(filepath, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        if attempt < 2:
                            import time
                            time.sleep(0.1)
                            continue
                        return {"job_id": job_id, "status": "unknown", "message": "Status file is empty."}
                    return json.loads(content)
            except Exception as e:
                if attempt < 2:
                    import time
                    time.sleep(0.1)
                    continue
                logger.error(f"Failed to read status for job {job_id}: {e}")
                return {"job_id": job_id, "status": "error", "message": f"Failed to read status file: {e}"}
    else:
        return {"job_id": job_id, "status": "unknown", "message": "Status file not found."}

def register_job_process(job_id: str, pid: int):
    """
    Registers a process ID (PID) with a job.
    """
    filepath = _get_status_filepath(job_id)
    job_status = get_job_status(job_id) # Get current status
    
    if "pids" not in job_status:
        job_status["pids"] = []
    
    if pid not in job_status["pids"]:
        job_status["pids"].append(pid)
        try:
            with open(filepath, 'w') as f:
                json.dump(job_status, f, indent=2)
            logger.info(f"Registered PID {pid} for job {job_id}.")
        except Exception as e:
            logger.error(f"Failed to register PID {pid} for job {job_id}: {e}")

def unregister_job_process(job_id: str, pid: int):
    """
    Unregisters a process ID (PID) from a job.
    """
    filepath = _get_status_filepath(job_id)
    job_status = get_job_status(job_id) # Get current status

    if "pids" in job_status and pid in job_status["pids"]:
        job_status["pids"].remove(pid)
        try:
            with open(filepath, 'w') as f:
                json.dump(job_status, f, indent=2)
            logger.info(f"Unregistered PID {pid} from job {job_id}.")
        except Exception as e:
            logger.error(f"Failed to unregister PID {pid} for job {job_id}: {e}")

def request_job_stop(job_id: str):
    """
    Sets a flag in the job's status file indicating that a stop has been requested.
    Also attempts to terminate any registered processes for the job.
    """
    filepath = _get_status_filepath(job_id)
    job_status = {}
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
                if content:
                    job_status = json.loads(content)
        except json.JSONDecodeError:
            pass # File corrupted, start with empty status

    job_status["stop_requested"] = True
    job_status["timestamp"] = datetime.now().isoformat()
    job_status["message"] = "Stop requested."
    
    # Attempt to terminate registered processes
    pids_to_terminate = job_status.get("pids", [])
    for pid in pids_to_terminate:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to PID {pid} for job {job_id}.")
        except ProcessLookupError:
            logger.warning(f"PID {pid} for job {job_id} not found (already terminated?).")
        except Exception as e:
            logger.error(f"Failed to send SIGTERM to PID {pid} for job {job_id}: {e}. Trying SIGKILL.")
            try:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Sent SIGKILL to PID {pid} for job {job_id}.")
            except ProcessLookupError:
                logger.warning(f"PID {pid} for job {job_id} not found (already terminated?).")
            except Exception as e_kill:
                logger.error(f"Failed to send SIGKILL to PID {pid} for job {job_id}: {e_kill}")
    
    # Clear PIDs after attempting termination
    job_status["pids"] = []

    try:
        with open(filepath, 'w') as f:
            json.dump(job_status, f, indent=2)
        logger.info(f"Stop requested for job {job_id}. Registered processes terminated.")
    except Exception as e:
        logger.error(f"Failed to request stop for job {job_id}: {e}")

def is_job_stop_requested(job_id: str) -> bool:
    """
    Checks if a stop has been requested for a given job.
    """
    filepath = _get_status_filepath(job_id)
    if filepath.exists():
        for attempt in range(3):
            try:
                with open(filepath, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        if attempt < 2:
                            import time
                            time.sleep(0.1)
                            continue
                        return False
                    job_status = json.loads(content)
                    return job_status.get("stop_requested", False)
            except Exception as e:
                if attempt < 2:
                    import time
                    time.sleep(0.1)
                    continue
                logger.error(f"Failed to read stop request for job {job_id}: {e}")
                return False
    return False
