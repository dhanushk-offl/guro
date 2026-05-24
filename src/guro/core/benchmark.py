import time
import logging
import threading
import numpy as np
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

import psutil
import platform

try:
    import GPUtil
    HAS_GPU_STATS = True
except ImportError:
    HAS_GPU_STATS = False

logger = logging.getLogger(__name__)


class SafeSystemBenchmark:
    def __init__(self):
        self.console = Console()
        self.results: Dict = {}
        self._stop_event = threading.Event()
        # Safety thresholds — these are for *monitoring*, not for killing benchmarks
        self.MAX_CPUSAFE = 98        # 98% CPU is reasonable during a benchmark
        self.MAX_MEMORY_USAGE = 95    # 95% memory before we worry
        self.has_gpu = self._check_gpu()

    @property
    def running(self) -> bool:
        return not self._stop_event.is_set()

    @running.setter
    def running(self, value: bool):
        if value:
            self._stop_event.clear()
        else:
            self._stop_event.set()

    def _check_gpu(self) -> Dict:
        """Check if GPU is available and get GPU information"""
        gpu_info: Dict = {'available': False, 'gpus': []}

        if HAS_GPU_STATS:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_info['available'] = True
                    for gpu in gpus:
                        gpu_info['gpus'].append({
                            'name': gpu.name,
                            'memory_total': gpu.memoryTotal,
                            'driver_version': gpu.driver
                        })
            except Exception:
                logger.exception("Error checking GPU availability")
        return gpu_info

    def get_system_info(self) -> Dict:
        """Get basic system information"""
        info: Dict = {
            'system': platform.system(),
            'processor': platform.processor(),
            'memory_total': psutil.virtual_memory().total,
            'cpu_cores': psutil.cpu_count(logical=False),
            'cpu_threads': psutil.cpu_count(logical=True),
            'gpus': self.has_gpu['gpus'] if self.has_gpu['available'] else []
        }
        return info

    def safe_gpu_test(self, duration: float) -> Dict:
        """Safe GPU benchmark with controlled load for all GPUs"""
        if not self.has_gpu['available']:
            return {'times': [], 'loads': [], 'error': 'No GPU available'}

        result: Dict = {'times': [], 'gpu_stats': []}
        start_time = time.time()

        try:
            while time.time() - start_time < duration and not self._stop_event.is_set():
                if HAS_GPU_STATS:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        current_stats = []
                        for gpu in gpus:
                            current_stats.append({
                                'load': gpu.load * 100,
                                'memory_usage': gpu.memoryUsed
                            })

                        result['times'].append(time.time() - start_time)
                        result['gpu_stats'].append(current_stats)

                time.sleep(0.1)

        except Exception:
            logger.exception("Error during GPU benchmark")
            result['error'] = 'GPU benchmark error'

        return result

    def monitor_resources(self):
        """Monitor system resources in real-time — graceful stop on unsafe levels"""
        while not self._stop_event.is_set():
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory_percent = psutil.virtual_memory().percent

            # Only stop for truly dangerous levels, not during normal benchmark load
            if cpu_percent > self.MAX_CPUSAFE or memory_percent > self.MAX_MEMORY_USAGE:
                self._stop_event.set()
                self.console.print("[red]Warning: System resource usage dangerously high. Stopping benchmark.[/red]")
                break

    def safe_cpu_test(self, duration: float) -> Dict:
        """CPU benchmark — continuous matrix multiplication, no sleep dominating the loop"""
        start_time = time.time()
        result: Dict = {'times': [], 'loads': []}

        # Warm up cpu_percent counter
        psutil.cpu_percent(interval=None)

        while time.time() - start_time < duration and not self._stop_event.is_set():
            # Use larger matrices for a meaningful workload
            size = 500
            matrix = np.random.rand(size, size)
            _ = np.dot(matrix, matrix.T)

            result['times'].append(time.time() - start_time)
            result['loads'].append(psutil.cpu_percent(interval=None))

        return result

    def safe_memory_test(self, duration: float) -> Dict:
        """Memory benchmark — allocates and operates on increasingly large buffers"""
        start_time = time.time()
        result: Dict = {'times': [], 'usage': [], 'bandwidth_mbps': []}
        allocated = []

        try:
            while time.time() - start_time < duration and not self._stop_event.is_set():
                # Allocate a 10MB chunk and perform copy operations
                chunk_size = 10 * 1024 * 1024 // 8  # 10MB worth of float64
                buf = np.zeros(chunk_size, dtype=np.float64)
                # Memory copy bandwidth test
                buf_copy = np.copy(buf)
                allocated.append(buf)
                allocated.append(buf_copy)

                result['times'].append(time.time() - start_time)
                mem = psutil.virtual_memory()
                result['usage'].append(mem.percent)

                # Stop if we're consuming more than 90% of available memory
                if mem.percent > 90:
                    break

                time.sleep(0.1)

        except MemoryError:
            result['memory_error'] = True
        finally:
            # Free all allocated memory
            del allocated

        return result

    def mini_test(self, gpu_only: bool = False, cpu_only: bool = False):
        """Run 30-second mini benchmark"""
        self._stop_event.clear()
        duration = 30

        # Start resource monitoring as daemon
        monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)
        monitor_thread.start()

        try:
            with Live(self.generate_status_table(), refresh_per_second=4) as live:
                self.results = {
                    'system_info': self.get_system_info(),
                    'duration': duration
                }

                if not gpu_only:
                    # CPU Test — half duration
                    self.results['cpu'] = self.safe_cpu_test(duration / 2)
                    # Memory Test — half duration
                    self.results['memory'] = self.safe_memory_test(duration / 2)

                if not cpu_only and self.has_gpu['available']:
                    # GPU Test
                    self.results['gpu'] = self.safe_gpu_test(duration / 2)

                live.update(self.generate_status_table())
        finally:
            self._stop_event.set()
            monitor_thread.join(timeout=2)

        self.display_results("Mini-Test")

    def god_test(self, gpu_only: bool = False, cpu_only: bool = False):
        """Running GOD-LEVEL comprehensive benchmark"""
        self._stop_event.clear()
        duration = 60

        # Start resource monitoring as daemon
        monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)
        monitor_thread.start()

        try:
            with Live(self.generate_status_table(), refresh_per_second=4) as live:
                self.results = {
                    'system_info': self.get_system_info(),
                    'duration': duration
                }

                if not gpu_only:
                    # Extended CPU Test
                    self.results['cpu'] = self.safe_cpu_test(duration / 2)
                    # Extended Memory Test
                    self.results['memory'] = self.safe_memory_test(duration / 2)

                if not cpu_only and self.has_gpu['available']:
                    # Extended GPU Test
                    self.results['gpu'] = self.safe_gpu_test(duration / 2)

                live.update(self.generate_status_table())
        finally:
            self._stop_event.set()
            monitor_thread.join(timeout=2)

        self.display_results("God-Test")

    def generate_status_table(self) -> Table:
        """Generate real-time status table"""
        table = Table(title="Benchmark Status")
        table.add_column("Metric")
        table.add_column("Value")

        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent

        table.add_row("CPU Usage", f"{cpu_percent}%")
        table.add_row("Memory Usage", f"{memory_percent}%")

        if self.has_gpu['available'] and HAS_GPU_STATS:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    for i, gpu in enumerate(gpus):
                        table.add_row(f"GPU {i}", f"[green]{gpu.name}[/green]")
                        table.add_row(f"GPU {i} Usage", f"{gpu.load * 100:.1f}%")
                        table.add_row(f"GPU {i} Memory", f"{gpu.memoryUsed} MB / {gpu.memoryTotal} MB")
                        if i < len(gpus) - 1:
                            table.add_section()
            except Exception:
                table.add_row("GPU", "[yellow]Error reading GPU stats[/yellow]")
        else:
            table.add_row("GPU", "[yellow]GPU not found in your device[/yellow]")

        table.add_row("Status", "[green]Running[/green]" if not self._stop_event.is_set() else "[red]Stopped[/red]")

        return table

    def display_results(self, test_type: str):
        """Display benchmark results"""
        if not self.results:
            return

        result_text = f"[bold cyan]{test_type} Results[/bold cyan]\n\n"

        # System Information
        result_text += "[green]System Information:[/green]\n"
        sys_info = self.results.get('system_info', {})
        result_text += f"• System: {sys_info.get('system', 'N/A')}\n"
        result_text += f"• Processor: {sys_info.get('processor', 'N/A')}\n"
        result_text += f"• CPU Cores: {sys_info.get('cpu_cores', 'N/A')}\n"
        result_text += f"• CPU Threads: {sys_info.get('cpu_threads', 'N/A')}\n"

        # GPU Information
        gpus = self.has_gpu.get('gpus', [])
        if gpus:
            result_text += f"• GPU Count: {len(gpus)}\n"
            for i, gpu in enumerate(gpus):
                result_text += f"  - GPU {i}: {gpu.get('name', 'N/A')}\n"
                result_text += f"    Memory Total: {gpu.get('memory_total', 'N/A')} MB\n"
                result_text += f"    Driver: {gpu.get('driver_version', 'N/A')}\n"
        else:
            result_text += "• GPU: [yellow]GPU not found in your device[/yellow]\n"

        result_text += "\n[green]Performance Results:[/green]\n"

        # CPU Results
        if 'cpu' in self.results:
            cpu_loads = self.results['cpu'].get('loads', [])
            if cpu_loads:
                result_text += f"• Average CPU Load: {np.mean(cpu_loads):.2f}%\n"
                result_text += f"• Peak CPU Load: {max(cpu_loads):.2f}%\n"

        # Memory Results
        if 'memory' in self.results:
            memory_usage = self.results['memory'].get('usage', [])
            if memory_usage:
                result_text += f"• Average Memory Usage: {np.mean(memory_usage):.2f}%\n"
                result_text += f"• Peak Memory Usage: {max(memory_usage):.2f}%\n"

        # GPU Results
        if 'gpu' in self.results and 'error' not in self.results['gpu']:
            gpu_stats_list = self.results['gpu'].get('gpu_stats', [])
            if gpu_stats_list:
                num_gpus = len(gpu_stats_list[0])
                for i in range(num_gpus):
                    gpu_loads = [stats[i]['load'] for stats in gpu_stats_list]
                    gpu_mems = [stats[i]['memory_usage'] for stats in gpu_stats_list]

                    result_text += f"• GPU {i} Results:\n"
                    result_text += f"  - Average Load: {np.mean(gpu_loads):.2f}%\n"
                    result_text += f"  - Peak Load: {max(gpu_loads):.2f}%\n"
                    result_text += f"  - Average Memory: {np.mean(gpu_mems):.2f} MB\n"
                    result_text += f"  - Peak Memory: {max(gpu_mems):.2f} MB\n"

        result_text += f"• Test Duration: {self.results.get('duration', 'N/A')} seconds\n"

        self.console.print(Panel(
            result_text,
            title=f"System Benchmark Report - {test_type}",
            border_style="blue"
        ))
