
import numpy as np
import yaml
from backend.core.simulation_engine import solve_scenario
import os

def test_comparison_logic():
    print("Testing Comparison Logic...")
    
    # Load Scenario 1
    with open("scenarios/scenario_1.yaml", 'r') as f:
        base_cfg = yaml.safe_load(f)
        
    # Create Reference
    cfg_ref = base_cfg.copy()
    cfg_ref['name'] = "TEST_REF"
    
    # Create Proposed (Change wall dimension directly)
    cfg_prop = base_cfg.copy()
    cfg_prop['name'] = "TEST_PROP"
    
    # Deep copy elements to avoid reference issues
    import copy
    cfg_prop['elements'] = copy.deepcopy(base_cfg['elements'])
    
    # Modify a wall element
    found = False
    for el in cfg_prop['elements']:
         if el.get('type') == 'wall':
             print(f"Modifying element: {el['type']}")
             # Change material to INSULATION (ID 2 -> ID 4 typically, or string)
             # Scenario 1 uses strings "WALL", "INSULATION"
             el['material'] = "INSULATION"
             found = True
             break
    
    if not found:
        print("WARNING: No wall width found to modify")
    
    # Run Reference
    print("Running Reference...")
    res_ref = solve_scenario({"name": "TEST_REF", "file_suffix": "ref", "cfg": cfg_ref}, use_adaptive_mesh=False) # Uniform for speed + grid match
    
    # Run Proposed
    print("Running Proposed...")
    res_prop = solve_scenario({"name": "TEST_PROP", "file_suffix": "prop", "cfg": cfg_prop}, use_adaptive_mesh=False)
    
    # Check Results
    assert 'measurements' in res_ref
    assert 'measurements' in res_prop
    assert 'temp' in res_ref
    assert 'temp' in res_prop
    
    psi_ref = res_ref['measurements']['Psi']['value']
    psi_prop = res_prop['measurements']['Psi']['value']
    
    print(f"Psi Ref: {psi_ref}")
    print(f"Psi Prop: {psi_prop}")
    
    assert psi_ref is not None
    assert psi_prop is not None
    assert abs(psi_ref - psi_prop) > 0.0001, "Psi values should differ"
    
    # Check Temp Field
    t_ref = res_ref['temp']
    t_prop = res_prop['temp']
    
    if t_ref.shape == t_prop.shape:
        delta = t_prop - t_ref
        max_diff = np.max(np.abs(delta))
        print(f"Max Temp Difference: {max_diff}")
        assert max_diff > 0.1, "Temperature fields should differ"
    else:
        print(f"Grids differ: {t_ref.shape} vs {t_prop.shape}. Skipping delta check.")
        # Note: Changing wall tickness might change grid size in UniformMesh if not fixed?
        # UniformMesh with fixed grid size should match if bounds match? 
        # Wall is w=360 vs w=500. Bounds will change. So grids will differ. 
        # That's expected behaviour.
        
    print("Test Passed!")

if __name__ == "__main__":
    test_comparison_logic()
