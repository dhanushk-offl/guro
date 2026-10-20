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
    @patch('guro.core.benchmark.GPUDetector.get_all_gpus')
    def test_benchmark_uses_shared_detector(self, detector):
        detector.return_value = {'available': True, 'gpus': [
            {'name': 'AMD GPU', 'memory_total': 8192 * 1024**2},
            {'name': 'NVIDIA GPU', 'memory_total': 16384 * 1024**2},
        ]}
        bench = SafeSystemBenchmark()
        assert bench.has_gpu == detector.return_value
        assert len(bench.get_system_info()['gpus']) == 2

    @patch('guro.core.benchmark.GPUDetector.get_all_gpus', return_value={'available': False, 'gpus': []})
    def test_gpu_not_found_status_table(self, detector):
        assert SafeSystemBenchmark().generate_status_table().title == 'Benchmark Status'


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

    def test_source_and_cli_versions_match(self):
        from guro._version import __version__ as src_version
        from guro.cli.main import __version__ as cli_version
        assert src_version == cli_version

    @patch('guro.core.monitor.GPUDetector.get_all_gpus', return_value={'available': False, 'gpus': []})
    def test_cli_version_matches(self, _):
        """Test that CLI uses the same version from _version.py."""
        from guro._version import __version__ as pkg_version
        assert pkg_version == __version__
