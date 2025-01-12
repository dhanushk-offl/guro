import unittest
from unittest.mock import Mock, patch
import numpy as np
import psutil
import platform
from rich.console import Console
from rich.table import Table

# Import the class to test
from guro.core.benchmark import SafeSystemBenchmark

class TestSafeSystemBenchmark(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.benchmark = SafeSystemBenchmark()
        
    def test_initialization(self):
        """Test proper initialization of benchmark instance"""
        self.assertIsInstance(self.benchmark.console, Console)
        self.assertIsInstance(self.benchmark.results, dict)
        self.assertFalse(self.benchmark.running)
        self.assertLessEqual(self.benchmark.MAX_CPU_USAGE, 100)
        self.assertLessEqual(self.benchmark.MAX_MEMORY_USAGE, 100)
        
    @patch('GPUtil.getGPUs')
    def test_check_gpu_with_gpu(self, mock_getGPUs):
        """Test GPU detection when GPU is available"""
        mock_gpu = Mock()
        mock_gpu.name = "Test GPU"
        mock_gpu.memoryTotal = 8192
        mock_gpu.driver = "123.45"
        mock_getGPUs.return_value = [mock_gpu]
        
        gpu_info = self.benchmark._check_gpu()
        self.assertTrue(gpu_info['available'])
        self.assertEqual(gpu_info['info']['name'], "Test GPU")
        self.assertEqual(gpu_info['info']['count'], 1)
        
    @patch('GPUtil.getGPUs')
    def test_check_gpu_without_gpu(self, mock_getGPUs):
        """Test GPU detection when no GPU is available"""
        mock_getGPUs.return_value = []
        
        gpu_info = self.benchmark._check_gpu()
        self.assertFalse(gpu_info['available'])
        self.assertIsNone(gpu_info['info'])
        
    def test_get_system_info(self):
        """Test system information gathering"""
        system_info = self.benchmark.get_system_info()
        
        self.assertEqual(system_info['system'], platform.system())
        self.assertEqual(system_info['processor'], platform.processor())
        self.assertEqual(system_info['cpu_cores'], psutil.cpu_count(logical=False))
        self.assertEqual(system_info['cpu_threads'], psutil.cpu_count(logical=True))
        self.assertIsInstance(system_info['gpu'], dict)
        
    @patch('time.sleep', return_value=None)
    def test_safe_cpu_test(self, mock_sleep):
        """Test CPU benchmark functionality"""
        duration = 1
        result = self.benchmark.safe_cpu_test(duration)
        
        self.assertIn('times', result)
        self.assertIn('loads', result)
        self.assertIsInstance(result['times'], list)
        self.assertIsInstance(result['loads'], list)
        
    @patch('time.sleep', return_value=None)
    def test_safe_memory_test(self, mock_sleep):
        """Test memory benchmark functionality"""
        duration = 1
        result = self.benchmark.safe_memory_test(duration)
        
        self.assertIn('times', result)
        self.assertIn('usage', result)
        self.assertIsInstance(result['times'], list)
        self.assertIsInstance(result['usage'], list)
        
    @patch('GPUtil.getGPUs')
    @patch('time.sleep', return_value=None)
    def test_safe_gpu_test_with_gpu(self, mock_sleep, mock_getGPUs):
        """Test GPU benchmark when GPU is available"""
        mock_gpu = Mock()
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 4096
        mock_getGPUs.return_value = [mock_gpu]
        
        self.benchmark.has_gpu['available'] = True
        duration = 1
        result = self.benchmark.safe_gpu_test(duration)
        
        self.assertIn('times', result)
        self.assertIn('loads', result)
        self.assertIn('memory_usage', result)
        self.assertIsInstance(result['times'], list)
        self.assertIsInstance(result['loads'], list)
        self.assertIsInstance(result['memory_usage'], list)
        
    def test_safe_gpu_test_without_gpu(self):
        """Test GPU benchmark when no GPU is available"""
        self.benchmark.has_gpu['available'] = False
        duration = 1
        result = self.benchmark.safe_gpu_test(duration)
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'No GPU available')
        
    def test_generate_status_table(self):
        """Test status table generation"""
        table = self.benchmark.generate_status_table()
        
        self.assertIsInstance(table, Table)
        self.assertEqual(table.title, "Benchmark Status")
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_monitor_resources_safety_threshold(self, mock_memory, mock_cpu):
        """Test resource monitoring safety thresholds"""
        mock_cpu.return_value = 90  # Above MAX_CPU_USAGE
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60
        mock_memory.return_value = mock_memory_obj
        
        self.benchmark.running = True
        self.benchmark.monitor_resources()
        
        self.assertFalse(self.benchmark.running)
        
    @patch('rich.live.Live')
    def test_mini_test(self, mock_live):
        """Test mini benchmark execution"""
        self.benchmark.mini_test()
        self.assertIn('system_info', self.benchmark.results)
        self.assertEqual(self.benchmark.results['duration'], 30)
        
    @patch('rich.live.Live')
    def test_god_test(self, mock_live):
        """Test god-level benchmark execution"""
        self.benchmark.god_test()
        self.assertIn('system_info', self.benchmark.results)
        self.assertEqual(self.benchmark.results['duration'], 60)

if __name__ == '__main__':
    unittest.main(verbosity=2)