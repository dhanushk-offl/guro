# tests/test_monitor.py
from unittest import TestCase
from guro.core.monitor import SystemMonitor

class TestMonitor(TestCase):
    def setUp(self):
        self.monitor = SystemMonitor()

    def test_get_cpu_info(self):
        info = self.monitor.get_cpu_info()
        self.assertIsInstance(info, dict)
        self.assertIn('percent', info)