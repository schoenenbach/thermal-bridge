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

import pytest
from backend.core.declarative_geometry import DeclarativeGeometry

def test_variable_substitution_simple():
    yaml_content = {
        'name': 'Test Simple',
        'canvas': {'bounds': [0, 100, 0, 100], 'grid': 10},
        'variables': {
            'width': 50.0,
            'height': 60.0,
            'name_suffix': 'Test'
        },
        'elements': [
            {
                'type': 'rect',
                'params': {
                    'width': '${width}',
                    'height': '${height}',
                    'name': 'Rect_${name_suffix}'
                }
            }
        ]
    }
    geom = DeclarativeGeometry(yaml_content)
    # Access private data to check resolution (or mock elements)
    # Elements are built into sketch, let's check sketch objects if possible, 
    # but DeclarativeGeometry doesn't easily expose the raw element params after build.
    # However, self.data should be updated.
    
    assert geom.data['elements'][0]['params']['width'] == 50.0
    assert geom.data['elements'][0]['params']['height'] == 60.0
    assert geom.data['elements'][0]['params']['name'] == 'Rect_Test'

def test_variable_dependency():
    yaml_content = {
        'name': 'Test Dependency',
        'canvas': {'bounds': [0, 100, 0, 100], 'grid': 10},
        'variables': {
            'base': 10.0,
            'derived': '${base} + 5.0',
            'chained': '${derived} * 2'
        },
        'elements': []
    }
    geom = DeclarativeGeometry(yaml_content)
    vars_ = geom.data['variables']
    
    assert vars_['base'] == 10.0
    assert vars_['derived'] == 15.0
    assert vars_['chained'] == 30.0

def test_math_expressions():
    yaml_content = {
        'name': 'Test Math',
        'canvas': {'bounds': [0, 100, 0, 100], 'grid': 10},
        'variables': {
            'a': 10,
            'b': 20,
            'sum': '${a} + ${b}',
            'complex': '(${a} * 2) + (${b} / 2)'
        },
        'elements': []
    }
    geom = DeclarativeGeometry(yaml_content)
    vars_ = geom.data['variables']
    
    assert vars_['sum'] == 30
    assert vars_['complex'] == 30.0

def test_variable_in_list():
    yaml_content = {
        'name': 'Test List',
        'canvas': {'bounds': [0, 100, 0, 100], 'grid': 10},
        'variables': {
            'coord': 5.5
        },
        'points': {
            'p1': ['${coord}', 0.0]
        },
        'elements': []
    }
    geom = DeclarativeGeometry(yaml_content)
    # Check points are resolved
    # DeclarativeGeometry defines points into the geometry, we can check that.
    # But self.data should also be updated.
    assert geom.data['points']['p1'][0] == 5.5

def test_missing_variable():
    # Should warn but not crash, keeping original string
    yaml_content = {
        'name': 'Test Missing',
        'canvas': {'bounds': [0, 100, 0, 100], 'grid': 10},
        'variables': {},
        'elements': [{'type': 'rect', 'params': {'x': '${missing}'}}]
    }
    geom = DeclarativeGeometry(yaml_content)
    assert geom.data['elements'][0]['params']['x'] == '${missing}'

def test_circular_dependency_safety():
    # Should handle gracefully (e.g. by hitting max iterations)
    yaml_content = {
        'name': 'Test Circular',
        'canvas': {'bounds': [0, 100, 0, 100], 'grid': 10},
        'variables': {
            'a': '${b}',
            'b': '${a}'
        },
        'elements': []
    }
    geom = DeclarativeGeometry(yaml_content)
    # They will likely remain as strings or whatever implementation does
    # as long as it doesn't infinite loop.
    assert isinstance(geom.data['variables']['a'], str)
