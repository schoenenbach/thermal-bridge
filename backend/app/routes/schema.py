"""
Schema API Routes.

Provides endpoints to retrieve the JSON Schema for scenarios,
elements, and materials, optionally enriched with UI hints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Query
from pydantic.json_schema import GenerateJsonSchema

from backend.core.scenario_schema import Scenario
from backend.app.ui_schema import UI_HINTS, get_element_hints

router = APIRouter()


@router.get("/scenario", response_model=Dict[str, Any])
async def get_scenario_schema(
    ui_hints: bool = Query(False, description="Include UI rendering hints")
):
    """
    Get the full JSON Schema for validation and form generation.
    
    Args:
        ui_hints: If true, injects 'x-ui-hints' into the schema properties.
    """
    # Generate fresh schema from Pydantic models
    schema = Scenario.model_json_schema()
    
    # Match title from backend.core.schema_export.py
    schema["title"] = "Thermal Bridge Scenario"
    
    if ui_hints:
        defs = schema.get("$defs", {})
        _inject_ui_hints(schema, UI_HINTS, definitions=defs)
        
    return schema


@router.get("/elements", response_model=Dict[str, Any])
async def get_element_schemas():
    """
    Get schemas specifically for element types (walls, windows, etc.).
    Useful for populating a 'Add Element' palette.
    """
    # Generate full schema to resolve refs
    full_schema = Scenario.model_json_schema()
    defs = full_schema.get("$defs", {})
    
    return {
        "definitions": defs,
        "hints": {
            "rect": get_element_hints("rect"),
            "wall": get_element_hints("wall"),
            "window_framework": get_element_hints("window_framework")
        }
    }


def _inject_ui_hints(
    schema: Dict[str, Any], 
    hints: Dict[str, Any], 
    prefix: str = "", 
    definitions: Optional[Dict[str, Any]] = None,
    visited_refs: Optional[set] = None
):
    """
    Recursively inject UI hints into the schema as 'x-ui-hints'.
    Follows $ref links to inject hints into definitions.
    
    Args:
        schema: The JSON schema dictionary (mutated in place)
        hints: The dictionary of hints
        prefix: Current property path (e.g. 'canvas.bounds')
        definitions: The global $defs dictionary for resolving refs
        visited_refs: Set of visited $ref strings to prevent infinite recursion
    """
    if visited_refs is None:
        visited_refs = set()

    # handle $ref
    if "$ref" in schema and definitions is not None:
        ref_name = schema["$ref"].split("/")[-1]
        
        # Determine if we should traverse this ref
        # We only traverse if there are hints that start with the current prefix
        # This prevents exploring the whole graph if unnecessary
        relevant_hints = any(k.startswith(prefix + ".") or k == prefix for k in hints.keys())
        
        if relevant_hints and ref_name not in visited_refs:
            visited_refs.add(ref_name)
            if ref_name in definitions:
                 _inject_ui_hints(definitions[ref_name], hints, prefix, definitions, visited_refs)
            visited_refs.remove(ref_name) # Allow re-visiting in different context if needed, though strictly we are mutating the def which is shared.
            # actually, if we mutate the def, it persists. 
            # We don't effectively distinguish paths for shared defs here. 
            # This is a limitation: canvas.bounds and other.bounds would share hints if they share type.
            # For this app, it's acceptable.

    properties = schema.get("properties", {})
    
    for prop_name, prop_schema in properties.items():
        path = f"{prefix}.{prop_name}" if prefix else prop_name
        
        # Check if we have a hint for this specific path
        if path in hints:
            if "x-ui-hints" not in prop_schema:
                prop_schema["x-ui-hints"] = {}
            prop_schema["x-ui-hints"].update(hints[path])
            
        # Recursive descent
        _inject_ui_hints(prop_schema, hints, prefix=path, definitions=definitions, visited_refs=visited_refs)

