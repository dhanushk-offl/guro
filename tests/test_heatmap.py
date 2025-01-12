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
    assert isinstance(heatmap.temp_maps, dict)

@patch('platform.system')
def test_windows_setup(mock_system):
    """Test Windows-specific setup."""
    mock_system.return_value = "Windows"
    with patch('ctypes.windll') as mock_windll:
        # Mock the Windows API calls
        mock_windll.kernel32.GetSystemPowerStatus = MagicMock()
        mock_windll.ntdll.NtQuerySystemInformation = MagicMock()
        mock_windll.powrprof.CallNtPowerInformation = MagicMock()
        
        heatmap = SystemHeatmap()
        if platform.system() == "Windows":
            assert hasattr(heatmap, 'GetSystemPowerStatus')
            assert hasattr(heatmap, 'NtQuerySystemInformation')

@patch('time.sleep', return_value=None)
@patch('time.time')
def test_run_with_duration(mock_time, mock_sleep, heatmap):
    """Test run method with duration."""
    mock_time.side_effect = [0, 1, 2, 3]  # Simulate time passing
    
    with patch('rich.live.Live'):
        update_count = heatmap.run(interval=1.0, duration=2)
        assert update_count == 2  # Verify two updates occurred

def test_cli_command_error_handling():
    """Test CLI command error handling."""
    runner = CliRunner()
    result = runner.invoke(cli, ['heatmap', '--interval', '-1'])
    assert result.exit_code == 2  # Changed to expect exit code 2 for invalid input