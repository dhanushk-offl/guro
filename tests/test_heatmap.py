import pytest
from unittest.mock import patch, MagicMock, mock_open
import platform
import psutil
import numpy as np
from pathlib import Path
import subprocess
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from click.testing import CliRunner

# Assuming your CLI is in these locations
from guro.cli.main import cli
from guro.core.heatmap import SystemHeatmap

@pytest.fixture
def heatmap():
    """Fixture to create a fresh heatmap instance for each test"""
    return SystemHeatmap()

@pytest.fixture
def mock_temps():
    """Fixture for mock temperature data"""
    return {
        'CPU': 50.0,
        'GPU': 45.0,
        'Motherboard': 40.0,
        'Storage': 35.0,
        'RAM': 30.0
    }

def test_initialization(heatmap):
    """Test proper initialization of SystemHeatmap."""
    assert heatmap.console is not None
    assert heatmap.history_size == 60
    assert isinstance(heatmap.components, dict)
    assert all(component in heatmap.components 
              for component in ['CPU', 'GPU', 'Motherboard', 'RAM', 'Storage'])
    assert isinstance(heatmap.temp_maps, dict)
    assert all(isinstance(heatmap.temp_maps[component], np.ndarray) 
              for component in heatmap.components)

@patch('platform.system')
def test_windows_setup(mock_system):
    """Test Windows-specific setup."""
    mock_system.return_value = "Windows"
    with patch('ctypes.windll') as mock_windll:
        mock_windll.kernel32.GetSystemPowerStatus = MagicMock()
        mock_windll.ntdll.NtQuerySystemInformation = MagicMock()
        mock_windll.powrprof.CallNtPowerInformation = MagicMock()
        
        heatmap = SystemHeatmap()
        if platform.system() == "Windows":
            assert hasattr(heatmap, 'GetSystemPowerStatus')
            assert hasattr(heatmap, 'NtQuerySystemInformation')
            assert hasattr(heatmap, 'CallNtPowerInformation')

@patch('psutil.sensors_temperatures')
@patch('subprocess.check_output')
def test_linux_temps(mock_subprocess, mock_sensors, heatmap, mock_temps):
    """Test Linux temperature gathering."""
    mock_sensors.return_value = {
        'coretemp': [
            MagicMock(current=mock_temps['CPU'])
        ],
        'acpitz': [
            MagicMock(current=mock_temps['Motherboard'])
        ]
    }
    
    # Mock nvidia-smi output
    mock_subprocess.side_effect = [
        mock_temps['GPU'].encode(),  # nvidia-smi
        f"194 Temperature_Celsius     0   0   0    0    {mock_temps['Storage']}".encode()  # smartctl
    ]
    
    with patch('platform.system', return_value='Linux'):
        temps = heatmap.get_system_temps()
        assert isinstance(temps, dict)
        assert all(component in temps for component in mock_temps.keys())
        assert temps['CPU'] == mock_temps['CPU']

def test_get_temp_char(heatmap):
    """Test temperature character mapping."""
    cold_char, cold_color = heatmap.get_temp_char(30.0)
    warm_char, warm_color = heatmap.get_temp_char(60.0)
    hot_char, hot_color = heatmap.get_temp_char(80.0)
    
    assert cold_color == "green"
    assert warm_color == "yellow"
    assert hot_color == "red"
    assert isinstance(cold_char, str)
    assert isinstance(warm_char, str)
    assert isinstance(hot_char, str)

def test_update_component_map(heatmap):
    """Test component map updating."""
    component = 'CPU'
    temp = 50.0
    
    original_shape = heatmap.temp_maps[component].shape
    heatmap.update_component_map(component, temp)
    
    assert heatmap.temp_maps[component].shape == original_shape
    assert np.all(heatmap.temp_maps[component] >= 0)
    assert np.all(heatmap.temp_maps[component] <= 100)

@patch('rich.live.Live')
@patch('time.sleep', return_value=None)
def test_run_method(mock_sleep, mock_live, heatmap):
    """Test the run method."""
    mock_live_instance = MagicMock()
    mock_live.return_value.__enter__.return_value = mock_live_instance
    
    def stop_after_updates(*args, **kwargs):
        mock_live_instance.update.call_count = 2
        raise KeyboardInterrupt()
    
    mock_live_instance.update.side_effect = stop_after_updates
    
    heatmap.run(interval=0.1)
    
    assert mock_live_instance.update.call_count >= 1

def test_generate_system_layout(heatmap):
    """Test system layout generation."""
    layout = heatmap.generate_system_layout()
    
    assert isinstance(layout, Panel)
    assert "System Temperature Heatmap" in layout.title
    assert isinstance(layout.renderable, Text)

def test_fallback_temps(heatmap):
    """Test fallback temperature gathering."""
    with patch('psutil.cpu_percent', return_value=50.0):
        with patch('psutil.virtual_memory', return_value=MagicMock(percent=60.0)):
            temps = heatmap.get_fallback_temps()
            
            assert isinstance(temps, dict)
            assert all(component in temps for component in heatmap.components)
            assert all(isinstance(temp, float) for temp in temps.values())
            assert all(0 <= temp <= 100 for temp in temps.values())

def test_cli_command():
    """Test CLI command basic functionality."""
    runner = CliRunner()
    
    # Test with valid interval
    result = runner.invoke(cli, ['heatmap', '--interval', '1'])
    assert result.exit_code == 0 or result.exit_code == -1  # -1 for KeyboardInterrupt
    
    # Test with invalid interval
    result = runner.invoke(cli, ['heatmap', '--interval', '-1'])
    assert result.exit_code == 2  # Invalid parameter should return 2
    
    # Test with invalid duration
    result = runner.invoke(cli, ['heatmap', '--duration', '-1'])
    assert result.exit_code == 2  # Invalid parameter should return 2

@patch('platform.system')
def test_cross_platform_compatibility(mock_system, heatmap):
    """Test compatibility across different platforms."""
    for os in ['Windows', 'Linux', 'Darwin']:
        mock_system.return_value = os
        temps = heatmap.get_system_temps()
        
        assert isinstance(temps, dict)
        assert all(component in temps for component in heatmap.components)
        assert all(isinstance(temp, float) for temp in temps.values())
        assert all(0 <= temp <= 100 for temp in temps.values())