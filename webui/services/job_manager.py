"""Job manager for background tasks"""

import uuid
import threading
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobManager:
    """Manages background jobs for organization tasks"""
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_type: str, initial_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new job
        
        Args:
            job_type: Type of job (e.g., 'dry_run', 'execute')
            initial_data: Optional initial data for the job
        
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                'id': job_id,
                'type': job_type,
                'status': JobStatus.PENDING,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'progress': {},
                'result': None,
                'error': None,
                'data': initial_data or {}
            }
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update_job(self, job_id: str, status: Optional[JobStatus] = None,
                   progress: Optional[Dict[str, Any]] = None,
                   result: Optional[Any] = None,
                   error: Optional[str] = None) -> bool:
        """
        Update job status
        
        Returns:
            True if job was updated, False if not found
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if status:
                job['status'] = status
            if progress is not None:
                job['progress'].update(progress)
            if result is not None:
                job['result'] = result
            if error:
                job['error'] = error
            job['updated_at'] = datetime.now().isoformat()
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if job['status'] in (JobStatus.PENDING, JobStatus.RUNNING):
                job['status'] = JobStatus.CANCELLED
                job['updated_at'] = datetime.now().isoformat()
                return True
            return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        with self._lock:
            to_remove = [
                job_id for job_id, job in self._jobs.items()
                if datetime.fromisoformat(job['created_at']).timestamp() < cutoff
            ]
            for job_id in to_remove:
                del self._jobs[job_id]
        return len(to_remove)


# Global job manager instance
job_manager = JobManager()

