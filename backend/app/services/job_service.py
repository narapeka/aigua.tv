"""
Job Service
Manages job lifecycle and state updates
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.models.api_models import JobStatus
from app.services.cache_service import CacheService


class JobService:
    """Service for managing job state and operations"""

    def __init__(self, cache_service: CacheService):
        """
        Initialize job service

        Args:
            cache_service: Cache service instance
        """
        self.cache = cache_service

    def create_job(
        self,
        job_id: str,
        input_dir: str,
        output_dir: str,
        status: JobStatus = JobStatus.PENDING
    ) -> Dict[str, Any]:
        """
        Create a new job

        Args:
            job_id: Job identifier
            input_dir: Input directory
            output_dir: Output directory
            status: Initial status

        Returns:
            Job data dict
        """
        now = datetime.now()
        job_data = {
            "job_id": job_id,
            "status": status.value,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "stats": {},
            "processed_shows": [],
            "unprocessed_shows": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "error": None
        }

        self.cache.set_job(job_id, job_data)
        return job_data

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data

        Args:
            job_id: Job identifier

        Returns:
            Job data dict or None if not found
        """
        return self.cache.get_job(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None
    ) -> None:
        """
        Update job status

        Args:
            job_id: Job identifier
            status: New status
            error: Optional error message
        """
        job_data = self.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")

        job_data["status"] = status.value
        job_data["updated_at"] = datetime.now().isoformat()

        if error:
            job_data["error"] = error

        self.cache.update_job(job_id, job_data)

    def update_job_result(
        self,
        job_id: str,
        stats: Dict[str, int],
        processed_shows: list,
        unprocessed_shows: list,
        status: JobStatus = JobStatus.COMPLETED
    ) -> None:
        """
        Update job with dry-run results

        Args:
            job_id: Job identifier
            stats: Statistics dict
            processed_shows: List of processed shows
            unprocessed_shows: List of unprocessed shows
            status: Job status
        """
        job_data = self.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")

        job_data["status"] = status.value
        job_data["stats"] = stats
        job_data["processed_shows"] = processed_shows
        job_data["unprocessed_shows"] = unprocessed_shows
        job_data["updated_at"] = datetime.now().isoformat()

        self.cache.update_job(job_id, job_data)

    def update_show_selection(
        self,
        job_id: str,
        show_id: str,
        selected: bool
    ) -> None:
        """
        Update show selection state

        Args:
            job_id: Job identifier
            show_id: Show identifier
            selected: Selection state
        """
        job_data = self.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")

        # Find and update show
        for show in job_data["processed_shows"]:
            if show["id"] == show_id:
                show["selected"] = selected
                break

        job_data["updated_at"] = datetime.now().isoformat()
        self.cache.update_job(job_id, job_data)

    def update_season_selection(
        self,
        job_id: str,
        show_id: str,
        season_number: int,
        selected: bool
    ) -> None:
        """
        Update season selection state

        Args:
            job_id: Job identifier
            show_id: Show identifier
            season_number: Season number
            selected: Selection state
        """
        job_data = self.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")

        # Find and update season
        for show in job_data["processed_shows"]:
            if show["id"] == show_id:
                for season in show["seasons"]:
                    if season["season_number"] == season_number:
                        season["selected"] = selected
                        break
                break

        job_data["updated_at"] = datetime.now().isoformat()
        self.cache.update_job(job_id, job_data)

    def update_episode_selection(
        self,
        job_id: str,
        show_id: str,
        season_number: int,
        episode_number: int,
        selected: bool
    ) -> None:
        """
        Update episode selection state

        Args:
            job_id: Job identifier
            show_id: Show identifier
            season_number: Season number
            episode_number: Episode number
            selected: Selection state
        """
        job_data = self.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")

        # Find and update episode
        for show in job_data["processed_shows"]:
            if show["id"] == show_id:
                for season in show["seasons"]:
                    if season["season_number"] == season_number:
                        for episode in season["episodes"]:
                            if episode["episode_number"] == episode_number:
                                episode["selected"] = selected
                                break
                        break
                break

        job_data["updated_at"] = datetime.now().isoformat()
        self.cache.update_job(job_id, job_data)

    def update_show_category(
        self,
        job_id: str,
        show_id: str,
        category: str
    ) -> None:
        """
        Update show category

        Args:
            job_id: Job identifier
            show_id: Show identifier
            category: New category
        """
        job_data = self.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")

        # Find and update show
        for show in job_data["processed_shows"]:
            if show["id"] == show_id:
                show["category"] = category
                break

        job_data["updated_at"] = datetime.now().isoformat()
        self.cache.update_job(job_id, job_data)

    def delete_job(self, job_id: str) -> None:
        """
        Delete job

        Args:
            job_id: Job identifier
        """
        self.cache.delete_job(job_id)
