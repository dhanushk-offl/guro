# tests/test_monitor.py
import unittest
from unittest.mock import patch, MagicMock
import platform
import psutil
import subprocess
from datetime import datetime
import os
import sys
from typing import Dict, List

# Import your classes
from guro.core.monitor import SystemMonitor, GPUDetector, ASCIIGraph

class TestSystemMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.monitor = SystemMonitor()

    def tearDown(self):
        """Clean up after each test method."""
        if hasattr(self, 'monitor'):
            del self.monitor

    @patch('psutil.cpu_freq')
    @patch('psutil.cpu_count')
    def test_get_system_info(self, mock_cpu_count, mock_cpu_freq):
        """Test system information retrieval"""
        # Mock CPU frequency
        mock_freq = MagicMock()
        mock_freq.current = 2400.0
        mock_cpu_freq.return_value = mock_freq
        
        # Mock CPU count
        mock_cpu_count.return_value = 8
        
        info = self.monitor.get_system_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn('os', info)
        self.assertIn('cpu_cores', info)
        self.assertIn('cpu_threads', info)
        self.assertIn('cpu_freq', info)
        self.assertIn('memory_total', info)
        self.assertIn('memory_available', info)

    @patch('subprocess.check_output')
    def test_nvidia_gpu_detection(self, mock_check_output):
        """Test NVIDIA GPU detection"""
        mock_output = "GeForce RTX 3080,10240,5120,5120,65,50,75,200"
        mock_check_output.return_value = mock_output
        
        gpu_info = GPUDetector.get_nvidia_info()
        
        self.assertIsInstance(gpu_info, list)
        if gpu_info:  # If GPU is detected
            self.assertIn('name', gpu_info[0])
            self.assertIn('memory_total', gpu_info[0])
            self.assertIn('temperature', gpu_info[0])
            self.assertEqual(gpu_info[0]['type'], 'NVIDIA')

    @patch('subprocess.check_output')
    def test_amd_gpu_detection(self, mock_check_output):
        """Test AMD GPU detection"""
        mock_output = """
        GPU 0: Card Series
        GPU Memory Use: 4096 MB
        Total GPU Memory: 8192 MB
        Temperature: 70 C
        """
        mock_check_output.return_value = mock_output
        
        gpu_info = GPUDetector.get_amd_info()
        
        self.assertIsInstance(gpu_info, list)
        if gpu_info:  # If GPU is detected
            self.assertIn('memory_total', gpu_info[0])
            self.assertIn('temperature', gpu_info[0])
            self.assertEqual(gpu_info[0]['type'], 'AMD')

    def test_ascii_graph(self):
        """Test ASCII graph generation"""
        graph = ASCIIGraph(width=50, height=10)
        
        # Test adding points
        test_values = [0, 25, 50, 75, 100]
        for value in test_values:
            graph.add_point(value)
        
        # Test rendering
        rendered = graph.render("Test Graph")
        self.assertIsInstance(rendered, str)
        self.assertGreater(len(rendered), 0)

    @patch('psutil.virtual_memory')
    def test_performance_monitoring(self, mock_virtual_memory):
        """Test performance monitoring functionality"""
        # Mock memory info
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024**3  # 16GB
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory

        # Test monitoring data collection
        self.monitor.monitoring_data = []
        self.monitor.run_performance_test(interval=0.1, duration=1, export_data=True)
        
        self.assertTrue(os.path.exists('monitoring_data.csv'))
        self.assertGreater(len(self.monitor.monitoring_data), 0)
        
        # Clean up test file
        if os.path.exists('monitoring_data.csv'):
            os.remove('monitoring_data.csv')

    def test_cpu_temperature_linux(self):
        """Test CPU temperature reading on Linux"""
        if platform.system() == 'Linux':
            temp = self.monitor._get_cpu_temperature()
            if temp is not None:  # Temperature might not be available on all systems
                self.assertIsInstance(temp, float)
                self.assertGreaterEqual(temp, 0)
                self.assertLess(temp, 150)  # Reasonable temperature range

    @patch('platform.system')
    @patch('platform.release')
    @patch('platform.processor')
    def test_system_detection(self, mock_processor, mock_release, mock_system):
        """Test system detection across different platforms"""
        # Test for Linux
        mock_system.return_value = 'Linux'
        mock_release.return_value = '5.10.0'
        mock_processor.return_value = 'x86_64'
        
        info = self.monitor.get_system_info()
        self.assertIn('Linux', info['os'])
        
        # Test for Windows
        mock_system.return_value = 'Windows'
        mock_release.return_value = '10'
        info = self.monitor.get_system_info()
        self.assertIn('Windows', info['os'])

    def test_error_handling(self):
        """Test error handling in critical sections"""
        # Test GPU detection with no GPUs
        gpu_info = GPUDetector.get_all_gpus()
        self.assertIsInstance(gpu_info, dict)
        self.assertIn('available', gpu_info)
        self.assertIn('gpus', gpu_info)

        # Test graph rendering with no data
        graph = ASCIIGraph()
        rendered = graph.render()
        self.assertEqual(rendered, "")

if __name__ == '__main__':
    unittest.main()