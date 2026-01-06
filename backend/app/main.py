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
FastAPI Application for Thermal Bridge Simulator.

REST API foundation for future React/Angular frontend migration.
Provides endpoints for scenario validation, simulation, and data retrieval.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import scenarios, simulation, materials, websocket, schema

app = FastAPI(
    title="Thermal Bridge Simulator API",
    description="REST API for thermal bridge simulation and analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(materials.router, prefix="/api/materials", tags=["Materials"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(schema.router, prefix="/api/schema", tags=["Schema"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Thermal Bridge Simulator API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "solver": "available"
        }
    }
