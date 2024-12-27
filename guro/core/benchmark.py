import psutil
import time
import numpy as np
import multiprocessing
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
import subprocess
import platform
from threading import Thread
import signal
import sys

try:
    import GPUtil
    HAS_GPU_STATS = True
except ImportError:
    HAS_GPU_STATS = False

class SafeSystemBenchmark:
    def __init__(self):
        self.console = Console()
        self.results = {}
        self.running = False
        self.baseline_scores = {
            'cpu_single': 2.5,
            'cpu_multi': 1.0,
            'gpu_compute': 1.5
        }
        # Safety thresholds
        self.MAX_CPU_USAGE = 80  # Maximum CPU usage percentage
        self.MAX_MEMORY_USAGE = 80  # Maximum memory usage percentage
        self.has_gpu = self._check_gpu()
        
    def _check_gpu(self):
        """Check if GPU is available and get GPU information"""
        gpu_info = {'available': False, 'info': None}
        
        if HAS_GPU_STATS:
            try:
                gpus = GPUtil.getGPUs()
                if gpus and len(gpus) > 0:
                    gpu = gpus[0]  # Get first GPU info
                    gpu_info['available'] = True
                    gpu_info['info'] = {
                        'name': gpu.name,
                        'count': len(gpus),
                        'memory_total': gpu.memoryTotal,
                        'driver_version': gpu.driver
                    }
            except Exception:
                pass
        return gpu_info
        
    def get_system_info(self):
        """Get basic system information safely"""
        info = {
            'system': platform.system(),
            'processor': platform.processor(),
            'memory_total': psutil.virtual_memory().total,
            'cpu_cores': psutil.cpu_count(logical=False),
            'cpu_threads': psutil.cpu_count(logical=True),
            'gpu': self.has_gpu
        }
        return info

    def safe_gpu_test(self, duration):
        """Safe GPU benchmark with controlled load"""
        if not self.has_gpu['available']:
            return {'times': [], 'loads': [], 'error': 'No GPU available'}
            
        result = {'times': [], 'loads': [], 'memory_usage': []}
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration and self.running:
                if HAS_GPU_STATS:
                    gpus = GPUtil.getGPUs()
                    if gpus and len(gpus) > 0:
                        gpu = gpus[0]
                        gpu_load = gpu.load * 100
                        gpu_memory = gpu.memoryUsed
                        
                        result['times'].append(time.time() - start_time)
                        result['loads'].append(gpu_load)
                        result['memory_usage'].append(gpu_memory)
                
                time.sleep(0.1)
                    
        except Exception as e:
            result['error'] = str(e)
            
        return result

    def monitor_resources(self):
        """Monitor system resources in real-time"""
        while self.running:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            # Safety check
            if cpu_percent > self.MAX_CPU_USAGE or memory_percent > self.MAX_MEMORY_USAGE:
                self.running = False
                self.console.print("[red]Warning: System resource usage too high. Stopping benchmark.[/red]")
                break
            
            time.sleep(0.5)

    def safe_cpu_test(self, duration):
        """Safe CPU benchmark with controlled load"""
        start_time = time.time()
        result = {'times': [], 'loads': []}
        
        while time.time() - start_time < duration and self.running:
            # Matrix operations with controlled size
            size = 100
            matrix = np.random.rand(size, size)
            np.dot(matrix, matrix.T)
            
            result['times'].append(time.time() - start_time)
            result['loads'].append(psutil.cpu_percent())
            time.sleep(0.1)
            
        return result

    def safe_memory_test(self, duration):
        """Safe memory benchmark"""
        start_time = time.time()
        result = {'times': [], 'usage': []}
        
        while time.time() - start_time < duration and self.running:
            memory = psutil.virtual_memory()
            result['times'].append(time.time() - start_time)
            result['usage'].append(memory.percent)
            time.sleep(0.1)
            
        return result

    def mini_test(self, gpu_only=False, cpu_only=False):
        """Run 30-second mini benchmark"""
        self.running = True
        duration = 30
        
        # Start resource monitoring
        monitor_thread = Thread(target=self.monitor_resources)
        monitor_thread.start()
        
        with Live(self.generate_status_table(), refresh_per_second=4) as live:
            self.results = {
                'system_info': self.get_system_info(),
                'duration': duration
            }
            
            if not gpu_only:
                # CPU Test
                self.results['cpu'] = self.safe_cpu_test(duration/2)
                # Memory Test
                self.results['memory'] = self.safe_memory_test(duration/2)
                
            if not cpu_only and self.has_gpu['available']:
                # GPU Test
                self.results['gpu'] = self.safe_gpu_test(duration/2)
            
            live.update(self.generate_status_table())
        
        self.running = False
        monitor_thread.join()
        self.display_results("Mini-Test")

    def god_test(self, gpu_only=False, cpu_only=False):
        """Run 120-second comprehensive benchmark"""
        self.running = True
        duration = 120
        
        # Start resource monitoring
        monitor_thread = Thread(target=self.monitor_resources)
        monitor_thread.start()
        
        with Live(self.generate_status_table(), refresh_per_second=4) as live:
            self.results = {
                'system_info': self.get_system_info(),
                'duration': duration
            }
            
            if not gpu_only:
                # Extended CPU Test
                self.results['cpu'] = self.safe_cpu_test(duration/2)
                # Extended Memory Test
                self.results['memory'] = self.safe_memory_test(duration/2)
                
            if not cpu_only and self.has_gpu['available']:
                # Extended GPU Test
                self.results['gpu'] = self.safe_gpu_test(duration/2)
            
            live.update(self.generate_status_table())
        
        self.running = False
        monitor_thread.join()
        self.display_results("God-Test")

    def generate_status_table(self):
        """Generate real-time status table"""
        table = Table(title="Benchmark Status")
        table.add_column("Metric")
        table.add_column("Value")
        
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        table.add_row("CPU Usage", f"{cpu_percent}%")
        table.add_row("Memory Usage", f"{memory_percent}%")
        
        if self.has_gpu['available'] and HAS_GPU_STATS:
            gpus = GPUtil.getGPUs()
            if gpus and len(gpus) > 0:
                gpu = gpus[0]
                table.add_row("GPU", f"[green]{gpu.name}[/green]")
                table.add_row("GPU Usage", f"{gpu.load * 100}%")
                table.add_row("GPU Memory", f"{gpu.memoryUsed} MB / {gpu.memoryTotal} MB")
                
        table.add_row("Status", "[green]Running[/green]" if self.running else "[red]Stopped[/red]")
        
        return table

    def display_results(self, test_type):
        """Display benchmark results"""
        if not self.results:
            return

        result_text = f"[bold cyan]{test_type} Results[/bold cyan]\n\n"
        
        # System Information
        result_text += "[green]System Information:[/green]\n"
        sys_info = self.results['system_info']
        result_text += f"• System: {sys_info['system']}\n"
        result_text += f"• Processor: {sys_info['processor']}\n"
        result_text += f"• CPU Cores: {sys_info['cpu_cores']}\n"
        result_text += f"• CPU Threads: {sys_info['cpu_threads']}\n"
        
        # GPU Information
        if sys_info['gpu']['available']:
            gpu_info = sys_info['gpu']['info']
            result_text += f"• GPU: {gpu_info['name']}\n"
            result_text += f"• GPU Count: {gpu_info['count']}\n"
            result_text += f"• GPU Memory: {gpu_info['memory_total']} MB\n"
            result_text += f"• Driver Version: {gpu_info['driver_version']}\n"
        else:
            result_text += "• GPU: Not Available\n"
        
        result_text += "\n[green]Performance Results:[/green]\n"
        
        # CPU Results
        if 'cpu' in self.results:
            result_text += f"• Average CPU Load: {np.mean(self.results['cpu']['loads']):.2f}%\n"
            result_text += f"• Peak CPU Load: {max(self.results['cpu']['loads']):.2f}%\n"
            
        # Memory Results
        if 'memory' in self.results:
            result_text += f"• Average Memory Usage: {np.mean(self.results['memory']['usage']):.2f}%\n"
            result_text += f"• Peak Memory Usage: {max(self.results['memory']['usage']):.2f}%\n"
            
        # GPU Results
        if 'gpu' in self.results and 'error' not in self.results['gpu']:
            loads = self.results['gpu']['loads']
            if loads:
                result_text += f"• Average GPU Load: {np.mean(loads):.2f}%\n"
                result_text += f"• Peak GPU Load: {max(loads):.2f}%\n"
                if 'memory_usage' in self.results['gpu']:
                    mem_usage = self.results['gpu']['memory_usage']
                    if mem_usage:
                        result_text += f"• Average GPU Memory Usage: {np.mean(mem_usage):.2f} MB\n"
                        result_text += f"• Peak GPU Memory Usage: {max(mem_usage):.2f} MB\n"
                
        result_text += f"• Test Duration: {self.results['duration']} seconds\n"

        self.console.print(Panel(
            result_text,
            title=f"System Benchmark Report - {test_type}",
            border_style="blue"
        ))

