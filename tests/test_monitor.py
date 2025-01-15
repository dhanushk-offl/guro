# tests/test_monitor.py
import pytest
from unittest.mock import patch, MagicMock
import platform
import psutil
import subprocess
from datetime import datetime
import os
import sys
from typing import Dict, List

# Import your classes
from guro.core.monitor import SystemMonitor, GPUDetector, ASCIIGraph

@pytest.fixture
def monitor():
    """Fixture to create a fresh monitor instance for each test"""
    return SystemMonitor()

@pytest.fixture
def ascii_graph():
    """Fixture for ASCII graph tests"""
    return ASCIIGraph(width=50, height=10)

@patch('psutil.cpu_freq')
@patch('psutil.cpu_count')
def test_get_system_info(mock_cpu_count, mock_cpu_freq, monitor):
    """Test system information retrieval"""
    # Mock CPU frequency
    mock_freq = MagicMock()
    mock_freq.current = 2400.0
    mock_cpu_freq.return_value = mock_freq
    
    # Mock CPU count
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
    mock_check_output.return_value = mock_output
    
    gpu_info = GPUDetector.get_nvidia_info()
    
    assert isinstance(gpu_info, list)
    if gpu_info:  # If GPU is detected
        assert 'name' in gpu_info[0]
        assert 'memory_total' in gpu_info[0]
        assert 'temperature' in gpu_info[0]
        assert gpu_info[0]['type'] == 'NVIDIA'

@patch('subprocess.check_output')
def test_amd_gpu_detection(mock_check_output):
    """Test AMD GPU detection"""
    mock_output = """
    GPU 0: Card Series
    GPU Memory Use: 4096 MB
    Total GPU Memory: 8192 MB
    Temperature: 70 C
    """
    mock_check_output.return_value = mock_output
    
    gpu_info = GPUDetector.get_amd_info()
    
    assert isinstance(gpu_info, list)
    if gpu_info:  # If GPU is detected
        assert 'memory_total' in gpu_info[0]
        assert 'temperature' in gpu_info[0]
        assert gpu_info[0]['type'] == 'AMD'

def test_ascii_graph(ascii_graph):
    """Test ASCII graph generation"""
    # Test adding points
    test_values = [0, 25, 50, 75, 100]
    for value in test_values:
        ascii_graph.add_point(value)
    
    # Test rendering
    rendered = ascii_graph.render("Test Graph")
    assert isinstance(rendered, str)
    assert len(rendered) > 0

@patch('psutil.virtual_memory')
def test_performance_monitoring(mock_virtual_memory, monitor):
    """Test performance monitoring functionality"""
    # Mock memory info
    mock_memory = MagicMock()
    mock_memory.total = 16 * 1024**3  # 16GB
    mock_memory.available = 8 * 1024**3  # 8GB
    mock_memory.percent = 50.0
    mock_virtual_memory.return_value = mock_memory

    # Test monitoring data collection
    monitor.monitoring_data = []
    monitor.run_performance_test(interval=0.1, duration=1, export_data=True)
    
    assert os.path.exists('monitoring_data.csv')
    assert len(monitor.monitoring_data) > 0
    
    # Clean up test file
    if os.path.exists('monitoring_data.csv'):
        os.remove('monitoring_data.csv')

@pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-only test")
def test_cpu_temperature_linux(monitor):
    """Test CPU temperature reading on Linux"""
    temp = monitor._get_cpu_temperature()
    if temp is not None:  # Temperature might not be available on all systems
        assert isinstance(temp, float)
        assert temp >= 0
        assert temp < 150  # Reasonable temperature range

@patch('platform.system')
@patch('platform.release')
@patch('platform.processor')
def test_system_detection(mock_processor, mock_release, mock_system, monitor):
    """Test system detection across different platforms"""
    # Test for Linux
    mock_system.return_value = 'Linux'
    mock_release.return_value = '5.10.0'
    mock_processor.return_value = 'x86_64'
    
    info = monitor.get_system_info()
    assert 'Linux' in info['os']
    
    # Test for Windows
    mock_system.return_value = 'Windows'
    mock_release.return_value = '10'
    info = monitor.get_system_info()
    assert 'Windows' in info['os']

def test_error_handling():
    """Test error handling in critical sections"""
    # Test GPU detection with no GPUs
    gpu_info = GPUDetector.get_all_gpus()
    assert isinstance(gpu_info, dict)
    assert 'available' in gpu_info
    assert 'gpus' in gpu_info

    # Test graph rendering with no data
    graph = ASCIIGraph()
    rendered = graph.render()
    assert rendered == ""