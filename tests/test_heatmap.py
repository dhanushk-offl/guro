import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import platform
import psutil
import numpy as np
from pathlib import Path
import subprocess
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from click.testing import CliRunner
import ctypes
import click
import time

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

def test_run_method(heatmap):
    """Test the run method."""
    updates = {'count': 0}
    mock_panel = Panel("Test")
    
    def mock_update(content):
        updates['count'] += 1
        if updates['count'] >= 1:
            raise KeyboardInterrupt()

    mock_live = MagicMock()
    mock_live.update = mock_update

    with patch('rich.live.Live', return_value=mock_live) as mock_live_class, \
         patch('time.sleep', return_value=None) as mock_sleep, \
         patch.object(heatmap, 'generate_system_layout', return_value=mock_panel):
        
        # Set up the context manager behavior
        mock_live_class.return_value.__enter__.return_value = mock_live
        mock_live_class.return_value.__exit__.return_value = None

        # Run the heatmap
        try:
            heatmap.run(interval=0.1, duration=1)
        except KeyboardInterrupt:
            pass

        # Verify the update was called and sleep was called
        assert updates['count'] >= 1, f"Update was called {updates['count']} times, expected at least 1"
        mock_sleep.assert_called_with(0.1)

@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
def test_windows_setup():
    """Test Windows-specific setup."""
    with patch('platform.system', return_value="Windows"), \
         patch('guro.core.heatmap.windll', create=True) as mock_windll, \
         patch('guro.core.heatmap.SYSTEM_POWER_STATUS', create=True), \
         patch('guro.core.heatmap.PROCESSOR_POWER_INFORMATION', create=True):
        
        # Set up mock Windows DLL functions
        mock_windll.kernel32 = MagicMock()
        mock_windll.ntdll = MagicMock()
        mock_windll.powrprof = MagicMock()
        
        heatmap = SystemHeatmap()
        
        # Verify Windows-specific setup
        assert hasattr(heatmap, 'system')
        assert heatmap.system == "Windows"

def test_linux_temps(heatmap, mock_temps):
    """Test Linux temperature gathering."""
    with patch('platform.system', return_value='Linux'), \
         patch('psutil.sensors_temperatures') as mock_sensors, \
         patch('subprocess.check_output') as mock_subprocess:
        
        # Mock psutil sensors
        mock_sensors.return_value = {
            'coretemp': [
                MagicMock(current=mock_temps['CPU'])
            ],
            'acpitz': [
                MagicMock(current=mock_temps['Motherboard'])
            ]
        }
        
        # Mock subprocess calls
        mock_subprocess.side_effect = [
            str(mock_temps['GPU']).encode(),  # nvidia-smi
            (f"194 Temperature_Celsius     0   0   0    0    "
             f"{mock_temps['Storage']}").encode()  # smartctl
        ]
        
        temps = heatmap.get_linux_temps()
        
        assert isinstance(temps, dict)
        assert all(component in temps for component in mock_temps.keys())
        assert abs(temps['CPU'] - mock_temps['CPU']) < 0.1
        assert abs(temps['Motherboard'] - mock_temps['Motherboard']) < 0.1

def test_cli_command():
    """Test CLI command basic functionality."""
    runner = CliRunner()
    
    # Test successful cases
    with patch('guro.core.heatmap.SystemHeatmap.run') as mock_run:
        # Test with valid interval and duration
        result = runner.invoke(cli, ['heatmap', '--interval', '1', '--duration', '1'])
        assert result.exit_code == 0, f"Failed with output: {result.output}"
        assert mock_run.called
        
        # Test with default values
        result = runner.invoke(cli, ['heatmap'])
        assert result.exit_code == 0, f"Failed with output: {result.output}"
    
    # Test invalid cases
    invalid_cases = [
        ('--interval', '-1', "Invalid value for '--interval' / '-i': -1.0 is not in the range x>=0.1"),
        ('--interval', '0', "Invalid value for '--interval' / '-i': 0.0 is not in the range x>=0.1"),
        ('--duration', '-1', "Invalid value for '--duration' / '-d': -1 is not in the range x>=1"),
        ('--duration', '0', "Invalid value for '--duration' / '-d': 0 is not in the range x>=1"),
    ]
    
    for param, value, expected_error in invalid_cases:
        result = runner.invoke(cli, ['heatmap', param, value])
        assert result.exit_code == 2, (
            f"Expected exit code 2 for {param}={value}, got {result.exit_code}\n"
            f"Output was: {result.output}"
        )
        assert expected_error in result.output, (
            f"Expected error message containing '{expected_error}'\n"
            f"Got output: {result.output}"
        )

def test_cli_keyboard_interrupt():
    """Test CLI command handles keyboard interrupt."""
    runner = CliRunner()
    
    with patch('guro.core.heatmap.SystemHeatmap.run') as mock_run:
        mock_run.side_effect = KeyboardInterrupt()
        result = runner.invoke(cli, ['heatmap'])
        assert result.exit_code == 0
        assert "stopped by user" in result.output.lower()

def test_cli_error_handling():
    """Test CLI command handles general errors."""
    runner = CliRunner()
    
    with patch('guro.core.heatmap.SystemHeatmap.run') as mock_run:
        mock_run.side_effect = Exception("Test error")
        result = runner.invoke(cli, ['heatmap'])
        assert result.exit_code == 0  # We're catching the error in the CLI
        assert "error during heatmap visualization" in result.output.lower()

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

@patch('platform.system')
def test_cross_platform_compatibility(mock_system, heatmap):
    """Test compatibility across different platforms."""
    for os_name in ['Windows', 'Linux', 'Darwin']:
        mock_system.return_value = os_name
        
        # Mock the appropriate temperature gathering method
        method_name = {
            'Windows': 'get_windows_temps',
            'Linux': 'get_linux_temps',
            'Darwin': 'get_macos_temps'
        }[os_name]
        
        with patch.object(heatmap, method_name, return_value={
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