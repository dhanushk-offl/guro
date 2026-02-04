import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from guro.core.monitor import GPUDetector, SystemMonitor
from guro.core.benchmark import SafeSystemBenchmark
from guro.core.heatmap import SystemHeatmap

class TestMultiGPUDetection:
    """Tests for multi-GPU detection logic across platforms"""

    @patch('subprocess.check_output')
    def test_nvidia_multi_gpu_parsing(self, mock_sub):
        # Mocking 3 NVIDIA GPUs output from nvidia-smi
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
        # Simulate no GPUs found by raising an error or returning empty
        mock_sub.side_effect = Exception("No nvidia-smi")
        gpus = GPUDetector.get_nvidia_info()
        assert gpus == []

class TestBenchmarkMultiGPU:
    """Tests for benchmark module with multiple GPUs"""

    @patch('GPUtil.getGPUs')
    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_benchmark_initialization_multi(self, mock_gpus):
        gpu1 = MagicMock(name="GPU1")
        gpu1.name = "NVIDIA RTX 4090"
        gpu1.memoryTotal = 24576
        gpu1.driver = "550.0"
        
        gpu2 = MagicMock(name="GPU2")
        gpu2.name = "NVIDIA RTX 3080"
        gpu2.memoryTotal = 10240
        gpu2.driver = "550.0"
        
        mock_gpus.return_value = [gpu1, gpu2]
        
        benchmark = SafeSystemBenchmark()
        assert benchmark.has_gpu['available'] is True
        assert len(benchmark.has_gpu['gpus']) == 2
        assert benchmark.has_gpu['gpus'][0]['name'] == "NVIDIA RTX 4090"

    @patch('GPUtil.getGPUs')
    @patch('guro.core.benchmark.HAS_GPU_STATS', True)
    def test_gpu_not_found_status_table(self, mock_gpus):
        mock_gpus.return_value = []
        benchmark = SafeSystemBenchmark()
        benchmark.has_gpu = {'available': False, 'gpus': []}
        
        table = benchmark.generate_status_table()
        # Check rows for the "GPU not found" message
        found_message = False
        for i in range(table.row_count):
            row_data = [str(cell) for cell in table.columns[1]._cells]
            if any("GPU not found in your device" in r for r in row_data):
                found_message = True
        assert found_message is True

class TestHeatmapMultiGPU:
    """Tests for heatmap module with hottest GPU logic"""

    @patch('subprocess.check_output')
    def test_linux_hottest_gpu(self, mock_sub):
        # Mock lm-sensors output with two GPUs
        mock_sub.return_value = (
            "gpu1-pci-0100\nAdapter: PCI adapter\ntemp1:        +45.0°C\n\n"
            "gpu2-pci-0200\nAdapter: PCI adapter\ntemp1:        +65.0°C\n"
        ).encode('utf-8')
        heatmap = SystemHeatmap()
        temps = heatmap.get_linux_temps()
        # Should pick the max (65.0)
        assert temps['GPU'] == 65.0
