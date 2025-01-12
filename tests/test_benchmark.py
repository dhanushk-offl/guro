import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import psutil
import platform
from rich.console import Console
from rich.table import Table
import time

# First, mock GPUtil to handle the import scenario
mock_GPUtil = Mock()
mock_GPUtil.getGPUs = Mock()

# Patch the module import
@patch.dict('sys.modules', {'GPUtil': mock_GPUtil})
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

    @patch('GPUtil.getGPUs')
    def test_check_gpu_with_gpu(self, mock_getGPUs, benchmark):
        """Test GPU detection when GPU is available"""
        # Create a mock GPU object with all required attributes
        mock_gpu = Mock(spec=['name', 'memoryTotal', 'driver', 'load', 'memoryUsed'])
        mock_gpu.name = "Test GPU"
        mock_gpu.memoryTotal = 8192
        mock_gpu.driver = "123.45"
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 4096
        mock_getGPUs.return_value = [mock_gpu]
        
        gpu_info = benchmark._check_gpu()
        assert gpu_info['available'] is True
        assert gpu_info['info']['name'] == "Test GPU"
        assert gpu_info['info']['count'] == 1
        assert gpu_info['info']['memory_total'] == 8192
        assert gpu_info['info']['driver_version'] == "123.45"

    @patch('GPUtil.getGPUs')
    def test_check_gpu_without_gpu(self, mock_getGPUs, benchmark):
        """Test GPU detection when no GPU is available"""
        mock_getGPUs.return_value = []
        
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

    @patch('GPUtil.getGPUs')
    def test_safe_gpu_test_with_gpu(self, mock_getGPUs, benchmark):
        """Test GPU benchmark when GPU is available"""
        # Mock GPU with required attributes
        mock_gpu = Mock(spec=['load', 'memoryUsed'])
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 4096
        mock_getGPUs.return_value = [mock_gpu]
        
        benchmark.running = True
        result = benchmark.safe_gpu_test(duration=0.1)
        
        assert 'times' in result
        assert 'loads' in result
        assert 'memory_usage' in result
        assert len(result['times']) > 0
        assert len(result['loads']) > 0
        assert len(result['memory_usage']) > 0

    def test_safe_gpu_test_without_gpu(self, benchmark):
        """Test GPU benchmark when GPU is not available"""
        benchmark.has_gpu['available'] = False
        result = benchmark.safe_gpu_test(duration=0.1)
        
        assert 'error' in result
        assert result['error'] == 'No GPU available'

    @patch('psutil.cpu_percent')
    def test_safe_cpu_test(self, mock_cpu_percent, benchmark):
        """Test CPU benchmark"""
        mock_cpu_percent.return_value = 50.0
        benchmark.running = True
        
        result = benchmark.safe_cpu_test(duration=0.1)
        
        assert 'times' in result
        assert 'loads' in result
        assert len(result['times']) > 0
        assert len(result['loads']) > 0

    @patch('psutil.virtual_memory')
    def test_safe_memory_test(self, mock_virtual_memory, benchmark):
        """Test memory benchmark"""
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_virtual_memory.return_value = mock_memory
        benchmark.running = True
        
        result = benchmark.safe_memory_test(duration=0.1)
        
        assert 'times' in result
        assert 'usage' in result
        assert len(result['times']) > 0
        assert len(result['usage']) > 0

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_monitor_resources_safety_threshold(self, mock_virtual_memory, mock_cpu_percent, benchmark):
        """Test resource monitoring safety thresholds"""
        mock_cpu_percent.return_value = 90.0  # Above MAX_CPU_USAGE
        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        benchmark.running = True
        benchmark.monitor_resources()
        assert not benchmark.running  # Should stop due to high CPU usage

    def test_generate_status_table(self, benchmark):
        """Test status table generation"""
        table = benchmark.generate_status_table()
        assert isinstance(table, Table)
        assert table.title == "Benchmark Status"

    @patch('rich.console.Console.print')
    def test_display_results(self, mock_print, benchmark):
        """Test results display"""
        benchmark.results = {
            'system_info': {
                'system': 'Test System',
                'processor': 'Test CPU',
                'cpu_cores': 4,
                'cpu_threads': 8,
                'gpu': {'available': False}
            },
            'duration': 30,
            'cpu': {'loads': [50.0, 60.0, 70.0]},
            'memory': {'usage': [60.0, 65.0, 70.0]}
        }
        
        benchmark.display_results("Test")
        mock_print.assert_called_once()

    @patch('threading.Thread')
    def test_mini_test(self, mock_thread, benchmark):
        """Test mini benchmark execution"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        benchmark.mini_test()
        
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        mock_thread_instance.join.assert_called_once()
        assert 'system_info' in benchmark.results
        assert 'duration' in benchmark.results

    @patch('threading.Thread')
    def test_god_test(self, mock_thread, benchmark):
        """Test comprehensive benchmark execution"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        benchmark.god_test()
        
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        mock_thread_instance.join.assert_called_once()
        assert 'system_info' in benchmark.results
        assert 'duration' in benchmark.results