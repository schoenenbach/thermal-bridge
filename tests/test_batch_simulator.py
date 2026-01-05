import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from batch_simulator import BatchSimulator, get_nested_value, set_nested_value, flatten_dict

class TestDictHelpers:
    def test_get_nested_value(self):
        data = {'a': 1, 'b': {'c': 2, 'd': [3, 4]}}
        assert get_nested_value(data, 'a') == 1
        assert get_nested_value(data, 'b.c') == 2
        assert get_nested_value(data, 'b.d.0') == 3
        # assert get_nested_value(data, 'b.d.1') == 4

    def test_set_nested_value(self):
        data = {'a': 1, 'b': {'c': 2, 'd': [3, 4]}}
        set_nested_value(data, 'a', 10)
        assert data['a'] == 10
        set_nested_value(data, 'b.c', 20)
        assert data['b']['c'] == 20
        set_nested_value(data, 'b.d.1', 40)
        assert data['b']['d'][1] == 40

    def test_flatten_dict(self):
        data = {'a': 1, 'b': {'c': 2}}
        flat = flatten_dict(data)
        assert flat['a'] == 1
        assert flat['b.c'] == 2

class TestBatchSimulator:
    @pytest.fixture
    def sample_config(self):
        return {
            'layer': {'thickness': 0.1},
            'other': 5
        }

    @patch('batch_simulator.solve_scenario')
    @patch('batch_simulator.multiprocessing.Pool')
    def test_run_sweep(self, mock_pool, mock_solve, sample_config):
        # Mock pool
        pool_instance = MagicMock()
        mock_pool.return_value.__enter__.return_value = pool_instance
        def side_effect_map(func, iterable):
            return [func(item) for item in iterable]
        pool_instance.map.side_effect = side_effect_map

        # Mock solve_scenario
        mock_solve.return_value = {
            "name": "test",
            "measurements": {
                "Psi": {"value": 0.5},
                "fRsi": {"value": 0.7}
            }
        }

        sim = BatchSimulator(sample_config)
        df = sim.run_sweep('layer.thickness', 0.1, 0.3, 0.1)
        
        assert len(df) == 3
        assert df.iloc[0]['psi_value'] == 0.5
        assert df.iloc[0]['value'] == pytest.approx(0.1)
