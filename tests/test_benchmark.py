import pytest
from unittest.mock import Mock, patch
import numpy as np
import psutil
import platform
from rich.console import Console
from rich.table import Table

# Import the class to test
from guro.core.benchmark import SafeSystemBenchmark

@pytest.fixture
def benchmark():
    """Fixture to create a fresh benchmark instance for each test"""
    return SafeSystemBenchmark()

def test_initialization(benchmark):
    """Test proper initialization of benchmark instance"""
    assert isinstance(benchmark.console, Console)
    assert isinstance(benchmark.results, dict)
    assert not benchmark.running
    assert benchmark.MAX_CPU_USAGE <= 100
    assert benchmark.MAX_MEMORY_USAGE <= 100

@patch('GPUtil.getGPUs')
def test_check_gpu_with_gpu(mock_getGPUs, benchmark):
    """Test GPU detection when GPU is available"""
    mock_gpu = Mock()
    mock_gpu.name = "Test GPU"
    mock_gpu.memoryTotal = 8192
    mock_gpu.driver = "123.45"
    mock_getGPUs.return_value = [mock_gpu]
    
    gpu_info = benchmark._check_gpu()
    assert gpu_info['available']
    assert gpu_info['info']['name'] == "Test GPU"
    assert gpu_info['info']['count'] == 1

@patch('GPUtil.getGPUs')
def test_check_gpu_without_gpu(mock_getGPUs, benchmark):
    """Test GPU detection when no GPU is available"""
    mock_getGPUs.return_value = []
    
    gpu_info = benchmark._check_gpu()
    assert not gpu_info['available']
    assert gpu_info['info'] is None

def test_get_system_info(benchmark):
    """Test system information gathering"""
    system_info = benchmark.get_system_info()
    
    assert system_info['system'] == platform.system()
    assert system_info['processor'] == platform.processor()
    assert system_info['cpu_cores'] == psutil.cpu_count(logical=False)
    assert system_info['cpu_threads'] == psutil.cpu_count(logical=True)
    assert isinstance(system_info['gpu'], dict)

@patch('time.sleep', return_value=None)
def test_safe_cpu_test(mock_sleep, benchmark):
    """Test CPU benchmark functionality"""
    duration = 1
    result = benchmark.safe_cpu_test(duration)
    
    assert 'times' in result
    assert 'loads' in result
    assert isinstance(result['times'], list)
    assert isinstance(result['loads'], list)

@patch('time.sleep', return_value=None)
def test_safe_memory_test(mock_sleep, benchmark):
    """Test memory benchmark functionality"""
    duration = 1
    result = benchmark.safe_memory_test(duration)
    
    assert 'times' in result
    assert 'usage' in result
    assert isinstance(result['times'], list)
    assert isinstance(result['usage'], list)

@patch('GPUtil.getGPUs')
@patch('time.sleep', return_value=None)
def test_safe_gpu_test_with_gpu(mock_sleep, mock_getGPUs, benchmark):
    """Test GPU benchmark when GPU is available"""
    mock_gpu = Mock()
    mock_gpu.load = 0.5
    mock_gpu.memoryUsed = 4096
    mock_getGPUs.return_value = [mock_gpu]
    
    benchmark.has_gpu['available'] = True
    duration = 1
    result = benchmark.safe_gpu_test(duration)
    
    assert 'times' in result
    assert 'loads' in result
    assert 'memory_usage' in result
    assert isinstance(result['times'], list)
    assert isinstance(result['loads'], list)
    assert isinstance(result['memory_usage'], list)

def test_safe_gpu_test_without_gpu(benchmark):
    """Test GPU benchmark when no GPU is available"""
    benchmark.has_gpu['available'] = False
    duration = 1
    result = benchmark.safe_gpu_test(duration)
    
    assert 'error' in result
    assert result['error'] == 'No GPU available'

def test_generate_status_table(benchmark):
    """Test status table generation"""
    table = benchmark.generate_status_table()
    
    assert isinstance(table, Table)
    assert table.title == "Benchmark Status"

@patch('psutil.cpu_percent')
@patch('psutil.virtual_memory')
def test_monitor_resources_safety_threshold(mock_memory, mock_cpu, benchmark):
    """Test resource monitoring safety thresholds"""
    mock_cpu.return_value = 90  # Above MAX_CPU_USAGE
    mock_memory_obj = Mock()
    mock_memory_obj.percent = 60
    mock_memory.return_value = mock_memory_obj
    
    benchmark.running = True
    benchmark.monitor_resources()
    
    assert not benchmark.running

@patch('rich.live.Live')
def test_mini_test(mock_live, benchmark):
    """Test mini benchmark execution"""
    benchmark.mini_test()
    assert 'system_info' in benchmark.results
    assert benchmark.results['duration'] == 30

@patch('rich.live.Live')
def test_god_test(mock_live, benchmark):
    """Test god-level benchmark execution"""
    benchmark.god_test()
    assert 'system_info' in benchmark.results
    assert benchmark.results['duration'] == 60