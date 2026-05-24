import pytest
from unittest.mock import Mock, patch
import numpy as np
import platform
import psutil
from rich.panel import Panel
from rich.text import Text
import time
import tempfile
import os
from pathlib import Path
from rich.console import Console
from guro.core.heatmap import SystemHeatmap


@pytest.fixture
def heatmap():
    return SystemHeatmap()


@pytest.fixture
def mock_system_temps():
    return {
        'CPU': 45.0,
        'GPU': 55.0,
        'Motherboard': 40.0,
        'RAM': 35.0,
        'Storage': 30.0
    }


def test_system_heatmap_initialization(heatmap):
    assert isinstance(heatmap.console, Console)
    assert heatmap.history_size == 60
    assert heatmap.system == platform.system()
    assert all(component in heatmap.components for component in ['CPU', 'GPU', 'Motherboard', 'RAM', 'Storage'])


@pytest.mark.parametrize("temperature,expected_char,expected_color", [
    (30.0, '·', "green"),
    (60.0, '▒', "yellow"),
    (80.0, '█', "red"),
    (45.0, '▒', "yellow"),  # Edge case: exactly 45
    (90.0, '█', "red"),     # Edge case: high temp
])
def test_temperature_character_mapping(heatmap, temperature, expected_char, expected_color):
    char, color = heatmap.get_temp_char(temperature)
    assert char == expected_char
    assert color == expected_color


def test_temperature_map_update(heatmap):
    component = 'CPU'
    test_temp = 50.0

    heatmap.update_component_map(component, test_temp)
    temp_map = heatmap.temp_maps[component]

    expected_shape = heatmap.components[component]['size']
    assert temp_map.shape == expected_shape

    # Check if the mean temperature is close to the input temperature
    assert np.isclose(np.mean(temp_map), test_temp, atol=5.0)


@patch('psutil.cpu_percent')
@patch('psutil.virtual_memory')
def test_fallback_temperatures(mock_virtual_memory, mock_cpu_percent, heatmap):
    mock_cpu_percent.return_value = 50.0
    mock_virtual_memory.return_value = Mock(percent=60.0)

    temps = heatmap.get_fallback_temps()

    assert isinstance(temps, dict)
    assert set(temps.keys()) == set(['CPU', 'GPU', 'Motherboard', 'RAM', 'Storage'])
    assert all(isinstance(temp, float) for temp in temps.values())
    assert all(0 <= temp <= 100 for temp in temps.values())


def test_system_layout_generation(heatmap):
    layout = heatmap.generate_system_layout()

    assert isinstance(layout, Panel)
    assert "Internal Thermal Map" in layout.title
    assert isinstance(layout.renderable, Text)


def test_heatmap_run_duration(heatmap, mock_system_temps):
    """Test heatmap run with mocked system temps and short durations."""
    duration = 2
    interval = 0.5

    with patch.object(heatmap, 'get_system_temps', return_value=mock_system_temps), \
         patch('guro.core.heatmap.Live'):
        update_count = heatmap.run(interval=interval, duration=duration)

    assert update_count >= 1


def test_invalid_inputs(heatmap):
    """Test that invalid inputs raise ValueError."""
    with pytest.raises(ValueError):
        heatmap.run(interval=0)
    with pytest.raises(ValueError):
        heatmap.run(interval=-0.5)
    with pytest.raises(ValueError):
        heatmap.run(duration=0)
    with pytest.raises(ValueError):
        heatmap.run(duration=-1)


def test_parse_sensor_temp():
    """Test the static method for parsing lm-sensors temperature strings."""
    assert SystemHeatmap._parse_sensor_temp('+45.0°C') == 45.0
    assert SystemHeatmap._parse_sensor_temp('+65.5°C') == 65.5
    assert SystemHeatmap._parse_sensor_temp('  +72.3°C  ') == 72.3
    assert SystemHeatmap._parse_sensor_temp('N/A') is None
    assert SystemHeatmap._parse_sensor_temp('') is None
