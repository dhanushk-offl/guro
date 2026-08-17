import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import psutil
import platform
from rich.console import Console
from rich.table import Table

# Create a mock GPUtil module
mock_GPUtil = Mock()
mock_GPUtil.getGPUs = Mock()

@pytest.fixture(autouse=True)
def mock_gputil_env():
    """Fixture to mock GPUtil for all tests"""
    with patch('guro.core.benchmark.HAS_GPU_STATS', True), \
         patch('guro.core.benchmark.GPUtil', mock_GPUtil):
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
        # After init, _stop_event is clear (not set), so running == True
        assert benchmark.running is True
        assert benchmark.MAX_CPUSAFE <= 100
        assert benchmark.MAX_MEMORY_USAGE <= 100

    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_check_gpu_with_gpu(self, benchmark):
        """Test GPU detection when GPU is available"""
        from guro.core.benchmark import GPUtil as test_GPUtil
        mock_gpu = Mock()
        mock_gpu.name = "Test GPU"
        mock_gpu.memoryTotal = 8192
        mock_gpu.driver = "123.45"

        with patch.object(test_GPUtil, 'getGPUs', return_value=[mock_gpu]):
            gpu_info = benchmark._check_gpu()
            assert gpu_info['available']
            assert len(gpu_info['gpus']) == 1
            assert gpu_info['gpus'][0]['name'] == "Test GPU"
            assert gpu_info['gpus'][0]['memory_total'] == 8192
            assert gpu_info['gpus'][0]['driver_version'] == "123.45"

    def test_check_gpu_without_gpu(self, benchmark):
        """Test GPU detection when no GPU is available"""
        from guro.core.benchmark import GPUtil as test_GPUtil
        with patch.object(test_GPUtil, 'getGPUs', return_value=[]):
            gpu_info = benchmark._check_gpu()
            assert not gpu_info['available']
            assert gpu_info['gpus'] == []

    def test_get_system_info(self, benchmark):
        """Test system information gathering"""
        system_info = benchmark.get_system_info()

        assert system_info['system'] == platform.system()
        assert system_info['processor'] == platform.processor()
        assert system_info['cpu_cores'] == psutil.cpu_count(logical=False)
        assert system_info['cpu_threads'] == psutil.cpu_count(logical=True)
        assert isinstance(system_info['gpus'], list)

    @patch('time.sleep', return_value=None)
    def test_safe_cpu_test(self, mock_sleep, benchmark):
        """Test CPU benchmark functionality"""
        duration = 0.5
        benchmark._stop_event.clear()
        result = benchmark.safe_cpu_test(duration)

        assert 'times' in result
        assert 'loads' in result
        assert isinstance(result['times'], list)
        assert isinstance(result['loads'], list)

    @patch('time.sleep', return_value=None)
    def test_safe_memory_test(self, mock_sleep, benchmark):
        """Test memory benchmark functionality"""
        duration = 0.5
        benchmark._stop_event.clear()
        result = benchmark.safe_memory_test(duration)

        assert 'times' in result
        assert 'usage' in result
        assert isinstance(result['times'], list)
        assert isinstance(result['usage'], list)

    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_safe_gpu_test_with_gpu(self, benchmark):
        """Test GPU benchmark when GPU is available"""
        from guro.core.benchmark import GPUtil as test_GPUtil
        duration = 0.5

        mock_gpu = Mock()
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 4096

        benchmark.has_gpu = {'available': True, 'gpus': [{'name': 'Test'}]}
        benchmark._stop_event.clear()

        with patch.object(test_GPUtil, 'getGPUs', return_value=[mock_gpu]):
            result = benchmark.safe_gpu_test(duration)

        assert 'times' in result
        assert 'gpu_stats' in result
        assert len(result['gpu_stats']) > 0
        assert result['gpu_stats'][0][0]['load'] == 50.0

    @patch('guro.core.benchmark.HAS_GPU_STATS', False)
    def test_safe_gpu_test_without_gpu(self, benchmark):
        """Test GPU benchmark when no GPU is available"""
        benchmark.has_gpu = {'available': False, 'gpus': []}
        duration = 0.5
        benchmark._stop_event.clear()

        result = benchmark.safe_gpu_test(duration)

        assert 'error' in result
        assert result['error'] == 'No GPU available'
        assert 'times' in result
        assert 'gpu_stats' not in result
        assert len(result['times']) == 0

    def test_generate_status_table(self, benchmark):
        """Test status table generation"""
        from guro.core.benchmark import GPUtil as test_GPUtil
        mock_gpu = Mock()
        mock_gpu.name = "Test GPU"
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 4096
        mock_gpu.memoryTotal = 8192

        benchmark.has_gpu = {'available': True, 'gpus': [{'name': 'Test'}]}
        with patch.object(test_GPUtil, 'getGPUs', return_value=[mock_gpu]):
            table = benchmark.generate_status_table()

            assert isinstance(table, Table)
            assert table.title == "Benchmark Status"
            assert len(table.columns) >= 2

    @patch('psutil.virtual_memory')
    def test_monitor_resources_safety_threshold(self, mock_memory, benchmark):
        """Test resource monitoring stops after sustained high *external* CPU"""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60
        mock_memory_obj.total = 16000 * 1024 * 1024
        mock_memory_obj.available = 8000 * 1024 * 1024
        mock_memory.return_value = mock_memory_obj

        benchmark._stop_event.clear()
        with patch.object(benchmark, '_external_cpu_percent', return_value=99.0):
            benchmark.monitor_resources()

        assert benchmark._stop_event.is_set()  # Should have stopped due to sustained high CPU usage
        assert benchmark.stop_reason != ''

    @patch('psutil.virtual_memory')
    def test_monitor_resources_ignores_own_load(self, mock_memory, benchmark):
        """Test that the benchmark's own load never trips the watchdog."""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 50
        mock_memory_obj.total = 16000 * 1024 * 1024
        mock_memory_obj.available = 8000 * 1024 * 1024
        mock_memory.return_value = mock_memory_obj

        iterations = {'count': 0}

        def low_external_cpu():
            iterations['count'] += 1
            if iterations['count'] >= 2:
                benchmark._stop_event.set()  # end the loop from outside
            return 50.0  # well below MAX_CPUSAFE

        benchmark._stop_event.clear()
        with patch.object(benchmark, '_external_cpu_percent', side_effect=low_external_cpu):
            benchmark.monitor_resources()

        # Watchdog never decided to stop on its own — no stop_reason recorded
        assert benchmark.stop_reason == ''

    @patch('psutil.virtual_memory')
    def test_external_cpu_excludes_benchmark_own_usage(self, mock_memory, benchmark):
        """Benchmark's own CPU usage is subtracted from the external percentage."""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 50
        mock_memory_obj.total = 16000 * 1024 * 1024
        mock_memory_obj.available = 8000 * 1024 * 1024
        mock_memory.return_value = mock_memory_obj

        fake_proc = Mock()
        fake_proc.cpu_percent.return_value = 80.0  # benchmark using 80% of one core
        benchmark._proc = fake_proc

        with patch('psutil.cpu_percent', return_value=60.0), \
             patch('psutil.cpu_count', return_value=4):
            external = benchmark._external_cpu_percent()

        # own_pct = 80/4 = 20; external = 60 - 20 = 40
        assert external == 40.0

    @patch('psutil.virtual_memory')
    def test_external_memory_excludes_benchmark_own_usage(self, mock_memory, benchmark):
        """Benchmark-owned memory is excluded from the watchdog memory percentage."""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 99.9   # system-wide would trip the threshold
        mock_memory_obj.total = 16000 * 1024 * 1024
        mock_memory_obj.available = 16 * 1024 * 1024  # 99.9% used system-wide
        mock_memory.return_value = mock_memory_obj

        fake_proc = Mock()
        fake_full = Mock()
        fake_full.uss = 1000 * 1024 * 1024
        fake_proc.memory_full_info.return_value = fake_full
        benchmark._proc = fake_proc

        external = benchmark._external_memory_percent()

        # system used = total - available = 15984MB; minus own 1000MB = 14984MB
        # external % = 14984 / 16000 = 93.65% (below the 95% threshold)
        assert external == pytest.approx(93.65, abs=0.01)

    @patch('psutil.virtual_memory')
    def test_benchmark_own_memory_never_trips_watchdog(self, mock_memory, benchmark):
        """Watchdog does not stop when only the benchmark's own memory is high."""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 99.9   # system-wide would trip the threshold
        mock_memory_obj.total = 16000 * 1024 * 1024
        mock_memory_obj.available = 16 * 1024 * 1024
        mock_memory.return_value = mock_memory_obj

        fake_proc = Mock()
        fake_full = Mock()
        fake_full.uss = 1000 * 1024 * 1024
        fake_proc.memory_full_info.return_value = fake_full
        benchmark._proc = fake_proc

        iterations = {'count': 0}

        def low_external_cpu():
            iterations['count'] += 1
            if iterations['count'] >= 2:
                benchmark._stop_event.set()  # end the loop from outside
            return 50.0

        benchmark._stop_event.clear()
        with patch.object(benchmark, '_external_cpu_percent', side_effect=low_external_cpu):
            benchmark.monitor_resources()

        # External memory stays ~89.9% < 95%, so the watchdog never fires
        assert benchmark.stop_reason == ''

    @patch('rich.live.Live')
    def test_mini_test(self, mock_live, benchmark):
        """Test mini benchmark execution"""
        from guro.core.benchmark import GPUtil as test_GPUtil
        with patch.object(test_GPUtil, 'getGPUs', return_value=[]), \
             patch.object(benchmark, 'safe_cpu_test',
                          return_value={'times': [], 'loads': [10.0]}), \
             patch.object(benchmark, 'safe_memory_test',
                          return_value={'times': [], 'usage': [50.0], 'bandwidth_mbps': []}), \
             patch.object(benchmark, 'safe_gpu_test',
                          return_value={'times': [], 'gpu_stats': []}):
            benchmark.mini_test()
            assert 'system_info' in benchmark.results
            assert benchmark.results['duration'] == 30
            assert 'cpu' in benchmark.results
            assert 'memory' in benchmark.results

    @patch('rich.live.Live')
    def test_god_test(self, mock_live, benchmark):
        """Test god-level benchmark execution"""
        from guro.core.benchmark import GPUtil as test_GPUtil
        with patch.object(test_GPUtil, 'getGPUs', return_value=[]), \
             patch.object(benchmark, 'safe_cpu_test',
                          return_value={'times': [], 'loads': [10.0]}), \
             patch.object(benchmark, 'safe_memory_test',
                          return_value={'times': [], 'usage': [50.0], 'bandwidth_mbps': []}), \
             patch.object(benchmark, 'safe_gpu_test',
                          return_value={'times': [], 'gpu_stats': []}):
            benchmark.god_test()
            assert 'system_info' in benchmark.results
            assert benchmark.results['duration'] == 60
            assert 'cpu' in benchmark.results
            assert 'memory' in benchmark.results

    def test_stop_event_property(self, benchmark):
        """Test that running property works with threading.Event"""
        benchmark._stop_event.clear()
        assert benchmark.running is True

        benchmark._stop_event.set()
        assert benchmark.running is False

        benchmark.running = True
        assert benchmark._stop_event.is_set() is False

        benchmark.running = False
        assert benchmark._stop_event.is_set() is True
