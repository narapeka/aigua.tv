"""Folder browsing and scanning API endpoints"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Optional

from webui.models.schemas import ScanFoldersRequest, ScanFoldersResponse, FolderItemSchema

router = APIRouter(prefix="/api/folders", tags=["folders"])


def _is_safe_path(path: Path, base: Path) -> bool:
    """Check if path is within base directory (prevent directory traversal)"""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


@router.post("/scan", response_model=ScanFoldersResponse)
async def scan_folders(request: ScanFoldersRequest):
    """Scan source folder for TV show folders"""
    try:
        source_path = Path(request.source_folder).resolve()
        
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Source folder does not exist")
        
        if not source_path.is_dir():
            raise HTTPException(status_code=400, detail="Source path is not a directory")
        
        # Get all subdirectories
        folders = [d.name for d in source_path.iterdir() if d.is_dir()]
        folders.sort()
        
        return ScanFoldersResponse(folders=folders)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan folders: {str(e)}")


@router.get("/browse")
async def browse_folder(path: Optional[str] = None, base: Optional[str] = None):
    """Browse directory structure"""
    try:
        if path:
            browse_path = Path(path).resolve()
        elif base:
            browse_path = Path(base).resolve()
        else:
            # Default to home directory
            browse_path = Path.home()
        
        if not browse_path.exists():
            raise HTTPException(status_code=404, detail="Path does not exist")
        
        if not browse_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        # Security: restrict to home directory or below
        home_path = Path.home()
        if not _is_safe_path(browse_path, home_path):
            # Allow if it's an absolute path that exists (for network drives, etc.)
            # But be cautious
            if not browse_path.is_absolute():
                raise HTTPException(status_code=403, detail="Access denied: path outside allowed directory")
        
        items = []
        for item in browse_path.iterdir():
            try:
                items.append(FolderItemSchema(
                    name=item.name,
                    path=str(item),
                    is_directory=item.is_dir()
                ))
            except (PermissionError, OSError):
                # Skip items we can't access
                continue
        
        # Sort: directories first, then by name
        items.sort(key=lambda x: (not x.is_directory, x.name.lower()))
        
        return {"path": str(browse_path), "items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to browse folder: {str(e)}")

