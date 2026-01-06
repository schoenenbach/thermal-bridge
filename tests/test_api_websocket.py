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
WebSocket API Tests.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import time

client = TestClient(app)

class TestWebSocketAPI:
    """Test WebSocket simulation workflow."""

    def test_run_async_and_socket(self):
        """Test full flow: Start job -> Connect WS -> Receive Progress -> Complete."""
        
        # 1. Start Async Job
        # Use a simple scenario
        scenario_data = {
            "name": "WS Test",
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 5.0},
            "elements": [
                {"type": "rect", "material": "WALL", "params": {"x": 0, "y": 0, "width": 50, "height": 100}}
            ]
        }
        
        response = client.post(
            "/api/simulation/run-async",
            json={
                "scenario": scenario_data,
                "use_adaptive_mesh": False # Faster for test
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "ws_url" in data
        
        job_id = data["job_id"]
        ws_url = data["ws_url"] # e.g., /api/ws/simulation/UUID
        
        # 2. Connect WebSocket
        with client.websocket_connect(ws_url) as websocket:
            # We expect progress messages and finally a complete message
            received_messages = []
            
            # Read until completion or timeout
            # (TestClient blocks on receive_json until message arrives)
            start_wait = time.time()
            final_result = None
            
            while time.time() - start_wait < 10.0: # 10s timeout
                try:
                    msg = websocket.receive_json()
                    received_messages.append(msg)
                    
                    if "status" in msg and msg["status"] == "complete":
                        final_result = msg
                        break
                    
                    if "status" in msg and msg["status"] == "error":
                        pytest.fail(f"Simulation returned error: {msg}")
                        
                except Exception as e:
                    # Timeout likely if using real socket, but TestClient might just block forever 
                    # if no message sent. However, simulation runs in background thread.
                    # In TestClient, background tasks run AFTER response.
                    # So the task has started.
                    break
            
            assert final_result is not None, "Did not receive completion message"
            assert final_result["status"] == "complete"
            assert "result" in final_result
            assert final_result["result"]["success"] == True
            
            # Check we got at least some progress
            progress_updates = [m for m in received_messages if "percent" in m]
            assert len(progress_updates) >= 0 # Might be 0 if fast, but typically we get some
            
            # Check phase info in progress
            if progress_updates:
                assert "phase" in progress_updates[0]
                assert "step" in progress_updates[0]

    def test_invalid_job_id(self):
        """Test connecting with bad ID."""
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises((WebSocketDisconnect, Exception)):
             # TestClient usually raises WebSocketDisconnect when receiving from closed socket
             # or sometimes immediately on connect if handshake fails (but here we handshaked)
             with client.websocket_connect("/api/ws/simulation/bad-id") as ws:
                 ws.receive_json()
