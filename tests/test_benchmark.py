import pytest
from unittest.mock import Mock, patch
import numpy as np
import psutil
import platform
from rich.console import Console
from rich.table import Table
import sys

# Create a mock GPUtil module
mock_GPUtil = Mock()
mock_GPUtil.getGPUs = Mock()

@pytest.fixture(autouse=True)
def mock_gputil():
    """Fixture to mock GPUtil for all tests"""
    with patch.dict('sys.modules', {'GPUtil': mock_GPUtil}):
        yield

class TestSafeSystemBenchmark:
    @pytest.fixture
    def benchmark(self):
        """Fixture to create a fresh benchmark instance for each test"""
        from guro.core.benchmark import SafeSystemBenchmark
        return SafeSystemBenchmark()

    def test_initialization(self, benchmark):
        """Test proper initialization of benchmark instance"""
        assert isinstance(benchmark.console, Console)
        assert isinstance(benchmark.results, dict)
        assert not benchmark.running
        assert benchmark.MAX_CPU_USAGE <= 100
        assert benchmark.MAX_MEMORY_USAGE <= 100

    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_check_gpu_with_gpu(self, benchmark):
        """Test GPU detection when GPU is available"""
        # Create a mock GPU object
        mock_gpu = Mock()
        mock_gpu.name = "Test GPU"
        mock_gpu.memoryTotal = 8192
        mock_gpu.driver = "123.45"
        mock_GPUtil.getGPUs.return_value = [mock_gpu]
        
        gpu_info = benchmark._check_gpu()
        assert gpu_info['available']
        assert gpu_info['info']['name'] == "Test GPU"
        assert gpu_info['info']['count'] == 1
        assert gpu_info['info']['memory_total'] == 8192
        assert gpu_info['info']['driver_version'] == "123.45"

    def test_check_gpu_without_gpu(self, benchmark):
        """Test GPU detection when no GPU is available"""
        # Simulate no GPUs available
        mock_GPUtil.getGPUs.return_value = []
        
        gpu_info = benchmark._check_gpu()
        assert not gpu_info['available']
        assert gpu_info['info'] is None

    def test_get_system_info(self, benchmark):
        """Test system information gathering"""
        system_info = benchmark.get_system_info()
        
        assert system_info['system'] == platform.system()
        assert system_info['processor'] == platform.processor()
        assert system_info['cpu_cores'] == psutil.cpu_count(logical=False)
        assert system_info['cpu_threads'] == psutil.cpu_count(logical=True)
        assert isinstance(system_info['gpu'], dict)
        assert 'available' in system_info['gpu']

    @patch('time.sleep', return_value=None)
    def test_safe_cpu_test(self, mock_sleep, benchmark):
        """Test CPU benchmark functionality"""
        duration = 1
        benchmark.running = True
        result = benchmark.safe_cpu_test(duration)
        
        assert 'times' in result
        assert 'loads' in result
        assert isinstance(result['times'], list)
        assert isinstance(result['loads'], list)
        assert len(result['times']) > 0
        assert len(result['loads']) > 0

    @patch('time.sleep', return_value=None)
    def test_safe_memory_test(self, mock_sleep, benchmark):
        """Test memory benchmark functionality"""
        duration = 1
        benchmark.running = True
        result = benchmark.safe_memory_test(duration)
        
        assert 'times' in result
        assert 'usage' in result
        assert isinstance(result['times'], list)
        assert isinstance(result['usage'], list)
        assert len(result['times']) > 0
        assert len(result['usage']) > 0

    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_safe_gpu_test_with_gpu(self, benchmark):
        """Test GPU benchmark when GPU is available"""
        duration = 1
        
        # Create a mock GPU object for initial check
        mock_gpu_init = Mock()
        mock_gpu_init.name = "Test GPU"
        mock_gpu_init.memoryTotal = 8192
        mock_gpu_init.driver = "123.45"
        mock_GPUtil.getGPUs.return_value = [mock_gpu_init]
        
        # Set up the benchmark GPU check
        benchmark.has_gpu = benchmark._check_gpu()
        benchmark.running = True
        
        # Create a mock GPU for the test
        mock_gpu = Mock()
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 4096
        mock_GPUtil.getGPUs.return_value = [mock_gpu]
        
        result = benchmark.safe_gpu_test(duration)
        
        assert 'times' in result
        assert 'loads' in result
        assert 'memory_usage' in result
        assert isinstance(result['times'], list)
        assert isinstance(result['loads'], list)
        assert isinstance(result['memory_usage'], list)
        assert len(result['times']) > 0
        assert len(result['loads']) > 0
        assert len(result['memory_usage']) > 0

    def test_safe_gpu_test_without_gpu(self, benchmark):
        """Test GPU benchmark when no GPU is available"""
        benchmark.has_gpu = {'available': False, 'info': None}
        duration = 1
        
        result = benchmark.safe_gpu_test(duration)
        
        assert 'error' in result
        assert result['error'] == 'No GPU available'
        assert 'times' in result
        assert 'loads' in result
        assert len(result['times']) == 0
        assert len(result['loads']) == 0

    def test_generate_status_table(self, benchmark):
        """Test status table generation"""
        table = benchmark.generate_status_table()
        
        assert isinstance(table, Table)
        assert table.title == "Benchmark Status"
        assert len(table.columns) >= 2  # Should have at least metric and value columns

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_monitor_resources_safety_threshold(self, mock_memory, mock_cpu, benchmark):
        """Test resource monitoring safety thresholds"""
        mock_cpu.return_value = 90  # Above MAX_CPU_USAGE
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60
        mock_memory.return_value = mock_memory_obj
        
        benchmark.running = True
        benchmark.monitor_resources()
        
        assert not benchmark.running  # Should have stopped due to high CPU usage

    @patch('rich.live.Live')
    def test_mini_test(self, mock_live, benchmark):
        """Test mini benchmark execution"""
        benchmark.mini_test()
        assert 'system_info' in benchmark.results
        assert benchmark.results['duration'] == 30
        assert 'cpu' in benchmark.results
        assert 'memory' in benchmark.results

    @patch('rich.live.Live')
    def test_god_test(self, mock_live, benchmark):
        """Test god-level benchmark execution"""
        benchmark.god_test()
        assert 'system_info' in benchmark.results
        assert benchmark.results['duration'] == 60
        assert 'cpu' in benchmark.results
        assert 'memory' in benchmark.results
        assert 'gpu' in benchmark.results