def main():
    benchmark = SafeSystemBenchmark()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        benchmark.running = False
        print("\nBenchmark stopped by user.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Test selection
    console = Console()
    console.print("\n[cyan]Select Benchmark Type:[/cyan]")
    console.print("1. Mini-Test (30 seconds)")
    console.print("2. God-Test (120 seconds)")
    
    choice = input("\nEnter your choice (1 or 2): ")
    
    if choice == "1":
        benchmark.mini_test()
    elif choice == "2":
        benchmark.god_test()
    else:
        console.print("[red]Invalid choice. Exiting.[/red]")

if __name__ == "__main__":
    main()
# # guro/core/benchmark.py
# import psutil
# import time
# import numpy as np
# import multiprocessing
# from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
# from rich.console import Console
# from rich.panel import Panel
# import torch

# class SystemBenchmark:
#     def __init__(self):
#         self.console = Console()
#         self.results = {}

#     def check_gpu_availability(self):
#         """Check if CUDA-capable GPU is available"""
#         try:
#             return torch.cuda.is_available()
#         except:
#             return False

#     def cpu_single_thread(self):
#         """Single-threaded CPU benchmark"""
#         start_time = time.time()
#         result = 0
#         # Perform intensive calculation
#         for i in range(10000000):
#             result += i * i
#         return time.time() - start_time

#     def cpu_multi_thread(self):
#         """Multi-threaded CPU benchmark"""
#         def worker():
#             result = 0
#             for i in range(5000000):
#                 result += i * i
#             return result

#         start_time = time.time()
#         num_cores = multiprocessing.cpu_count()
#         with multiprocessing.Pool(num_cores) as pool:
#             pool.map(worker, range(num_cores))
#         return time.time() - start_time

#     def gpu_benchmark(self):
#         """GPU benchmark using PyTorch"""
#         if not self.check_gpu_availability():
#             return None

#         # Create large tensors for GPU computation
#         size = 5000
#         torch.cuda.empty_cache()
        
#         start_time = time.time()
#         a = torch.randn(size, size, device='cuda')
#         b = torch.randn(size, size, device='cuda')
        
#         # Perform matrix multiplications
#         for _ in range(10):
#             c = torch.matmul(a, b)
#             torch.cuda.synchronize()
        
#         duration = time.time() - start_time
#         torch.cuda.empty_cache()
#         return duration

#     def run_benchmark(self, gpu=False, cpu=False):
#         """Run the specified benchmarks"""
#         if not (gpu or cpu):
#             cpu = True
#             gpu = True

#         with Progress(
#             SpinnerColumn(),
#             *Progress.get_default_columns(),
#             TimeElapsedColumn(),
#             console=self.console
#         ) as progress:
#             if cpu:
#                 task = progress.add_task("[cyan]Running CPU benchmarks...", total=2)
                
#                 # Single-thread benchmark
#                 single_thread_time = self.cpu_single_thread()
#                 progress.update(task, advance=1)
                
#                 # Multi-thread benchmark
#                 multi_thread_time = self.cpu_multi_thread()
#                 progress.update(task, advance=1)
                
#                 self.results['cpu'] = {
#                     'single_thread': round(single_thread_time, 2),
#                     'multi_thread': round(multi_thread_time, 2),
#                     'cpu_cores': multiprocessing.cpu_count()
#                 }

#             if gpu:
#                 if self.check_gpu_availability():
#                     task = progress.add_task("[cyan]Running GPU benchmarks...", total=1)
#                     gpu_time = self.gpu_benchmark()
#                     progress.update(task, advance=1)
                    
#                     self.results['gpu'] = {
#                         'compute_time': round(gpu_time, 2),
#                         'gpu_info': torch.cuda.get_device_name(0)
#                     }
#                 else:
#                     self.console.print(Panel(
#                         "[yellow]No CUDA-capable GPU found in the system.[/yellow]",
#                         title="GPU Benchmark",
#                         border_style="yellow"
#                     ))

#         self.display_results()

#     def display_results(self):
#         """Display benchmark results in a formatted panel"""
#         if not self.results:
#             return

#         result_text = "[bold cyan]Benchmark Results[/bold cyan]\n\n"
        
#         if 'cpu' in self.results:
#             result_text += "[green]CPU Benchmark:[/green]\n"
#             result_text += f"• Cores: {self.results['cpu']['cpu_cores']}\n"
#             result_text += f"• Single-thread time: {self.results['cpu']['single_thread']}s\n"
#             result_text += f"• Multi-thread time: {self.results['cpu']['multi_thread']}s\n"
#             result_text += f"• Performance ratio: {round(self.results['cpu']['single_thread'] / self.results['cpu']['multi_thread'], 2)}x\n\n"
        
#         if 'gpu' in self.results:
#             result_text += "[green]GPU Benchmark:[/green]\n"
#             result_text += f"• GPU: {self.results['gpu']['gpu_info']}\n"
#             result_text += f"• Compute time: {self.results['gpu']['compute_time']}s\n"

#         self.console.print(Panel(
#             result_text,
#             title="Guro Benchmark Report",
#             border_style="blue"
#         ))
