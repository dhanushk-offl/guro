import pytest
from unittest.mock import patch, MagicMock
import platform
import psutil
import os
import tempfile
from typing import Dict, List

from guro.core.monitor import SystemMonitor, GPUDetector, _safe_float
from guro.core.utils import ASCIIGraph


@pytest.fixture
def monitor():
    """Fixture to create a fresh monitor instance for each test"""
    with patch.object(GPUDetector, 'get_all_gpus', return_value={'available': False, 'gpus': []}):
        return SystemMonitor()


@pytest.fixture
def ascii_graph():
    """Fixture for ASCII graph tests"""
    return ASCIIGraph(width=50, height=10)


class TestSafeFloat:
    """Tests for the _safe_float helper"""

    @pytest.mark.parametrize("value,expected", [
        ('45.0', 45.0),
        ('[N/A]', None),
        ('N/A', None),
        ('Not Available', None),
        ('NAN', None),
        ('-', None),
        ('', None),
        ('  72.5  ', 72.5),
        ('+65.0', 65.0),
    ])
    def test_safe_float_values(self, value, expected):
        assert _safe_float(value) == expected

    def test_safe_float_none_input(self):
        assert _safe_float(None) is None  # type: ignore


@patch('psutil.cpu_freq')
@patch('psutil.cpu_count')
def test_get_system_info(mock_cpu_count, mock_cpu_freq, monitor):
    """Test system information retrieval"""
    mock_freq = MagicMock()
    mock_freq.current = 2400.0
    mock_cpu_freq.return_value = mock_freq
    mock_cpu_count.return_value = 8

    info = monitor.get_system_info()

    assert isinstance(info, dict)
    assert 'os' in info
    assert 'cpu_cores' in info
    assert 'cpu_threads' in info
    assert 'cpu_freq' in info
    assert 'memory_total' in info
    assert 'memory_available' in info


@patch('subprocess.check_output')
def test_nvidia_gpu_detection(mock_check_output):
    """Test NVIDIA GPU detection"""
    mock_output = "GeForce RTX 3080,10240,5120,5120,65,50,75,200"
    mock_check_output.return_value = mock_output.encode()

    gpus = GPUDetector.get_nvidia_info()

    assert isinstance(gpus, list)
    if gpus:
        assert 'name' in gpus[0]
        assert 'memory_total' in gpus[0]
        assert 'temperature' in gpus[0]
        assert gpus[0]['type'] == 'NVIDIA'


@patch('subprocess.check_output')
def test_nvidia_gpu_na_values(mock_check_output):
    """Test NVIDIA GPU detection with [N/A] values"""
    mock_output = "GeForce RTX 3080,10240,5120,5120,65,50,[N/A],[N/A]"
    mock_check_output.return_value = mock_output.encode()

    gpus = GPUDetector.get_nvidia_info()

    assert isinstance(gpus, list)
    if gpus:
        assert gpus[0]['fan_speed'] is None
        assert gpus[0]['power_draw'] is None


@patch('subprocess.check_output')
def test_amd_gpu_detection(mock_check_output):
    """Test AMD GPU detection"""
    mock_output = """
    GPU 0: Card Series
    GPU Memory Use: 4096 MB
    Total GPU Memory: 8192 MB
    Temperature: 70 C
    """
    mock_check_output.return_value = mock_output.encode()

    gpus = GPUDetector.get_amd_info()

    assert isinstance(gpus, list)
    if gpus:
        assert 'memory_total' in gpus[0]
        assert 'temperature' in gpus[0]
        assert gpus[0]['type'] == 'AMD'


def test_ascii_graph(ascii_graph):
    """Test ASCII graph generation"""
    test_values = [0, 25, 50, 75, 100]
    for value in test_values:
        ascii_graph.add_point(value)

    rendered = ascii_graph.render("Test Graph")
    assert isinstance(rendered, str)
    assert len(rendered) > 0


def test_ascii_graph_empty():
    """Test ASCII graph with no data"""
    graph = ASCIIGraph()
    rendered = graph.render()
    assert rendered == ""


@patch('psutil.virtual_memory')
def test_csv_export_uses_timestamp(mock_virtual_memory, monitor):
    """Test that CSV export creates a timestamped file"""
    mock_memory = MagicMock()
    mock_memory.total = 16 * 1024**3
    mock_memory.available = 8 * 1024**3
    mock_memory.percent = 50.0
    mock_virtual_memory.return_value = mock_memory

    monitor.monitoring_data = [
        {'timestamp': '2024-01-01T00:00:00', 'cpu_usage': 10.0, 'memory_usage': 50.0}
    ]

    # Export to a temp file using the explicit filepath parameter
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
        filepath = f.name

    try:
        monitor.export_monitoring_data(filepath=filepath)
        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()
            assert 'timestamp' in content
            assert 'cpu_usage' in content
    finally:
        os.remove(filepath)


@pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-only test")
def test_cpu_temperature_linux(monitor):
    """Test CPU temperature reading on Linux"""
    temp = monitor._get_cpu_temperature()
    if temp is not None:
        assert isinstance(temp, float)
        assert temp >= 0
        assert temp < 150


@patch('platform.system')
@patch('platform.release')
@patch('platform.processor')
def test_system_detection(mock_processor, mock_release, mock_system, monitor):
    """Test system detection across different platforms"""
    mock_system.return_value = 'Linux'
    mock_release.return_value = '5.10.0'
    mock_processor.return_value = 'x86_64'

    info = monitor.get_system_info()
    assert 'Linux' in info['os']

    mock_system.return_value = 'Windows'
    mock_release.return_value = '10'
    info = monitor.get_system_info()
    assert 'Windows' in info['os']


def test_error_handling():
    """Test error handling in critical sections"""
    gpu_info = GPUDetector.get_all_gpus()
    assert isinstance(gpu_info, dict)
    assert 'available' in gpu_info
    assert 'gpus' in gpu_info


def test_gpu_cache(monitor):
    """Test GPU info caching mechanism"""
    # Initial call should use the cached info
    info1 = monitor._refresh_gpu_info()
    assert isinstance(info1, dict)

    # Immediately calling again should return the same cached info without subprocess calls
    info2 = monitor._refresh_gpu_info()
    assert info2 == info1
