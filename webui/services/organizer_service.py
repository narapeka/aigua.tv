"""Service wrapper for TVShowOrganizer"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from tv_show_organizer import TVShowOrganizer
from config import load_config
from tmdb import create_tmdb_client_from_config


class OrganizerService:
    """Service wrapper for TVShowOrganizer with preview support"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._organizer: Optional[TVShowOrganizer] = None
    
    def create_preview(self, source_folder: str, target_folder: str,
                      selected_folders: Optional[List[str]] = None,
                      manual_matches: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Create a preview of organization without actually moving files
        
        Args:
            source_folder: Source folder path
            target_folder: Target folder path
            selected_folders: Optional list of folder names to include
            manual_matches: Optional dict mapping folder_name -> tmdb_id
        
        Returns:
            Preview data dictionary
        """
        try:
            organizer = TVShowOrganizer(
                input_dir=source_folder,
                output_dir=target_folder,
                dry_run=True,
                verbose=False
            )
            
            # Set manual matches if provided
            if manual_matches:
                organizer._manual_matches = manual_matches
            
            # Run scan and organize (dry-run)
            organizer.scan_and_organize()
            
            # Get preview data
            preview_data = organizer.get_preview_data()
            
            # Apply selected folders filter if provided
            if selected_folders:
                preview_data['shows'] = [
                    show for show in preview_data['shows']
                    if show['folder_name'] in selected_folders
                ]
            
            return preview_data
        except Exception as e:
            self.logger.error(f"Error creating preview: {e}")
            raise
    
    def execute_organization(self, source_folder: str, target_folder: str,
                            selected_folders: List[str],
                            manual_matches: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Execute actual organization
        
        Args:
            source_folder: Source folder path
            target_folder: Target folder path
            selected_folders: List of folder names to process
            manual_matches: Optional dict mapping folder_name -> tmdb_id
        
        Returns:
            Result dictionary with stats
        """
        try:
            organizer = TVShowOrganizer(
                input_dir=source_folder,
                output_dir=target_folder,
                dry_run=False,
                verbose=False
            )
            
            # Set selected folders and manual matches
            organizer._selected_folders = set(selected_folders)
            if manual_matches:
                organizer._manual_matches = manual_matches
            
            # Run organization
            success = organizer.scan_and_organize()
            
            # Get final stats
            result = {
                'success': success,
                'stats': organizer.stats.copy(),
                'processed_shows': organizer.processed_shows.copy(),
                'unprocessed_shows': organizer.unprocessed_shows.copy()
            }
            
            return result
        except Exception as e:
            self.logger.error(f"Error executing organization: {e}")
            raise


# Global service instance
organizer_service = OrganizerService()

