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
Simulation API Routes.

Provides endpoints for running simulations and parameter sweeps.
"""

import os
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.app.models import (
    SimulationRequest,
    SimulationResult,
    SimulationMetrics,
    TemperatureData,
    OptimizationRequest,
    OptimizationResult,
    OptimizationPoint,
)
import numpy as np

router = APIRouter()

# Results storage directory
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def compress_temperature_data(temp_array: np.ndarray, canvas_width: float, 
                               canvas_height: float, max_resolution: int = 200) -> TemperatureData:
    """
    Downsample and compress temperature array for frontend rendering.
    
    Args:
        temp_array: 2D numpy array of temperatures
        canvas_width: Canvas width in mm
        canvas_height: Canvas height in mm
        max_resolution: Maximum grid dimension (larger grids are downsampled)
    
    Returns:
        TemperatureData model ready for JSON serialization
    """
    rows, cols = temp_array.shape
    
    # Downsample if too large
    if max(rows, cols) > max_resolution:
        step_r = max(1, rows // max_resolution)
        step_c = max(1, cols // max_resolution)
        downsampled = temp_array[::step_r, ::step_c]
    else:
        downsampled = temp_array
    
    # Round to 2 decimal places to reduce JSON size
    data = np.round(downsampled, 2).tolist()
    
    return TemperatureData(
        data=data,
        width=float(canvas_width),
        height=float(canvas_height),
        temp_min=float(np.min(temp_array)),
        temp_max=float(np.max(temp_array)),
        rows=len(data),
        cols=len(data[0]) if data else 0
    )


@router.post("/run", response_model=SimulationResult)
async def run_simulation(request: SimulationRequest):
    """Run a thermal bridge simulation."""
    from backend.core.simulation_engine import solve_scenario
    
    start_time = time.time()
    
    try:
        # Apply grid override if specified
        scenario = request.scenario.copy()
        if request.override_grid_size and request.override_grid_size > 0:
            if 'canvas' in scenario:
                scenario['canvas']['grid'] = request.override_grid_size
        
        # Run simulation
        # Engine expects a wrapper dict with 'cfg' key
        wrapper = {
            "name": scenario.get("name", "simulation"),
            "file_suffix": "api_run",
            "cfg": scenario
        }
        
        results = solve_scenario(
            wrapper,
            use_adaptive_mesh=request.use_adaptive_mesh
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Extract metrics
        metrics = SimulationMetrics(
            psi_value=results.get('psi_value'),
            frsi_factor=results.get('frsi_factor'),
            temp_min=results.get('temp_min'),
            temp_max=results.get('temp_max'),
            heat_flux_interior=results.get('flux_int'),
            solver_iterations=results.get('iterations'),
            computation_time_ms=elapsed_ms
        )
        
        # Prepare temperature data for client-side rendering
        temp_data = None
        if 'temp' in results and results['temp'] is not None:
            canvas = scenario.get('canvas', {})
            bounds = canvas.get('bounds', [0, 500, 0, 500])
            canvas_width = bounds[1] - bounds[0]
            canvas_height = bounds[3] - bounds[2]
            temp_data = compress_temperature_data(
                results['temp'], canvas_width, canvas_height
            )
        
        return SimulationResult(
            success=True,
            metrics=metrics,
            temperature_map_url=results.get('temperature_map'),
            geometry_map_url=results.get('geometry_map'),
            mold_risk_map_url=results.get('mold_map') if request.mold_analysis else None,
            temperature_data=temp_data,
            measurements=results.get('measurements', {})
        )
        
    except Exception as e:
        return SimulationResult(
            success=False,
            error=str(e)
        )


@router.post("/optimize", response_model=OptimizationResult)
async def run_optimization(request: OptimizationRequest):
    """Run parameter sweep optimization."""
    from backend.core.batch_simulator import BatchSimulator
    
    try:
        simulator = BatchSimulator(request.scenario)
        
        # Run sweep
        results_df = simulator.run_sweep(
            variable=request.variable,
            start=request.start,
            end=request.end,
            step=request.step
        )
        
        # Convert to response format
        points = []
        for _, row in results_df.iterrows():
            points.append(OptimizationPoint(
                variable_value=row[request.variable],
                psi_value=row.get('psi_value'),
                frsi_factor=row.get('frsi_factor'),
                success=not row.get('error')
            ))
        
        # Find optimal
        valid_points = [p for p in points if p.psi_value is not None]
        if valid_points:
            best = min(valid_points, key=lambda p: p.psi_value)
            optimal_value = best.variable_value
            optimal_psi = best.psi_value
        else:
            optimal_value = None
            optimal_psi = None
        
        return OptimizationResult(
            success=True,
            variable=request.variable,
            points=points,
            optimal_value=optimal_value,
            optimal_psi=optimal_psi
        )
        
    except Exception as e:
        return OptimizationResult(
            success=False,
            variable=request.variable,
            error=str(e)
        )


@router.get("/results/{result_id}")
async def get_result(result_id: str):
    """Get a stored simulation result."""
    # TODO: Implement result storage and retrieval
    raise HTTPException(status_code=501, detail="Result storage not yet implemented")


# --- Async / WebSocket Support ---

from backend.app.models import JobCreatedResponse
from backend.app.jobs import job_manager
import asyncio

async def _run_simulation_task(job_id: str, request: SimulationRequest):
    """
    Background task to run simulation (in thread pool) and push updates.
    """
    from backend.core.simulation_engine import solve_scenario
    
    loop = asyncio.get_running_loop()
    
    # Callback must be thread-safe to schedule async updates on the loop
    def progress_handler(phase, step, total, delta):
        coro = job_manager.set_progress(job_id, phase, step, total)
        asyncio.run_coroutine_threadsafe(coro, loop)
        
    try:
        # Prepare parameters (similar to sync endpoint)
        scenario = request.scenario.copy()
        if request.override_grid_size and request.override_grid_size > 0:
            if 'canvas' in scenario:
                scenario['canvas']['grid'] = request.override_grid_size
        
        start_time = time.time()
        
        # Run blocking solve in thread pool
        # lambda wrapper needed to pass arguments
        def solve_wrapper():
            # Engine expects a wrapper dict with 'cfg' key
            wrapper = {
                "name": scenario.get("name", "simulation"),
                "file_suffix": "api_async",
                "cfg": scenario
            }
            return solve_scenario(
                wrapper,
                use_adaptive_mesh=request.use_adaptive_mesh,
                progress_callback=progress_handler
            )
            
        results = await loop.run_in_executor(None, solve_wrapper)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Extract metrics
        metrics = SimulationMetrics(
            psi_value=results.get('psi_value'),
            frsi_factor=results.get('frsi_factor'),
            temp_min=results.get('temp_min'),
            temp_max=results.get('temp_max'),
            heat_flux_interior=results.get('flux_int'),
            solver_iterations=results.get('iterations'),
            computation_time_ms=elapsed_ms
        )
        
        # Prepare temperature data for client-side rendering
        temp_data = None
        if 'temp' in results and results['temp'] is not None:
            canvas = scenario.get('canvas', {})
            bounds = canvas.get('bounds', [0, 500, 0, 500])
            canvas_width = bounds[1] - bounds[0]
            canvas_height = bounds[3] - bounds[2]
            temp_data = compress_temperature_data(
                results['temp'], canvas_width, canvas_height
            )
        
        final_result = SimulationResult(
            success=True,
            metrics=metrics,
            temperature_map_url=results.get('temperature_map'),
            geometry_map_url=results.get('geometry_map'),
            mold_risk_map_url=results.get('mold_map') if request.mold_analysis else None,
            temperature_data=temp_data,
            measurements=results.get('measurements', {})
        )
        
        await job_manager.set_complete(job_id, final_result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await job_manager.set_error(job_id, str(e))


@router.post("/run-async", response_model=JobCreatedResponse)
async def run_simulation_async(request: SimulationRequest, background_tasks: BackgroundTasks):
    """
    Start simulation job asynchronously. 
    Returns job_id to subscribe via WebSocket /api/ws/simulation/{job_id}.
    """
    job_id = job_manager.create_job()
    
    # Add to background tasks (FastAPI runs these ensuring event loop is not blocked)
    # But since _run_simulation_task manages the thread pool execution, 
    # we can just schedule it as a coroutine.
    background_tasks.add_task(_run_simulation_task, job_id, request)
    
    return JobCreatedResponse(
        job_id=job_id,
        ws_url=f"/api/ws/simulation/{job_id}"
    )
