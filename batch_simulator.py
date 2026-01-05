import copy
import multiprocessing
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from simulation_engine import solve_scenario

def get_nested_value(data: Dict[str, Any], path: str, sep: str = '.') -> Any:
    """Get value from nested dictionary using dot notation path."""
    keys = path.split(sep)
    val = data
    for key in keys:
        if isinstance(val, list):
            try:
                key = int(key)
            except ValueError:
                raise ValueError(f"Cannot access list with non-integer key: {key}")
        if isinstance(val, (dict, list)):
            try:
                val = val[key]
            except (KeyError, IndexError):
                 raise KeyError(f"Key '{key}' not found in path '{path}'")
        else:
             raise KeyError(f"Cannot traverse deeper at '{key}' in path '{path}'")
    return val

def set_nested_value(data: Dict[str, Any], path: str, value: Any, sep: str = '.') -> None:
    """Set value in nested dictionary using dot notation path."""
    keys = path.split(sep)
    ref = data
    for i, key in enumerate(keys[:-1]):
        if isinstance(ref, list):
            try:
                key = int(key)
            except ValueError:
                raise ValueError(f"Cannot access list with non-integer key: {key}")
        
        if isinstance(ref, (dict, list)):
             ref = ref[key]
        else:
             raise KeyError(f"Cannot traverse deeper at '{key}' in path '{path}'")
            
    last_key = keys[-1]
    if isinstance(ref, list):
        try:
            last_key = int(last_key)
        except ValueError:
             raise ValueError(f"Cannot access list with non-integer key: {last_key}")
    ref[last_key] = value

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary efficiently, handling lists as indices."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
             for i, item in enumerate(v):
                 list_key = f"{new_key}{sep}{i}"
                 if isinstance(item, (dict, list)):
                     items.extend(flatten_dict(item, list_key, sep=sep).items())
                 else:
                     items.append((list_key, item))
        else:
            items.append((new_key, v))
    return dict(items)

def _worker_run_scenario(args: Tuple[Dict[str, Any], str, float]) -> Dict[str, Any]:
    """Worker function to run a single simulation."""
    config, param_path, value = args
    
    # Update configuration
    try:
        updated_config = copy.deepcopy(config)
        set_nested_value(updated_config, param_path, value)
    except Exception as e:
        return {"value": value, "error": f"Failed to update config: {e}"}

    # Run simulation
    try:
        # Wrap config in scenario definition
        scenario_def = {
            "name": f"Sweep_{param_path}_{value}",
            "file_suffix": "sweep",
            "cfg": updated_config
        }
        
        # We suppress print output or handle it? 
        # Ideally, we should capture stdout/stderr to avoid spam, but multiprocessing handles this loosely.
        
        # solve_scenario returns dict with 'measurements'
        results_full = solve_scenario(scenario_def, use_adaptive_mesh=True)
        
        # Extract Psi
        psi_value = None
        measurements = results_full.get("measurements", {})
        if "Psi" in measurements:
            psi_value = measurements["Psi"].get("value")
        # Fallback to looking for "psi_value" derived
        elif "psi_value" in measurements:
            psi_value = measurements["psi_value"].get("value")
            
        frsi_value = None
        if "fRsi" in measurements:
            frsi_value = measurements["fRsi"].get("value")

        return {
            "value": value,
            "psi_value": psi_value,
            "fRsi": frsi_value,
            "error": None
        }
    except Exception as e:
        return {"value": value, "error": str(e)}

class BatchSimulator:
    def __init__(self, base_config: Dict[str, Any]):
        self.base_config = base_config

    def get_optimizable_parameters(self) -> Dict[str, Any]:
        """Return a flat dictionary of parameters that can be optimized."""
        # We filter for only numeric types (int, float) as they are sweepable
        flat = flatten_dict(self.base_config)
        return {k: v for k, v in flat.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}

    def run_sweep(self, param_path: str, start: float, end: float, step: float) -> pd.DataFrame:
        """Run a parameter sweep."""
        
        # Generated values
        try:
             # Ensure step is positive and loop makes sense
             if step <= 0: raise ValueError("Step must be positive")
             if start > end: start, end = end, start
             
             values = np.arange(start, end + step, step)
             # Filter to not exceed end significantly due to float errors
             values = values[values <= end + 1e-9]
        except Exception as e:
             raise ValueError(f"Invalid range generation: {e}")

        # Prepare tasks
        tasks = [(self.base_config, param_path, val) for val in values]
        
        # Run in parallel
        cpu_count = max(1, multiprocessing.cpu_count() - 1)
        
        results = []
        with multiprocessing.Pool(processes=cpu_count) as pool:
             results = pool.map(_worker_run_scenario, tasks)
             
        # Aggregate
        df = pd.DataFrame(results)
        return df
