# tests/test_optimizer.py
from unittest import TestCase
from guro.core.optimizer import SystemOptimizer

class TestOptimizer(TestCase):
    def setUp(self):
        self.optimizer = SystemOptimizer()

    def test_optimize_cpu(self):
        result = self.optimizer.optimize_cpu()
        self.assertIsInstance(result, bool)