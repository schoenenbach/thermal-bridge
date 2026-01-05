"""
Job Manager for Async Simulations.

Tracks running simulation jobs and manages their state and WebSocket progress.
"""

import uuid
import time
from typing import Dict, Optional, Any, List
import asyncio
from fastapi import WebSocket

from backend.app.models import ProgressMessage, SimulationResult

class JobManager:
    """
    Manages async simulation jobs and their associated WebSocket connections.
    Keys are job_id strings.
    """
    
    def __init__(self):
        # job_id -> dict with state
        self.jobs: Dict[str, Dict[str, Any]] = {}
        # job_id -> active websocket (if connected)
        self.websockets: Dict[str, WebSocket] = {}
        # Simple lock to be safe (though CPython GIL mostly handles dict operations)
        self._lock = asyncio.Lock()

    def create_job(self) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "status": "created",
            "created_at": time.time(),
            "progress": None,
            "result": None,
            "error": None
        }
        return job_id

    async def connect_websocket(self, job_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a job."""
        if job_id not in self.jobs:
            return False
        
        self.websockets[job_id] = websocket
        return True

    async def disconnect_websocket(self, job_id: str):
        """Unregister a WebSocket connection."""
        if job_id in self.websockets:
            del self.websockets[job_id]

    async def set_progress(self, job_id: str, phase: str, step: int, total: int):
        """Update job progress and notify WebSocket client."""
        if job_id not in self.jobs:
            return

        percent = (step / total * 100.0) if total > 0 else 0.0
        
        progress = ProgressMessage(
            phase=phase,
            step=step,
            total=total,
            percent=percent
        )
        
        self.jobs[job_id]["status"] = "running"
        self.jobs[job_id]["progress"] = progress.model_dump()
        
        # Notify WebSocket if connected
        ws = self.websockets.get(job_id)
        if ws:
            try:
                await ws.send_json(progress.model_dump())
            except Exception:
                 # Connection likely closed
                 pass

    async def set_complete(self, job_id: str, result: SimulationResult):
        """Mark job as complete and send result."""
        if job_id not in self.jobs:
            return

        self.jobs[job_id]["status"] = "completed"
        self.jobs[job_id]["completed_at"] = time.time()
        self.jobs[job_id]["result"] = result.model_dump()
        
        # Send completion message
        ws = self.websockets.get(job_id)
        if ws:
            try:
                await ws.send_json({
                    "status": "complete",
                    "result": result.model_dump()
                })
                # We typically don't close here, let client close or send close frame
            except Exception:
                pass

    async def set_error(self, job_id: str, error: str):
        """Mark job as failed."""
        if job_id not in self.jobs:
            return

        self.jobs[job_id]["status"] = "error"
        self.jobs[job_id]["error"] = error
        
        ws = self.websockets.get(job_id)
        if ws:
            try:
                await ws.send_json({
                    "status": "error",
                    "error": error
                })
            except Exception:
                pass
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job info."""
        return self.jobs.get(job_id)

    def cleanup_old_jobs(self, max_age_seconds=3600):
        """Remove old finished jobs."""
        now = time.time()
        to_remove = []
        for job_id, job in self.jobs.items():
            # If completed/error and old
            if job["status"] in ["completed", "error"]:
                 if "completed_at" in job and (now - job["completed_at"] > max_age_seconds):
                     to_remove.append(job_id)
            # If created but stalled/abandoned (e.g. 1 hour with no updates)
            elif job["status"] == "created" and (now - job["created_at"] > max_age_seconds):
                to_remove.append(job_id)
                
        for job_id in to_remove:
            if job_id in self.jobs:
                del self.jobs[job_id]
            if job_id in self.websockets:
                del self.websockets[job_id]

# Global instance
job_manager = JobManager()
