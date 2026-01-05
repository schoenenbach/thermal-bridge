
"""
UI Validation Module for Thermal Bridge Simulation

Provides real-time schema validation helpers for the Streamlit editor.
Wraps Pydantic validation to provide user-friendly error messages with line numbers.
"""

import yaml
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from backend.core.scenario_schema import Scenario, RectParams, WallParams, AirParams

@dataclass
class ValidationErrorInfo:
    """Structured validation error with line number specific to the UI."""
    line: int
    message: str
    loc: List[Union[str, int]]

@dataclass
class ValidationResult:
    """Result of a validation attempt."""
    is_valid: bool
    data: Optional[Dict[str, Any]]
    errors: List[ValidationErrorInfo]
    warnings: List[str]

def _find_line_for_path(yaml_content: str, loc: List[Union[str, int]]) -> int:
    """
    Attempt to find the approximate line number for a specific path in the YAML.
    This is a heuristic approach since standard yaml parsers don't map value locations easily.
    """
    if not loc:
        return 1
        
    lines = yaml_content.split('\n')
    current_line = 0
    current_depth = 0
    
    # Very simple heuristic: search for keys sequentially
    # This acts as a fallback "best guess"
    # A true line mapper requires a CST parser (like ruamel.yaml) but we want to stick to std deps if possible.
    # If key uniqueness is an issue, this might point to the first occurrence.
    
    # Just return 1 for now if complex. 
    # Improvement: use ruamel.yaml if available, or simple text search for context.
    
    target_key = str(loc[-1])
    
    for i, line in enumerate(lines):
        if target_key in line:
            # Check if it looks like a key
            if f"{target_key}:" in line or f"- {target_key}" in line:
                return i + 1
                
    return 1

def validate_scenario_yaml(yaml_content: str) -> ValidationResult:
    """
    Parse YAML content and validate it against the Scenario schema.
    Returns structured result with line numbers.
    """
    if not yaml_content.strip():
        return ValidationResult(False, None, [ValidationErrorInfo(1, "Empty content", [])], [])

    try:
        # 1. Parse YAML
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        # Handle YAML syntax errors
        line = 1
        if hasattr(e, 'problem_mark'):
            line = e.problem_mark.line + 1
        return ValidationResult(False, None, [ValidationErrorInfo(line, f"YAML Syntax Error: {e}", [])], [])
    except Exception as e:
        return ValidationResult(False, None, [ValidationErrorInfo(1, f"Parse Error: {e}", [])], [])

    if not isinstance(data, dict):
         return ValidationResult(False, None, [ValidationErrorInfo(1, "Root must be a dictionary/object", [])], [])

    # 2. Validate with Pydantic
    try:
        scenario = Scenario(**data)
        # Re-export data to ensure we have the clean model data (with defaults)
        # But for the editor, we usually want to keep the raw dict if valid
        return ValidationResult(True, data, [], [])
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = err['loc']
            msg = err['msg']
            
            # Map location to line number
            # Using a simplified finder for now
            line = _find_line_for_path(yaml_content, loc)
            
            # Formatted message
            path_str = " -> ".join(str(l) for l in loc)
            full_msg = f"{path_str}: {msg}" if path_str else msg
            
            errors.append(ValidationErrorInfo(line, full_msg, loc))
            
        return ValidationResult(False, data, errors, [])

def get_element_hints(element_type: str) -> List[str]:
    """
    Return list of required parameters for a given element type.
    """
    # Mapping for common types
    # In a full implementation, this could verify against Pydantic fields
    hints = {
        "rect": ["x", "y", "width", "height"],
        "wall": ["x", "y", "width", "height"],
        "air": ["x", "y", "width", "height", "type ('int' or 'ext')"],
        "insulation_tapered": ["x_base", "y_bottom", "y_top", "thick_main", "thick_taper"],
        "window_detail": ["x_frame_start", "y_frame_start", "frame_depth", "glass_thickness"],
        "polygon": ["points (list of names)"]
    }
    return hints.get(element_type, [])
