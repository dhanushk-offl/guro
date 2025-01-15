import pytest
from unittest.mock import Mock, patch
import numpy as np
import platform
import psutil
from rich.panel import Panel
from rich.text import Text
import time
from pathlib import Path
from rich.console import Console
from guro.core.heatmap import SystemHeatmap

# Add fixtures for commonly used objects
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
    (45.0, '▒', "yellow"),  # Added edge case
    (90.0, '█', "red"),     # Added edge case
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
    
    # Check if the temperature map has the correct shape
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
    assert "System Temperature Heatmap" in layout.title
    # Add more specific assertions about layout content
    assert isinstance(layout.renderable, Text)

@pytest.mark.parametrize("interval,duration", [
    (1.0, 3),  # Normal case
    (0.5, 2),  # Faster updates
    (2.0, 4),  # Slower updates
])
def test_heatmap_run_duration(heatmap, mock_system_temps, interval, duration):
    start_time = time.time()
    
    with patch.object(heatmap, 'get_system_temps', return_value=mock_system_temps):
        update_count = heatmap.run(interval=interval, duration=duration)
    
    elapsed_time = time.time() - start_time
    assert duration - 0.1 <= elapsed_time <= duration + 1.0
    expected_updates = duration / interval
    assert abs(update_count - expected_updates) <= 2

@pytest.mark.parametrize("system_name", ["Windows", "Linux", "Darwin"])
def test_system_specific_temperatures(system_name):
    if system_name != platform.system():
        pytest.skip(f"Skipping {system_name}-specific test on {platform.system()}")
    
    with patch('platform.system', return_value=system_name):
        heatmap = SystemHeatmap()
        temps = heatmap.get_system_temps()
        
        assert isinstance(temps, dict)
        assert set(temps.keys()) == set(['CPU', 'GPU', 'Motherboard', 'RAM', 'Storage'])
        assert all(isinstance(temp, float) for temp in temps.values())
        assert all(0 <= temp <= 100 for temp in temps.values())

@pytest.mark.parametrize("invalid_input,expected_error", [
    ((-1, 1.0), ValueError),   # Invalid duration
    ((5, 0), ValueError),      # Invalid interval
    ((5, -0.5), ValueError),   # Invalid interval
])
def test_invalid_inputs(heatmap, invalid_input, expected_error):
    duration, interval = invalid_input
    with pytest.raises(expected_error):
        heatmap.run(interval=interval, duration=duration)

# Add cleanup in case of resource usage
@pytest.fixture(autouse=True)
def cleanup():
    yield
    

if __name__ == '__main__':
    pytest.main(['-v', __file__])