import pytest
from unittest.mock import patch, MagicMock
import platform
import psutil
import numpy as np
from pathlib import Path
import subprocess
from rich.panel import Panel
from rich.text import Text
from click.testing import CliRunner
from guro.cli.main import cli

from guro.core.heatmap import SystemHeatmap

@pytest.fixture
def heatmap():
    """Fixture to create a fresh heatmap instance for each test"""
    return SystemHeatmap()

def test_initialization(heatmap):
    """Test proper initialization of SystemHeatmap."""
    assert heatmap.console is not None
    assert heatmap.history_size == 60
    assert isinstance(heatmap.components, dict)
    assert 'CPU' in heatmap.components
    assert 'GPU' in heatmap.components
    assert isinstance(heatmap.temp_maps, dict)

@patch('platform.system')
def test_windows_setup(mock_system):
    """Test Windows-specific setup."""
    mock_system.return_value = "Windows"
    heatmap = SystemHeatmap()
    if platform.system() == "Windows":
        assert hasattr(heatmap, 'GetSystemPowerStatus')
        assert hasattr(heatmap, 'NtQuerySystemInformation')

def test_temp_maps_initialization(heatmap):
    """Test temperature maps initialization."""
    for component, temp_map in heatmap.temp_maps.items():
        expected_shape = heatmap.components[component]['size']
        assert temp_map.shape == expected_shape
        assert np.all(temp_map == 0)

@patch('psutil.cpu_percent')
def test_get_cpu_load_temp(mock_cpu_percent, heatmap):
    """Test CPU load temperature calculation."""
    mock_cpu_percent.return_value = 50.0
    temp = heatmap.get_cpu_load_temp()
    assert isinstance(temp, float)
    assert temp == 40 + (50.0 * 0.6)

@patch('psutil.cpu_percent')
def test_get_gpu_load_temp(mock_cpu_percent, heatmap):
    """Test GPU load temperature calculation."""
    mock_cpu_percent.return_value = 50.0
    temp = heatmap.get_gpu_load_temp()
    assert isinstance(temp, float)
    assert temp == 35 + (50.0 * 0.5)

@patch('psutil.disk_io_counters')
def test_get_disk_load_temp(mock_disk_io, heatmap):
    """Test disk load temperature calculation."""
    mock_disk_io.return_value = MagicMock(
        read_bytes=1024**3,  # 1 GB
        write_bytes=1024**3  # 1 GB
    )
    temp = heatmap.get_disk_load_temp()
    assert isinstance(temp, float)
    assert temp > 30.0

def test_get_temp_char(heatmap):
    """Test temperature character and color mapping."""
    # Test cold temperature
    char, color = heatmap.get_temp_char(40)
    assert char == '·'
    assert color == "green"

    # Test warm temperature
    char, color = heatmap.get_temp_char(60)
    assert char == '▒'
    assert color == "yellow"

    # Test hot temperature
    char, color = heatmap.get_temp_char(80)
    assert char == '█'
    assert color == "red"

@patch('platform.system')
@patch('subprocess.check_output')
def test_linux_temps(mock_subprocess, mock_system, heatmap):
    """Test Linux temperature detection."""
    mock_system.return_value = "Linux"
    mock_subprocess.return_value = b"50\n"
    
    # Mock psutil sensors
    with patch('psutil.sensors_temperatures') as mock_sensors:
        mock_sensors.return_value = {
            'coretemp': [MagicMock(current=50.0)],
            'acpitz': [MagicMock(current=45.0)]
        }
        
        temps = heatmap.get_linux_temps()
        assert isinstance(temps, dict)
        assert 'CPU' in temps
        assert 'GPU' in temps
        assert 'Motherboard' in temps

def test_update_component_map(heatmap):
    """Test component temperature map updates."""
    component = 'CPU'
    test_temp = 50.0
    
    heatmap.update_component_map(component, test_temp)
    temp_map = heatmap.temp_maps[component]
    
    # Check if the map has been updated with noise
    assert not np.all(temp_map == 0)
    assert np.all(temp_map >= 0)
    assert np.all(temp_map <= 100)

def test_generate_system_layout(heatmap):
    """Test system layout generation."""
    layout = heatmap.generate_system_layout()
    assert isinstance(layout, Panel)
    assert "System Temperature Heatmap" in layout.title

@patch('psutil.cpu_percent')
@patch('psutil.virtual_memory')
def test_fallback_temps(mock_memory, mock_cpu, heatmap):
    """Test fallback temperature calculations."""
    mock_cpu.return_value = 50.0
    mock_memory.return_value = MagicMock(percent=60.0)
    
    temps = heatmap.get_fallback_temps()
    assert isinstance(temps, dict)
    assert 'CPU' in temps
    assert 'GPU' in temps
    assert 'Motherboard' in temps
    assert 'Storage' in temps
    assert 'RAM' in temps

@patch('time.sleep', return_value=None)
@patch('time.time')
def test_run_with_duration(mock_time, mock_sleep, heatmap):
    """Test run method with duration."""
    mock_time.side_effect = [0, 1, 2, 3]  # Simulate time passing
    
    # Test run with 2 second duration
    with patch('rich.live.Live'):
        heatmap.run(interval=1.0, duration=2)
        assert mock_sleep.call_count == 2

def test_cli_command_error_handling():
    """Test CLI command error handling."""
    runner = CliRunner()
    result = runner.invoke(cli, ['heatmap', '--interval', '-1'])
    assert result.exit_code != 0