from unittest.mock import Mock, patch

import numpy as np
import pytest

from guro.core.benchmark import SafeSystemBenchmark
from guro.core.telemetry import Reading


@pytest.fixture
def benchmark():
    with patch('guro.core.benchmark.GPUDetector.get_all_gpus', return_value={'available': False, 'gpus': []}):
        bench = SafeSystemBenchmark()
    bench._thermal = Mock()
    bench._thermal.get_readings.return_value = {'CPU': Reading.temperature(40, 'sensor')}
    return bench


def test_full_cpu_load_does_not_abort(benchmark):
    with patch('psutil.cpu_percent', return_value=100), patch('psutil.virtual_memory', return_value=Mock(percent=30)):
        assert benchmark._check_safety()


@pytest.mark.parametrize('value,source,stops', [(95, 'sensor', True), (95, 'estimate', False), (None, 'sensor', False)])
def test_thermal_stop_requires_real_reading(benchmark, value, source, stops):
    benchmark._thermal.get_readings.return_value = {'CPU': Reading.temperature(value, source)}
    with patch('psutil.virtual_memory', return_value=Mock(percent=30)):
        assert benchmark._check_safety() is not stops
    assert bool(benchmark.stop_reason) is stops


def test_memory_pressure_stops_before_allocation(benchmark):
    with patch('psutil.virtual_memory', return_value=Mock(percent=95, available=1024**3)), patch('numpy.ones') as allocate:
        result = benchmark.safe_memory_test(1)
    assert result['status'] == 'aborted'
    allocate.assert_not_called()


def test_memory_copy_measures_bytes_with_fixed_buffers(benchmark):
    benchmark._tick = Mock(side_effect=[True, True, False])
    with patch('psutil.virtual_memory', return_value=Mock(percent=30, available=1024**3)), patch('numpy.copyto', wraps=np.copyto) as copy:
        result = benchmark.safe_memory_test(10)
    assert copy.call_count == 2
    assert result['buffer_bytes'] <= benchmark.MAX_BUFFER_BYTES
    assert result['bytes_copied'] == result['buffer_bytes']
    assert result['bandwidth_mbps'] > 0


def test_cpu_records_operations(benchmark):
    benchmark._tick = Mock(side_effect=[True, True, False])
    with patch('numpy.dot') as dot:
        result = benchmark.safe_cpu_test(10)
    assert dot.call_count == result['iterations'] == 2
    assert result['gflops'] > 0


def test_gpu_workload_explicitly_unsupported(benchmark):
    result = benchmark.mini_test(gpu_only=True, display=False)
    assert result['status'] == 'unsupported'
    assert result['duration'] < 1
    assert result['gpu']['status'] == 'unsupported'


def test_conflicting_modes_rejected(benchmark):
    with pytest.raises(ValueError):
        benchmark.mini_test(gpu_only=True, cpu_only=True)


@pytest.mark.parametrize('method,duration', [('mini_test', 30), ('god_test', 60)])
def test_run_records_actual_duration_and_configuration(benchmark, method, duration):
    benchmark.safe_cpu_test = Mock(return_value={'gflops': 1})
    benchmark.safe_memory_test = Mock(return_value={'bandwidth_mbps': 1})
    with patch('psutil.virtual_memory', return_value=Mock(percent=30, total=1024**3)):
        result = getattr(benchmark, method)(display=False)
    assert result['requested_duration'] == duration
    assert result['duration'] < 1
    assert result['status'] == 'completed'
    assert result['configuration']['memory_budget_bytes'] == 32 * 1024 * 1024
    assert not benchmark.running


def test_abort_skips_workloads(benchmark):
    benchmark.safe_cpu_test = Mock()
    with patch('psutil.virtual_memory', return_value=Mock(percent=95, total=1024**3)):
        result = benchmark.mini_test(display=False)
    assert result['status'] == 'aborted'
    benchmark.safe_cpu_test.assert_not_called()


def test_cancellation_records_outcome_and_cleans_up(benchmark):
    benchmark.safe_cpu_test = Mock(side_effect=KeyboardInterrupt)
    with patch('psutil.virtual_memory', return_value=Mock(percent=30, total=1024**3)):
        with pytest.raises(KeyboardInterrupt):
            benchmark.mini_test(display=False)
    assert benchmark.results['status'] == 'cancelled'
    assert not benchmark.running
    assert benchmark._live is None


def test_cpu_only_does_not_run_memory(benchmark):
    benchmark.safe_cpu_test = Mock(return_value={'gflops': 1})
    benchmark.safe_memory_test = Mock()
    with patch('psutil.virtual_memory', return_value=Mock(percent=30, total=1024**3)):
        benchmark.mini_test(cpu_only=True, display=False)
    assert benchmark.safe_cpu_test.call_args.args[0] > 29
    benchmark.safe_memory_test.assert_not_called()
