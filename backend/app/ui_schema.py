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
UI Hints for dynamic form generation.

This module provides metadata to guide frontend applications in rendering
forms based on the JSON Schema. It defines widget types, field grouping,
ordering, and other UI-specific properties that are not part of the standard
JSON Schema.
"""

# UI Hints keyed by schema property path (dot notation)
UI_HINTS = {
    # Canvas Settings
    "canvas": {
        "group": "Canvas Configuration",
        "order": 1,
        "expanded": True
    },
    "canvas.bounds": {
        "widget": "bounds_editor",
        "label": "Canvas Bounds (mm)",
        "description": "Define the simulation area [x_min, x_max, y_min, y_max]",
        "order": 1
    },
    "canvas.grid": {
        "widget": "slider",
        "label": "Grid Size (mm)",
        "min": 1,
        "max": 50,
        "step": 0.5,
        "unit": "mm",
        "order": 2
    },

    # Material Definitions
    "materials": {
        "group": "Materials",
        "order": 2,
        "widget": "material_list",
        "item_label": "{name}"
    },
    
    # Boundary Conditions
    "boundary_conditions": {
        "group": "Boundary Conditions",
        "order": 3
    },
    "boundary_conditions.dirichlet": {
        "widget": "key_value_pairs",
        "key_label": "Boundary Name",
        "value_label": "Temperature (°C)",
        "value_type": "number"
    },
    "boundary_conditions.convective": {
        "widget": "convective_bc_editor",
        "description": "Define heat transfer coefficient and ambient temperature per boundary"
    },
    
    # Simulation Settings
    "transient": {
        "group": "Transient Simulation",
        "order": 4,
        "dependency": "enabled"  # Only show if enabled is true
    },
    "transient.duration_hours": {
        "widget": "slider",
        "min": 1,
        "max": 72,
        "step": 1,
        "unit": "h"
    },
    "transient.dt_seconds": {
        "widget": "select",
        "options": [60, 300, 600, 1800, 3600],
        "labels": ["1 min", "5 min", "10 min", "30 min", "1 hour"]
    },

    # Geometry Elements
    "elements": {
        "group": "Geometry",
        "order": 5,
        "widget": "element_list",
        "polymorphic_key": "type"  # Field that determines the sub-schema/widget
    }
}

def get_element_hints(element_type: str) -> dict:
    """Get UI hints specific to an element type."""
    
    common_hints = {
        "material": {"widget": "material_select"},
        "color": {"widget": "color_picker"}
    }
    
    specific_hints = {
        "rect": {
            "x": {"step": 1, "unit": "mm"},
            "y": {"step": 1, "unit": "mm"},
            "width": {"min": 1, "unit": "mm"},
            "height": {"min": 1, "unit": "mm"}
        },
        "wall": {
            "thickness": {"min": 10, "unit": "mm"},
            "depth": {"min": 10, "unit": "mm"}
        },
        "window_framework": {
            "frame_width": {"min": 10, "unit": "mm"},
            "frame_depth": {"min": 10, "unit": "mm"}
        }
    }
    
    hints = common_hints.copy()
    if element_type in specific_hints:
        hints.update(specific_hints[element_type])
        
    return hints
