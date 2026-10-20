"""Bounded CPU and memory workloads with explicit measurement and stop outcomes."""
import platform
import os
from contextlib import nullcontext
from rich.text import Text
import threading
import time
from typing import Dict

import numpy as np
import psutil
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .heatmap import SystemHeatmap
from .monitor import GPUDetector


class SafeSystemBenchmark:
    def __init__(self):
        self.console = Console()
        self.results: Dict = {}
        self._stop_event = threading.Event()
        self.MAX_MEMORY_USAGE = 90
        self.MAX_TEMPERATURE = 90
        self.MAX_BUFFER_BYTES = 32 * 1024 * 1024
        self.has_gpu = self._check_gpu()
        self._thermal = SystemHeatmap()
        self.stop_reason = None
        self._last_check = float('-inf')
        self._live = None
        self.phase = 'idle'

    @property
    def running(self):
        return not self._stop_event.is_set()

    @running.setter
    def running(self, value):
        self._stop_event.clear() if value else self._stop_event.set()

    def _check_gpu(self):
        return GPUDetector.get_all_gpus()

    def get_system_info(self):
        return {
            'system': platform.system(), 'processor': platform.processor(),
            'memory_total': psutil.virtual_memory().total,
            'cpu_cores': psutil.cpu_count(logical=False),
            'cpu_threads': psutil.cpu_count(logical=True),
            'gpus': self.has_gpu['gpus'],
        }

    def safe_gpu_test(self, duration):
        return {'status': 'unsupported', 'error': 'GPU workloads are not implemented; use guro gpu for telemetry.'}

    def _check_safety(self):
        memory = psutil.virtual_memory()
        if memory.percent >= self.MAX_MEMORY_USAGE:
            self.stop_reason = 'Memory usage reached the configured limit'
        readings = self._thermal.get_readings()
        for component, reading in readings.items():
            if reading.available and reading.source != 'estimate' and reading.value >= self.MAX_TEMPERATURE:
                self.stop_reason = f'{component} temperature reached {reading.value:.1f} Celsius'
        self.results['thermal_monitoring'] = {
            component: reading.to_dict() for component, reading in readings.items()
        }
        # Not all devices expose sensors. Report coverage instead of inventing data.
        if self.stop_reason:
            self._stop_event.set()
        return self.running

    def _tick(self):
        now = time.monotonic()
        if now - self._last_check >= 0.25:
            self._last_check = now
            self._check_safety()
            if self._live:
                self._live.update(self.generate_status_table())
        return self.running

    def monitor_resources(self):
        while self.running:
            self._check_safety()
            self._stop_event.wait(0.25)

    def safe_cpu_test(self, duration):
        # Allocation and random generation are excluded from the timed workload.
        size = 256
        matrix = np.random.RandomState(0).rand(size, size)
        target = np.empty_like(matrix)
        start = time.perf_counter()
        iterations = 0
        compute_seconds = 0.0
        while time.perf_counter() - start < duration and self._tick():
            operation_start = time.perf_counter()
            np.dot(matrix, matrix.T, out=target)
            compute_seconds += time.perf_counter() - operation_start
            iterations += 1
        elapsed = time.perf_counter() - start
        return {
            'status': 'completed' if self.running else 'aborted',
            'duration': elapsed, 'iterations': iterations, 'matrix_size': size,
            'gflops': (iterations * 2 * size ** 3 / max(compute_seconds, 1e-9)) / 1e9,
            'compute_seconds': compute_seconds,
            'seed': 0, 'numpy_version': np.__version__,
        }

    def safe_memory_test(self, duration):
        memory = psutil.virtual_memory()
        # Budget includes both source and destination and is checked before allocation.
        budget = min(self.MAX_BUFFER_BYTES, int(memory.available * 0.01))
        if memory.percent >= self.MAX_MEMORY_USAGE or budget < 2 * 1024 * 1024:
            self.stop_reason = 'Insufficient available memory for the bounded workload'
            self.running = False
            return {'status': 'aborted', 'duration': 0, 'bandwidth_mbps': 0}
        size = budget // 2 // 8
        try:
            source = np.ones(size, dtype=np.float64)
            target = np.empty_like(source)
            target.fill(0)
            start = time.perf_counter()
            copied = 0
            iterations = 0
            copy_seconds = 0.0
            while time.perf_counter() - start < duration and self._tick():
                operation_start = time.perf_counter()
                np.copyto(target, source)
                copy_seconds += time.perf_counter() - operation_start
                copied += source.nbytes
                iterations += 1
            elapsed = time.perf_counter() - start
            return {
                'status': 'completed' if self.running else 'aborted',
                'duration': elapsed, 'iterations': iterations,
                'buffer_bytes': source.nbytes + target.nbytes,
                'bytes_copied': copied,
                'bandwidth_mbps': copied / max(copy_seconds, 1e-9) / 1e6,
                'copy_seconds': copy_seconds,
            }
        except MemoryError:
            self.stop_reason = 'Memory allocation failed'
            self.running = False
            return {'status': 'aborted', 'duration': 0, 'bandwidth_mbps': 0}

    def _run(self, duration, gpu_only=False, cpu_only=False, display=True):
        if gpu_only and cpu_only:
            raise ValueError('Use only one of --gpu-only or --cpu-only')
        self.running = True
        self.stop_reason = None
        self._last_check = float('-inf')
        self.results = {
            'system_info': self.get_system_info(), 'requested_duration': duration,
            'configuration': {'memory_budget_bytes': self.MAX_BUFFER_BYTES,
                              'max_memory_percent': self.MAX_MEMORY_USAGE,
                              'max_temperature_celsius': self.MAX_TEMPERATURE,
                              'blas_thread_environment': {key: os.environ.get(key) for key in
                                  ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}},
            'status': 'running',
        }
        start = time.monotonic()
        try:
            if gpu_only:
                self.results['gpu'] = self.safe_gpu_test(duration)
                self.results['status'] = 'unsupported'
            else:
                # Both phases share one total duration. GPU observation adds no time.
                with (Live(self.generate_status_table(), refresh_per_second=4) if display else nullcontext()) as live:
                    self._live = live if display else None
                    self._check_safety()
                    self._last_check = time.monotonic()
                    if self.running:
                        self.phase = 'cpu'
                        cpu_budget = duration if cpu_only else duration / 2
                        self.results['cpu'] = self.safe_cpu_test(max(0, cpu_budget - (time.monotonic() - start)))
                    if self.running and not cpu_only:
                        self.phase = 'memory'
                        remaining = max(0, duration - (time.monotonic() - start))
                        self.results['memory'] = self.safe_memory_test(remaining)
                    if not cpu_only:
                        self.results['gpu'] = self.safe_gpu_test(0)
                self.results['status'] = 'completed' if self.running else 'aborted'
        except KeyboardInterrupt:
            self.results['status'] = 'cancelled'
            self.stop_reason = 'Interrupted by user'
            raise
        except Exception:
            self.results['status'] = 'failed'
            raise
        finally:
            self._live = None
            self.running = False
            self.phase = 'idle'
            self.results['duration'] = time.monotonic() - start
            self.results['stop_reason'] = self.stop_reason
        if display:
            self.display_results('Benchmark')
        return self.results

    def mini_test(self, gpu_only=False, cpu_only=False, display=True):
        return self._run(30, gpu_only, cpu_only, display)

    def god_test(self, gpu_only=False, cpu_only=False, display=True):
        return self._run(60, gpu_only, cpu_only, display)

    def generate_status_table(self):
        table = Table(title='Benchmark Status')
        table.add_column('Metric')
        table.add_column('Value')
        table.add_row('Phase', self.phase)
        table.add_row('Memory usage', f'{psutil.virtual_memory().percent:.1f}%')
        table.add_row('Status', self.stop_reason or self.results.get('status', 'idle'))
        return table

    def display_results(self, test_type):
        lines = [f"Status: {self.results['status']}", f"Elapsed: {self.results['duration']:.2f} seconds"]
        if self.stop_reason:
            lines.append(self.stop_reason)
        if 'cpu' in self.results:
            lines.append(f"CPU: {self.results['cpu'].get('gflops', 0):.2f} GFLOP/s (NumPy/BLAS)")
        if 'memory' in self.results:
            lines.append(f"Memory copy: {self.results['memory']['bandwidth_mbps']:.2f} MB/s")
        if 'gpu' in self.results:
            lines.append(self.results['gpu']['error'])
        coverage = self.results.get('thermal_monitoring', {})
        monitored = [c for c, r in coverage.items() if r['available']]
        lines.append('Temperature sensors: ' + (', '.join(monitored) or 'unavailable'))
        self.console.print(Panel(Text('\n'.join(lines)), title=test_type))
