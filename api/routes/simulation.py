"""
Simulation API Routes.

Provides endpoints for running simulations and parameter sweeps.
"""

import os
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks

from api.models import (
    SimulationRequest,
    SimulationResult,
    SimulationMetrics,
    OptimizationRequest,
    OptimizationResult,
    OptimizationPoint,
)

router = APIRouter()

# Results storage directory
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


@router.post("/run", response_model=SimulationResult)
async def run_simulation(request: SimulationRequest):
    """Run a thermal bridge simulation."""
    from simulation_engine import solve_scenario
    
    start_time = time.time()
    
    try:
        # Apply grid override if specified
        scenario = request.scenario.copy()
        if request.override_grid_size and request.override_grid_size > 0:
            if 'canvas' in scenario:
                scenario['canvas']['grid'] = request.override_grid_size
        
        # Run simulation
        results = solve_scenario(
            scenario,
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
        
        return SimulationResult(
            success=True,
            metrics=metrics,
            temperature_map_url=results.get('temperature_map'),
            geometry_map_url=results.get('geometry_map'),
            mold_risk_map_url=results.get('mold_map') if request.mold_analysis else None,
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
    from batch_simulator import BatchSimulator
    
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
