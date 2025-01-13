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

from guro.cli.main import cli
from guro.core.heatmap import SystemHeatmap

@pytest.fixture
def heatmap():
    """Fixture to create a fresh heatmap instance for each test"""
    with patch('platform.system', return_value='Linux'):  # Use Linux as default for tests
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
    
    # Mock the required Windows DLLs
    with patch('ctypes.windll') as mock_windll:
        # Create mock objects for each DLL function
        mock_kernel32 = MagicMock()
        mock_ntdll = MagicMock()
        mock_powrprof = MagicMock()
        
        # Set up the mock DLL attributes
        mock_windll.kernel32 = mock_kernel32
        mock_windll.ntdll = mock_ntdll
        mock_windll.powrprof = mock_powrprof
        
        # Create the heatmap instance
        heatmap = SystemHeatmap()
        
        # Verify Windows-specific attributes are set up
        assert hasattr(heatmap, 'GetSystemPowerStatus')
        assert hasattr(heatmap, 'NtQuerySystemInformation')
        assert hasattr(heatmap, 'CallNtPowerInformation')

@patch('platform.system')
@patch('psutil.sensors_temperatures')
@patch('subprocess.check_output')
def test_linux_temps(mock_subprocess, mock_sensors, mock_system, heatmap, mock_temps):
    """Test Linux temperature gathering."""
    mock_system.return_value = 'Linux'
    
    # Mock psutil sensors
    mock_sensors.return_value = {
        'coretemp': [
            MagicMock(current=mock_temps['CPU'])
        ],
        'acpitz': [
            MagicMock(current=mock_temps['Motherboard'])
        ]
    }
    
    # Mock subprocess calls for GPU and storage temps
    mock_subprocess.side_effect = [
        str(mock_temps['GPU']).encode(),  # nvidia-smi
        (f"194 Temperature_Celsius     0   0   0    0    "
         f"{mock_temps['Storage']}").encode()  # smartctl
    ]
    
    temps = heatmap.get_system_temps()
    
    assert isinstance(temps, dict)
    assert all(component in temps for component in mock_temps.keys())
    assert temps['CPU'] == mock_temps['CPU']
    assert temps['Motherboard'] == mock_temps['Motherboard']

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
def test_run_method(mock_live, heatmap):
    """Test the run method."""
    # Create a mock Live context
    mock_live_instance = MagicMock()
    mock_live.return_value.__enter__.return_value = mock_live_instance
    
    # Mock the update method to raise KeyboardInterrupt after first update
    def raise_keyboard_interrupt(*args, **kwargs):
        raise KeyboardInterrupt()
    
    mock_live_instance.update.side_effect = raise_keyboard_interrupt
    
    # Run with a short duration to ensure test completes quickly
    with patch('time.sleep', return_value=None):  # Mock sleep to speed up test
        heatmap.run(interval=0.1, duration=1)
    
    # Verify the Live display was updated at least once
    assert mock_live_instance.update.call_count >= 1

def test_generate_system_layout(heatmap):
    """Test system layout generation."""
    with patch.object(heatmap, 'get_system_temps', return_value={
        'CPU': 50.0,
        'GPU': 45.0,
        'Motherboard': 40.0,
        'Storage': 35.0,
        'RAM': 30.0
    }):
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
    
    # Test with minimal duration to ensure quick test completion
    with patch('guro.core.heatmap.SystemHeatmap.run') as mock_run:
        result = runner.invoke(cli, ['heatmap', '--interval', '1', '--duration', '1'])
        assert result.exit_code == 0
        assert mock_run.called
    
    # Test with invalid interval
    result = runner.invoke(cli, ['heatmap', '--interval', '-1'])
    assert result.exit_code == 2
    
    # Test with invalid duration
    result = runner.invoke(cli, ['heatmap', '--duration', '-1'])
    assert result.exit_code == 2

@patch('platform.system')
def test_cross_platform_compatibility(mock_system, heatmap):
    """Test compatibility across different platforms."""
    for os in ['Windows', 'Linux', 'Darwin']:
        mock_system.return_value = os
        
        # Mock platform-specific methods to avoid actual system calls
        with patch.object(heatmap, 'get_windows_temps' if os == 'Windows' else
                         'get_linux_temps' if os == 'Linux' else
                         'get_macos_temps', return_value={
            'CPU': 50.0,
            'GPU': 45.0,
            'Motherboard': 40.0,
            'Storage': 35.0,
            'RAM': 30.0
        }):
            temps = heatmap.get_system_temps()
            
            assert isinstance(temps, dict)
            assert all(component in temps for component in heatmap.components)
            assert all(isinstance(temp, float) for temp in temps.values())
            assert all(0 <= temp <= 100 for temp in temps.values())