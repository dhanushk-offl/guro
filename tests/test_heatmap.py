# test_heatmap.py
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import platform
from guro.core.heatmap import SystemHeatmap

class TestSystemHeatmap(unittest.TestCase):
    def setUp(self):
        self.heatmap = SystemHeatmap()

    def test_init(self):
        """Test initialization of SystemHeatmap."""
        self.assertEqual(self.heatmap.history_size, 60)
        self.assertEqual(self.heatmap.current_index, 0)
        self.assertIsNotNone(self.heatmap.cpu_history)
        self.assertIsNotNone(self.heatmap.gpu_history)

    @patch('platform.system')
    @patch('psutil.cpu_count')
    def test_get_cpu_temps_linux(self, mock_cpu_count, mock_platform):
        """Test CPU temperature retrieval on Linux."""
        mock_platform.return_value = "Linux"
        mock_cpu_count.return_value = 4

        with patch('psutil.sensors_temperatures') as mock_temps:
            mock_temps.return_value = {
                'coretemp': [
                    MagicMock(current=45.0),
                    MagicMock(current=46.0),
                    MagicMock(current=47.0),
                    MagicMock(current=48.0)
                ]
            }
            temps = self.heatmap.get_cpu_temps()
            self.assertEqual(len(temps), 4)
            self.assertEqual(temps, [45.0, 46.0, 47.0, 48.0])

    def test_get_temp_color(self):
        """Test temperature to color conversion."""
        self.assertEqual(self.heatmap.get_temp_color(45), "green")
        self.assertEqual(self.heatmap.get_temp_color(65), "yellow")
        self.assertEqual(self.heatmap.get_temp_color(80), "red")

    @patch('platform.system')
    def test_get_gpu_count_windows(self, mock_platform):
        """Test GPU count retrieval on Windows."""
        mock_platform.return_value = "Windows"
        with patch('wmi.WMI') as mock_wmi:
            mock_wmi.return_value.Win32_VideoController.return_value = [MagicMock(), MagicMock()]
            self.assertEqual(self.heatmap.get_gpu_count(), 2)

    def test_update_histories(self):
        """Test history update functionality."""
        with patch.object(self.heatmap, 'get_cpu_temps') as mock_cpu_temps:
            with patch.object(self.heatmap, 'get_gpu_temps') as mock_gpu_temps:
                mock_cpu_temps.return_value = [50.0] * 4
                mock_gpu_temps.return_value = [60.0] * 2
                
                self.heatmap.update_histories()
                
                self.assertEqual(self.heatmap.cpu_history[:, 0].tolist(), [50.0] * 4)
                self.assertEqual(self.heatmap.gpu_history[:, 0].tolist(), [60.0] * 2)

    def test_generate_heatmap_table(self):
        """Test heatmap table generation."""
        table = self.heatmap.generate_heatmap_table()
        self.assertIsNotNone(table)

if __name__ == '__main__':
    unittest.main()