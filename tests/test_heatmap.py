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
import ctypes
import click

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

@patch('rich.live.Live')
@patch('time.sleep', return_value=None)
def test_run_method(mock_sleep, mock_live, heatmap):
    """Test the run method."""
    # Set up the mock Live context manager
    mock_live_instance = MagicMock()
    mock_live.return_value.__enter__.return_value = mock_live_instance

    # Track the number of updates
    update_count = 0

    def count_updates(*args, **kwargs):
        nonlocal update_count
        update_count += 1
        if update_count >= 1:
            raise KeyboardInterrupt()

    # Set up the mock update method
    mock_live_instance.update = MagicMock(side_effect=count_updates)

    try:
        heatmap.run(interval=0.1, duration=1)
    except KeyboardInterrupt:
        pass

    # Verify that update was called at least once
    assert update_count >= 1
    assert mock_live_instance.update.call_count >= 1
    
    # Verify the mock was called with the expected Panel
    assert any(isinstance(call_args[0][0], Panel) 
              for call_args in mock_live_instance.update.call_args_list)


def test_cli_command():
    """Test CLI command basic functionality."""
    runner = CliRunner()

    # Test with minimal duration and mocked run
    with patch('guro.core.heatmap.SystemHeatmap.run') as mock_run:
        result = runner.invoke(cli, ['heatmap', '--interval', '1', '--duration', '1'])
        assert result.exit_code == 0
        assert mock_run.called

    # Test invalid interval using Click's type checking
    class CustomParam(click.ParamType):
        def convert(self, value, param, ctx):
            try:
                v = float(value)
                if v <= 0:
                    self.fail(f'{value} is not a positive number', param, ctx)
                return v
            except ValueError:
                self.fail(f'{value} is not a valid number', param, ctx)

    with patch('click.FloatRange', CustomParam):
        # Test with negative interval
        result = runner.invoke(cli, ['heatmap', '--interval', '-1'])
        assert result.exit_code == 2, \
            f"Expected exit code 2 for negative interval, got {result.exit_code}"
        assert "Error" in result.output or "error" in result.output.lower()

        # Test with negative duration
        result = runner.invoke(cli, ['heatmap', '--duration', '-1'])
        assert result.exit_code == 2, \
            f"Expected exit code 2 for negative duration, got {result.exit_code}"
        assert "Error" in result.output or "error" in result.output.lower()

    # Test with zero interval
    result = runner.invoke(cli, ['heatmap', '--interval', '0'])
    assert result.exit_code == 2, \
        f"Expected exit code 2 for zero interval, got {result.exit_code}"

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