import unittest
from unittest.mock import patch, MagicMock
import platform
import psutil
import numpy as np
from pathlib import Path
import subprocess
from rich.panel import Panel
from rich.text import Text

from guro.core.heatmap import SystemHeatmap

class TestSystemHeatmap(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.heatmap = SystemHeatmap()

    def tearDown(self):
        """Clean up after each test method."""
        if hasattr(self, 'heatmap'):
            del self.heatmap

    def test_initialization(self):
        """Test proper initialization of SystemHeatmap."""
        self.assertIsNotNone(self.heatmap.console)
        self.assertEqual(self.heatmap.history_size, 60)
        self.assertIsInstance(self.heatmap.components, dict)
        self.assertIn('CPU', self.heatmap.components)
        self.assertIn('GPU', self.heatmap.components)
        self.assertIsInstance(self.heatmap.temp_maps, dict)

    @patch('platform.system')
    def test_windows_setup(self, mock_system):
        """Test Windows-specific setup."""
        mock_system.return_value = "Windows"
        heatmap = SystemHeatmap()
        if platform.system() == "Windows":
            self.assertTrue(hasattr(heatmap, 'GetSystemPowerStatus'))
            self.assertTrue(hasattr(heatmap, 'NtQuerySystemInformation'))

    def test_temp_maps_initialization(self):
        """Test temperature maps initialization."""
        for component, temp_map in self.heatmap.temp_maps.items():
            expected_shape = self.heatmap.components[component]['size']
            self.assertEqual(temp_map.shape, expected_shape)
            self.assertTrue(np.all(temp_map == 0))

    @patch('psutil.cpu_percent')
    def test_get_cpu_load_temp(self, mock_cpu_percent):
        """Test CPU load temperature calculation."""
        mock_cpu_percent.return_value = 50.0
        temp = self.heatmap.get_cpu_load_temp()
        self.assertIsInstance(temp, float)
        self.assertEqual(temp, 40 + (50.0 * 0.6))

    @patch('psutil.cpu_percent')
    def test_get_gpu_load_temp(self, mock_cpu_percent):
        """Test GPU load temperature calculation."""
        mock_cpu_percent.return_value = 50.0
        temp = self.heatmap.get_gpu_load_temp()
        self.assertIsInstance(temp, float)
        self.assertEqual(temp, 35 + (50.0 * 0.5))

    @patch('psutil.disk_io_counters')
    def test_get_disk_load_temp(self, mock_disk_io):
        """Test disk load temperature calculation."""
        mock_disk_io.return_value = MagicMock(
            read_bytes=1024**3,  # 1 GB
            write_bytes=1024**3  # 1 GB
        )
        temp = self.heatmap.get_disk_load_temp()
        self.assertIsInstance(temp, float)
        self.assertGreater(temp, 30.0)

    def test_get_temp_char(self):
        """Test temperature character and color mapping."""
        # Test cold temperature
        char, color = self.heatmap.get_temp_char(40)
        self.assertEqual(char, '·')
        self.assertEqual(color, "green")

        # Test warm temperature
        char, color = self.heatmap.get_temp_char(60)
        self.assertEqual(char, '▒')
        self.assertEqual(color, "yellow")

        # Test hot temperature
        char, color = self.heatmap.get_temp_char(80)
        self.assertEqual(char, '█')
        self.assertEqual(color, "red")

    @patch('platform.system')
    @patch('subprocess.check_output')
    def test_linux_temps(self, mock_subprocess, mock_system):
        """Test Linux temperature detection."""
        mock_system.return_value = "Linux"
        mock_subprocess.return_value = b"50\n"
        
        # Mock psutil sensors
        with patch('psutil.sensors_temperatures') as mock_sensors:
            mock_sensors.return_value = {
                'coretemp': [MagicMock(current=50.0)],
                'acpitz': [MagicMock(current=45.0)]
            }
            
            temps = self.heatmap.get_linux_temps()
            self.assertIsInstance(temps, dict)
            self.assertIn('CPU', temps)
            self.assertIn('GPU', temps)
            self.assertIn('Motherboard', temps)

    def test_update_component_map(self):
        """Test component temperature map updates."""
        component = 'CPU'
        test_temp = 50.0
        
        self.heatmap.update_component_map(component, test_temp)
        temp_map = self.heatmap.temp_maps[component]
        
        # Check if the map has been updated with noise
        self.assertFalse(np.all(temp_map == 0))
        self.assertTrue(np.all(temp_map >= 0))
        self.assertTrue(np.all(temp_map <= 100))

    def test_generate_system_layout(self):
        """Test system layout generation."""
        # Test layout generation
        layout = self.heatmap.generate_system_layout()
        self.assertIsInstance(layout, Panel)
        self.assertIn("System Temperature Heatmap", layout.title)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_fallback_temps(self, mock_memory, mock_cpu):
        """Test fallback temperature calculations."""
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        
        temps = self.heatmap.get_fallback_temps()
        self.assertIsInstance(temps, dict)
        self.assertIn('CPU', temps)
        self.assertIn('GPU', temps)
        self.assertIn('Motherboard', temps)
        self.assertIn('Storage', temps)
        self.assertIn('RAM', temps)

    @patch('time.sleep', return_value=None)
    @patch('time.time')
    def test_run_with_duration(self, mock_time, mock_sleep):
        """Test run method with duration."""
        mock_time.side_effect = [0, 1, 2, 3]  # Simulate time passing
        
        # Test run with 2 second duration
        with patch('rich.live.Live'):
            self.heatmap.run(interval=1.0, duration=2)
            self.assertEqual(mock_sleep.call_count, 2)

    def test_cli_command_error_handling(self):
        """Test CLI command error handling."""
        from click.testing import CliRunner
        from system_heatmap import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['heatmap', '--interval', '-1'])
        self.assertNotEqual(result.exit_code, 0)

if __name__ == '__main__':
    unittest.main()