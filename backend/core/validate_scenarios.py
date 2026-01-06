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
Schema Validation Helper

Analyzes all scenario YAML files to understand:
1. What element types are used
2. What params each element type uses
3. What issues exist (missing params, typos, etc.)

Usage:
    python validate_scenarios.py
"""

import yaml
import glob
import os
from collections import defaultdict
from typing import Dict, List, Any, Set


def analyze_scenarios():
    """Analyze all scenario YAML files for element usage patterns."""
    
    scenario_files = glob.glob("scenarios/*.yaml")
    
    # Track element types and their params
    element_types: Dict[str, Dict[str, Set]] = defaultdict(lambda: {
        'param_keys': set(),
        'top_level_keys': set(),
        'files': set(),
        'count': 0
    })
    
    issues: List[Dict] = []
    
    for fpath in sorted(scenario_files):
        fname = os.path.basename(fpath)
        
        try:
            with open(fpath, 'r') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            issues.append({'file': fname, 'error': f"YAML parse error: {e}"})
            continue
            
        if not data:
            continue
            
        elements = data.get('elements', [])
        
        for i, el in enumerate(elements):
            if not isinstance(el, dict):
                issues.append({'file': fname, 'element': i, 'error': "Element is not a dict"})
                continue
                
            el_type = el.get('type')
            if not el_type:
                issues.append({'file': fname, 'element': i, 'error': "Missing 'type' field"})
                continue
            
            # Track this element type
            info = element_types[el_type]
            info['files'].add(fname)
            info['count'] += 1
            
            # Track top-level keys (excluding common ones)
            for key in el.keys():
                if key not in ['type', 'name', 'material', 'params', 'lambda', 'points']:
                    info['top_level_keys'].add(key)
            
            # Track param keys
            params = el.get('params', {})
            if isinstance(params, dict):
                for key in params.keys():
                    info['param_keys'].add(key)
    
    return element_types, issues, scenario_files


def print_report(element_types, issues, files):
    """Print analysis report."""
    
    print("=" * 70)
    print("SCENARIO SCHEMA VALIDATION REPORT")
    print("=" * 70)
    print(f"\nAnalyzed {len(files)} scenario files\n")
    
    # Element Types Summary
    print("-" * 70)
    print("ELEMENT TYPES FOUND")
    print("-" * 70)
    
    for el_type in sorted(element_types.keys()):
        info = element_types[el_type]
        print(f"\n### {el_type.upper()} ({info['count']} occurrences)")
        print(f"    Files: {', '.join(sorted(info['files']))}")
        
        if info['param_keys']:
            print(f"    params.* keys: {sorted(info['param_keys'])}")
        
        if info['top_level_keys']:
            print(f"    top-level keys: {sorted(info['top_level_keys'])}")
    
    # Recommended Pydantic Schema
    print("\n" + "=" * 70)
    print("RECOMMENDED PYDANTIC SCHEMAS")
    print("=" * 70)
    
    for el_type in sorted(element_types.keys()):
        info = element_types[el_type]
        class_name = ''.join(word.title() for word in el_type.split('_')) + 'Element'
        params_class = ''.join(word.title() for word in el_type.split('_')) + 'Params'
        
        print(f"\nclass {params_class}(BaseModel):")
        for key in sorted(info['param_keys']):
            print(f"    {key}: float")
        if not info['param_keys']:
            print("    pass")
        
        print(f"\nclass {class_name}(ElementBase):")
        print(f"    type: Literal['{el_type}']")
        print(f"    params: {params_class} = Field(default_factory={params_class})")
    
    # Issues
    if issues:
        print("\n" + "=" * 70)
        print("ISSUES FOUND")
        print("=" * 70)
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✓ No issues found")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    element_types, issues, files = analyze_scenarios()
    print_report(element_types, issues, files)
