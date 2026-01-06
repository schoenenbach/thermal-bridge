# Copyright (C) 2026 Thomas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
WebSocket Routes.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from backend.app.jobs import job_manager

router = APIRouter()

@router.websocket("/simulation/{job_id}")
async def websocket_simulation(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for simulation progress updates.
    Client connects with job_id obtained from /api/simulation/run-async.
    """
    job = job_manager.get_job(job_id)
    if not job:
        # We can't use HTTPException in websocket context, 
        # so we accept and close with code
        await websocket.accept()
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()
    
    # Register connection
    success = await job_manager.connect_websocket(job_id, websocket)
    if not success:
        await websocket.close(code=4004, reason="Job not found/expired")
        return
        
    try:
        # Send current status immediately upon connection
        if job["status"] == "running" and job["progress"]:
            await websocket.send_json(job["progress"])
        elif job["status"] == "completed" and job["result"]:
             await websocket.send_json({
                "status": "complete",
                "result": job["result"]
            })
        elif job["status"] == "error" and job["error"]:
             await websocket.send_json({
                "status": "error",
                "error": job["error"]
            })
            
        # Keep connection open until client disconnects
        # We don't expect messages from client, but we need to listen
        # to detect disconnects
        while True:
            data = await websocket.receive_text()
            # Echo or ignore
            
    except WebSocketDisconnect:
        await job_manager.disconnect_websocket(job_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await job_manager.disconnect_websocket(job_id)
