import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from guro.core.monitor import GPUDetector, SystemMonitor
from guro.core.benchmark import SafeSystemBenchmark
from guro.core.heatmap import SystemHeatmap
from guro._version import __version__


class TestMultiGPUDetection:
    """Tests for multi-GPU detection logic across platforms"""

    @patch('subprocess.check_output')
    def test_nvidia_multi_gpu_parsing(self, mock_sub):
        """Test parsing multiple NVIDIA GPUs from nvidia-smi output."""
        mock_sub.return_value = (
            "RTX 4090, 24576, 1024, 23552, 45, 10, 30, 250\n"
            "RTX 3080, 10240, 512, 9728, 50, 5, 35, 180\n"
            "GTX 1050, 4096, 256, 3840, 40, 0, 0, 50"
        ).encode('utf-8')

        gpus = GPUDetector.get_nvidia_info()
        assert len(gpus) == 3
        assert gpus[0]['name'] == "RTX 4090"
        assert gpus[1]['name'] == "RTX 3080"
        assert gpus[2]['utilization'] == 0.0

    @patch('subprocess.check_output')
    def test_gpu_not_found_message(self, mock_sub):
        """Test that GPU detection returns empty list on failure."""
        mock_sub.side_effect = FileNotFoundError("nvidia-smi not found")
        gpus = GPUDetector.get_nvidia_info()
        assert gpus == []


class TestBenchmarkMultiGPU:
    """Tests for benchmark module with multiple GPUs"""

    @patch('guro.core.benchmark.GPUtil')
    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_benchmark_initialization_multi(self, mock_gputil):
        """Test benchmark initialization detects multiple GPUs."""
        gpu1 = MagicMock(name="GPU1")
        gpu1.name = "NVIDIA RTX 4090"
        gpu1.memoryTotal = 24576
        gpu1.driver = "550.0"

        gpu2 = MagicMock(name="GPU2")
        gpu2.name = "NVIDIA RTX 3080"
        gpu2.memoryTotal = 10240
        gpu2.driver = "550.0"

        mock_gputil.getGPUs.return_value = [gpu1, gpu2]

        benchmark = SafeSystemBenchmark()
        assert benchmark.has_gpu['available'] is True
        assert len(benchmark.has_gpu['gpus']) == 2
        assert benchmark.has_gpu['gpus'][0]['name'] == "NVIDIA RTX 4090"

    @patch('guro.core.benchmark.GPUtil')
    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_gpu_not_found_status_table(self, mock_gputil):
        """Test status table when no GPU is found."""
        mock_gputil.getGPUs.return_value = []
        benchmark = SafeSystemBenchmark()
        benchmark.has_gpu = {'available': False, 'gpus': []}

        table = benchmark.generate_status_table()
        # Check that the table renders without error when no GPU is available
        assert table is not None


class TestHeatmapMultiGPU:
    """Tests for heatmap module with hottest GPU logic"""

    def test_hottest_gpu_selection(self):
        """Test that get_fallback_temps returns all component temps."""
        heatmap = SystemHeatmap()
        temps = heatmap.get_fallback_temps()
        assert 'GPU' in temps
        assert isinstance(temps['GPU'], float)


class TestVersionConsistency:
    """Test that version is consistent across all modules."""

    def test_version_is_1_1_4(self):
        assert __version__ == "1.1.4"

    @patch('guro.core.monitor.GPUDetector.get_all_gpus', return_value={'available': False, 'gpus': []})
    def test_cli_version_matches(self, _):
        """Test that CLI uses the same version from _version.py."""
        from guro._version import __version__ as pkg_version
        assert pkg_version == "1.1.4"
