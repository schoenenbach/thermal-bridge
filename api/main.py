"""
FastAPI Application for Thermal Bridge Simulator.

REST API foundation for future React/Angular frontend migration.
Provides endpoints for scenario validation, simulation, and data retrieval.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import scenarios, simulation, materials, websocket, schema

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
