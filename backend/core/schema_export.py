"""
Export JSON Schema from Pydantic models for IDE integration.

Usage:
    python schema_export.py

This generates scenario.schema.json which can be used by:
- VS Code YAML extension for autocomplete and validation
- External tools and documentation
- API contract validation
"""

import json
from backend.core.scenario_schema import Scenario


def export_schema(output_path: str = "scenario.schema.json"):
    """Export JSON Schema from Pydantic Scenario model."""
    schema = Scenario.model_json_schema()
    
    # Add $schema reference for tooling
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    
    # Add title and description
    schema["title"] = "Thermal Bridge Scenario"
    schema["description"] = "Configuration schema for thermal bridge simulations. Defines geometry, materials, boundary conditions, and measurement specifications."
    
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    
    print(f"✓ Exported schema to {output_path}")
    print(f"  - {len(schema.get('$defs', {}))} definitions")
    print(f"  - {len(schema.get('properties', {}))} top-level properties")
    
    return schema


if __name__ == "__main__":
    export_schema()
