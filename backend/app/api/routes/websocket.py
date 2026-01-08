"""
WebSocket API Routes
Real-time progress updates
"""

import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.cache_service import get_cache_service
from app.services.job_service import JobService

router = APIRouter()

# Store active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates

    Clients connect with a job_id and receive progress messages
    during execution.
    """
    await websocket.accept()

    # Add connection to active connections
    if job_id not in active_connections:
        active_connections[job_id] = set()
    active_connections[job_id].add(websocket)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "status",
            "data": {"status": "connected", "job_id": job_id}
        })

        # Keep connection alive and poll for job status
        cache = get_cache_service()
        job_service = JobService(cache)

        while True:
            # Check job status
            job_data = job_service.get_job(job_id)

            if job_data:
                # Send status update
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "status": job_data["status"],
                        "stats": job_data.get("stats", {})
                    }
                })

                # If job is completed or failed, send final message
                if job_data["status"] in ["completed", "failed", "cancelled"]:
                    await websocket.send_json({
                        "type": "completed" if job_data["status"] == "completed" else "error",
                        "data": {
                            "status": job_data["status"],
                            "stats": job_data.get("stats", {}),
                            "error": job_data.get("error")
                        }
                    })
                    break

            # Wait before next poll
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error for job {job_id}: {e}")
    finally:
        # Remove connection
        if job_id in active_connections:
            active_connections[job_id].discard(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]


async def broadcast_to_job(job_id: str, message: dict):
    """
    Broadcast message to all WebSocket clients for a job

    Args:
        job_id: Job identifier
        message: Message dict to broadcast
    """
    if job_id in active_connections:
        disconnected = set()

        for websocket in active_connections[job_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            active_connections[job_id].discard(websocket)
