"""
Scenarios API Routes.

Provides endpoints for scenario CRUD operations and validation.
"""

import os
import glob
from typing import List
from fastapi import APIRouter, HTTPException
import yaml

from api.models import (
    ScenarioValidationRequest,
    ValidationResult,
    ValidationError,
    ScenarioSummary,
)
from scenario_schema import Scenario
from ui_validation import validate_scenario_yaml

router = APIRouter()

# Path from api/routes/scenarios.py -> project_root/scenarios
SCENARIOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scenarios")


@router.get("/", response_model=List[ScenarioSummary])
async def list_scenarios():
    """List all available scenarios."""
    scenarios = []
    
    yaml_files = glob.glob(os.path.join(SCENARIOS_DIR, "*.yaml"))
    yaml_files.sort()
    
    for filepath in yaml_files:
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            scenarios.append(ScenarioSummary(
                filename=os.path.basename(filepath),
                name=data.get('name', os.path.basename(filepath)),
                description=data.get('description'),
                element_count=len(data.get('elements', [])),
                has_measurements=bool(data.get('measurements', {}).get('point_probes'))
            ))
        except Exception as e:
            # Skip malformed files
            scenarios.append(ScenarioSummary(
                filename=os.path.basename(filepath),
                name=f"[Error: {e}]",
                element_count=0
            ))
    
    return scenarios


@router.get("/{filename}")
async def get_scenario(filename: str):
    """Get a specific scenario by filename."""
    filepath = os.path.join(SCENARIOS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found")
    
    if not filename.endswith('.yaml'):
        raise HTTPException(status_code=400, detail="Only .yaml files are supported")
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        data = yaml.safe_load(content)
        return {
            "filename": filename,
            "yaml_content": content,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read scenario: {e}")


@router.post("/validate", response_model=ValidationResult)
async def validate_scenario(request: ScenarioValidationRequest):
    """Validate a scenario definition."""
    try:
        content = request.get_content()
    except ValueError as e:
        return ValidationResult(
            is_valid=False,
            errors=[ValidationError(field="request", message=str(e))]
        )
    except yaml.YAMLError as e:
        return ValidationResult(
            is_valid=False,
            errors=[ValidationError(field="yaml", message=f"YAML parse error: {e}")]
        )
    
    # Use existing UI validation logic
    yaml_str = request.yaml_content or yaml.dump(content)
    result = validate_scenario_yaml(yaml_str)
    
    errors = [
        ValidationError(
            field=" -> ".join(str(l) for l in err.loc) if err.loc else "scenario",
            message=err.message,
            line=err.line
        )
        for err in result.errors
    ]
    
    return ValidationResult(
        is_valid=result.is_valid,
        errors=errors,
        scenario_name=content.get('name') if result.is_valid else None
    )


@router.post("/")
async def create_scenario(scenario: dict, filename: str):
    """Save a new scenario."""
    if not filename.endswith('.yaml'):
        filename = f"{filename}.yaml"
    
    filepath = os.path.join(SCENARIOS_DIR, filename)
    
    if os.path.exists(filepath):
        raise HTTPException(status_code=409, detail=f"Scenario '{filename}' already exists")
    
    # Validate first
    try:
        Scenario(**scenario)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {e}")
    
    try:
        with open(filepath, 'w') as f:
            yaml.dump(scenario, f, default_flow_style=False, sort_keys=False)
        return {"message": f"Scenario saved as {filename}", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save scenario: {e}")


@router.put("/{filename}")
async def update_scenario(filename: str, scenario: dict):
    """Update an existing scenario."""
    filepath = os.path.join(SCENARIOS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found")
    
    # Validate
    try:
        Scenario(**scenario)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {e}")
    
    try:
        with open(filepath, 'w') as f:
            yaml.dump(scenario, f, default_flow_style=False, sort_keys=False)
        return {"message": f"Scenario '{filename}' updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update scenario: {e}")


@router.delete("/{filename}")
async def delete_scenario(filename: str):
    """Delete a scenario."""
    filepath = os.path.join(SCENARIOS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found")
    
    # Protect important files
    protected = ['iso_case_1.yaml', 'iso_case_2.yaml']
    if filename in protected:
        raise HTTPException(status_code=403, detail="Cannot delete protected ISO test cases")
    
    try:
        os.remove(filepath)
        return {"message": f"Scenario '{filename}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scenario: {e}")
