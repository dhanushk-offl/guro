import psutil
import platform
import datetime
import os
import time
import csv
import logging
import subprocess
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box

from .utils import ASCIIGraph

logger = logging.getLogger(__name__)

SUBPROCESS_TIMEOUT = 5  # seconds


def _safe_float(val: str) -> Optional[float]:
    """Parse a numeric string that may be '[N/A]', 'N/A', 'Not Available', etc."""
    if not val:
        return None
    stripped = val.strip().upper()
    if stripped in ('[N/A]', 'N/A', 'NOT AVAILABLE', 'NAN', '-'):
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


class GPUDetector:
    @staticmethod
    def get_nvidia_info() -> List[Dict]:
        try:
            nvidia_smi = "nvidia-smi"
            output = subprocess.check_output(
                [nvidia_smi,
                 "--query-gpu=gpu_name,memory.total,memory.used,"
                 "memory.free,temperature.gpu,utilization.gpu,"
                 "fan.speed,power.draw",
                 "--format=csv,noheader,nounits"],
                universal_newlines=False,
                timeout=SUBPROCESS_TIMEOUT,
            ).decode('utf-8')
            lines = output.strip().split('\n')
            gpus = []
            for line in lines:
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 8:
                    continue
                name, total, used, free, temp, util, fan, power = parts
                gpus.append({
                    'name': name,
                    'memory_total': _safe_float(total) * (1024**2) if _safe_float(total) is not None else None,
                    'memory_used': _safe_float(used) * (1024**2) if _safe_float(used) is not None else None,
                    'memory_free': _safe_float(free) * (1024**2) if _safe_float(free) is not None else None,
                    'temperature': _safe_float(temp),
                    'utilization': _safe_float(util) or 0.0,
                    'fan_speed': _safe_float(fan),
                    'power_draw': _safe_float(power),
                    'type': 'NVIDIA'
                })
            return gpus
        except FileNotFoundError:
            logger.debug("nvidia-smi not found, skipping NVIDIA GPU detection")
            return []
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi timed out")
            return []
        except subprocess.CalledProcessError as e:
            logger.warning("nvidia-smi failed with return code %d", e.returncode)
            return []
        except Exception:
            logger.exception("Unexpected error detecting NVIDIA GPUs")
            return []

    @staticmethod
    def get_amd_info() -> List[Dict]:
        try:
            rocm_smi = "rocm-smi"
            output = subprocess.check_output(
                [rocm_smi, "--showuse", "--showmeminfo", "--showtemp"],
                universal_newlines=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
            gpus = []
            lines = output.strip().split('\n')
            current_gpu: Dict = {}
            for line in lines:
                if 'GPU' in line and 'Card' in line:
                    if current_gpu:
                        gpus.append(current_gpu)
                    current_gpu = {'type': 'AMD'}
                if 'GPU Memory Use' in line:
                    try:
                        used = float(line.split(':')[1].strip().split()[0]) * 1024**2
                        current_gpu['memory_used'] = used
                    except (ValueError, IndexError):
                        pass
                if 'Total GPU Memory' in line:
                    try:
                        total = float(line.split(':')[1].strip().split()[0]) * 1024**2
                        current_gpu['memory_total'] = total
                        current_gpu['memory_free'] = total - current_gpu.get('memory_used', 0)
                    except (ValueError, IndexError):
                        pass
                if 'Temperature' in line:
                    try:
                        temp = float(line.split(':')[1].strip().split()[0])
                        current_gpu['temperature'] = temp
                    except (ValueError, IndexError):
                        pass
            if current_gpu:
                gpus.append(current_gpu)
            return gpus
        except FileNotFoundError:
            logger.debug("rocm-smi not found, skipping AMD GPU detection")
            return []
        except subprocess.TimeoutExpired:
            logger.warning("rocm-smi timed out")
            return []
        except subprocess.CalledProcessError as e:
            logger.warning("rocm-smi failed with return code %d", e.returncode)
            return []
        except Exception:
            logger.exception("Unexpected error detecting AMD GPUs")
            return []

    @staticmethod
    def get_integrated_info() -> List[Dict]:
        gpus = []
        try:
            if platform.system() == "Windows":
                import wmi  # type: ignore
                w = wmi.WMI()
                for video in w.Win32_VideoController():
                    name = video.Name
                    gpus.append({
                        'name': name,
                        'type': 'Integrated',
                        'memory_total': int(video.AdapterRAM) if video.AdapterRAM else None,
                        'utilization': None,
                        'temperature': None
                    })
            elif platform.system() == "Linux":
                # Use subprocess without shell=True — no pipe, no injection
                output = subprocess.check_output(
                    ["lspci", "-mm"],
                    universal_newlines=True,
                    timeout=SUBPROCESS_TIMEOUT,
                )
                for line in output.strip().split('\n'):
                    if 'VGA' in line.upper() or '3D' in line.upper() or 'Display' in line.upper():
                        # Parse device description from lspci -mm output
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            gpus.append({
                                'name': parts[-1].strip(),
                                'type': 'Integrated',
                                'memory_total': None,
                                'utilization': None,
                                'temperature': None
                            })
        except FileNotFoundError:
            logger.debug("lspci not found, skipping integrated GPU detection")
        except subprocess.TimeoutExpired:
            logger.warning("lspci timed out")
        except subprocess.CalledProcessError:
            logger.debug("lspci returned non-zero, no integrated GPU info available")
        except Exception:
            logger.exception("Unexpected error detecting integrated GPUs")
        return gpus

    @staticmethod
    def get_all_gpus() -> Dict:
        gpu_info = {
            'available': False,
            'gpus': []
        }

        nvidia_gpus = GPUDetector.get_nvidia_info()
        amd_gpus = GPUDetector.get_amd_info()
        integrated_gpus = GPUDetector.get_integrated_info()

        all_gpus = nvidia_gpus + amd_gpus

        # Add integrated GPUs only if no dedicated GPUs of the same name exist
        detected_names = [g.get('name', '') for g in all_gpus if g.get('name')]
        for ig in integrated_gpus:
            if ig.get('name', '') not in detected_names:
                all_gpus.append(ig)

        if all_gpus:
            gpu_info['available'] = True
            gpu_info['gpus'] = all_gpus

        return gpu_info


class SystemMonitor:
    def __init__(self):
        self.console = Console()
        self.cpu_graph = ASCIIGraph()
        self.memory_graph = ASCIIGraph()
        self.monitoring_data: List[Dict] = []
        # Cache GPU info — subprocess calls are expensive
        self._gpu_info = GPUDetector.get_all_gpus()
        self._gpu_info_time = time.time()
        self._gpu_info_ttl = 5.0  # Re-query every 5 seconds

    def _refresh_gpu_info(self) -> Dict:
        """Return cached GPU info if fresh, otherwise re-query."""
        now = time.time()
        if now - self._gpu_info_time > self._gpu_info_ttl:
            try:
                self._gpu_info = GPUDetector.get_all_gpus()
                self._gpu_info_time = now
            except Exception:
                logger.exception("Error refreshing GPU info, using cached data")
        return self._gpu_info

    def _get_cpu_temperature(self) -> Optional[float]:
        if platform.system() == 'Linux':
            try:
                temp_file = '/sys/class/thermal/thermal_zone0/temp'
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        return float(f.read()) / 1000.0
            except (OSError, ValueError):
                pass
        return None

    def get_system_info(self) -> Dict:
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()

        system_info: Dict = {
            'os': f"{platform.system()} {platform.release()}",
            'cpu_model': platform.processor(),
            'cpu_cores': psutil.cpu_count(),
            'cpu_threads': psutil.cpu_count(logical=True),
            'cpu_freq': f"{cpu_freq.current:.2f}MHz" if cpu_freq else "N/A",
            'memory_total': f"{memory.total / (1024**3):.2f}GB",
            'memory_available': f"{memory.available / (1024**3):.2f}GB",
        }

        temp = self._get_cpu_temperature()
        if temp is not None:
            system_info['cpu_temp'] = f"{temp:.1f}°C"

        return system_info

    def export_monitoring_data(self, filepath: Optional[str] = None):
        """Export monitoring data to CSV. Uses a timestamped filename by default."""
        if not self.monitoring_data:
            return

        if filepath is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f'monitoring_data_{timestamp}.csv'

        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'cpu_usage', 'memory_usage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for data in self.monitoring_data:
                writer.writerow(data)

        self.console.print(f"[green]Monitoring data exported to '{filepath}'[/green]")

    def run_performance_test(self, interval: float = 1.0, duration: Optional[int] = 30, export_data: bool = False):
        self.console.clear()

        # Initial GPU info (subprocess calls)
        gpu_info = self._refresh_gpu_info()
        gpu_graphs = [ASCIIGraph(width=40, height=5) for _ in gpu_info.get('gpus', [])]

        # Setup Dashboard Layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="graphs", ratio=1),
            Layout(name="details", ratio=1)
        )
        layout["graphs"].split_column(
            Layout(name="cpu_graph"),
            Layout(name="mem_graph"),
            Layout(name="gpu_graphs")
        )

        start_time = time.time()
        try:
            with Live(layout, refresh_per_second=4, screen=True):
                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    if duration and (elapsed >= duration):
                        break

                    # Update System Stats
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                    sys_info = self.get_system_info()

                    self.cpu_graph.add_point(cpu_percent)
                    self.memory_graph.add_point(memory_percent)

                    if export_data:
                        self.monitoring_data.append({
                            'timestamp': datetime.datetime.now().isoformat(),
                            'cpu_usage': cpu_percent,
                            'memory_usage': memory_percent
                        })

                    # Header
                    header_text = (
                        f"[bold cyan]Guro System Dashboard[/bold cyan] | "
                        f"[yellow]Running for: {int(elapsed)}s"
                        f"{f'/{duration}s' if duration else ''}[/yellow] | "
                        f"[green]{sys_info['os']}[/green]"
                    )
                    layout["header"].update(Panel(header_text, border_style="blue"))

                    # Graphs Column
                    cpu_panel = Panel(
                        self.cpu_graph.render(f"CPU: {cpu_percent:.1f}%"),
                        title="CPU Usage History", border_style="green"
                    )
                    mem_panel = Panel(
                        self.memory_graph.render(f"Memory: {memory_percent:.1f}%"),
                        title="Memory Usage History", border_style="magenta"
                    )

                    layout["cpu_graph"].update(cpu_panel)
                    layout["mem_graph"].update(mem_panel)

                    # Refresh GPU info from cache
                    gpu_info = self._refresh_gpu_info()
                    # Ensure enough graphs if GPU count changed
                    while len(gpu_graphs) < len(gpu_info.get('gpus', [])):
                        gpu_graphs.append(ASCIIGraph(width=40, height=5))

                    gpu_details_table = Table(
                        title="GPU & Device Information",
                        box=box.SIMPLE, expand=True
                    )
                    gpu_details_table.add_column("Device", style="cyan")
                    gpu_details_table.add_column("Stat", style="yellow")
                    gpu_details_table.add_column("Value", style="green")

                    if gpu_info['available']:
                        gpu_plots = []
                        for i, (gpu, graph) in enumerate(zip(gpu_info['gpus'], gpu_graphs)):
                            util = gpu.get('utilization', 0) or 0
                            graph.add_point(util)
                            gpu_plots.append(graph.render(f"GPU {i} ({gpu['name']}): {util:.1f}%"))

                            gpu_details_table.add_row(
                                f"GPU {i}", "Name",
                                gpu.get('name', 'Unknown')[:20]
                            )
                            gpu_details_table.add_row(
                                "", "Temp",
                                f"{gpu.get('temperature', 'N/A')}°C"
                            )
                            if gpu.get('memory_used') is not None and gpu.get('memory_total') is not None:
                                mem_str = (
                                    f"{gpu['memory_used']/(1024**2):.0f}/"
                                    f"{gpu['memory_total']/(1024**2):.0f}MB"
                                )
                                gpu_details_table.add_row("", "Mem", mem_str)

                        layout["gpu_graphs"].update(Panel(
                            "\n".join(gpu_plots),
                            title="GPU Usage History", border_style="cyan"
                        ))
                    else:
                        layout["gpu_graphs"].update(Panel(
                            "[yellow]No dedicated GPU stats available[/yellow]",
                            title="GPU Usage History"
                        ))
                        gpu_details_table.add_row(
                            "GPU", "Status",
                            "[yellow]GPU not found in your device[/yellow]"
                        )

                    # Details Column
                    details_layout = Layout()
                    details_layout.split_column(
                        Layout(Panel(gpu_details_table, title="Detailed Stats", border_style="white")),
                        Layout(Panel(self._get_process_table(), title="Top Processes", border_style="white"))
                    )
                    layout["details"].update(details_layout)

                    # Footer
                    layout["footer"].update(Panel(
                        "[bold yellow]Press Ctrl+C to stop monitoring[/bold yellow] | "
                        f"[cyan]Export: {'Enabled' if export_data else 'Disabled'}[/cyan]",
                        border_style="blue"
                    ))

                    time.sleep(interval)

        except KeyboardInterrupt:
            pass

        self.console.clear()
        self.console.print("[bold green]Monitoring completed.[/bold green]")
        if export_data:
            self.export_monitoring_data()

    def _get_process_table(self) -> Table:
        """Build a table of top 10 processes by CPU usage.
        Calls cpu_percent twice with a brief delay for accurate readings."""
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("PID", style="dim")
        table.add_column("Name")
        table.add_column("CPU%", justify="right")
        table.add_column("Mem%", justify="right")

        try:
            # First call seeds the counters — discard results
            procs = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc.cpu_percent(interval=None)  # Seed
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Brief sleep for delta accumulation
            time.sleep(0.05)

            # Second call gets meaningful delta values
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    cpu_pct = proc.cpu_percent(interval=None)
                    mem_pct = proc.info.get('memory_percent', 0.0) or 0.0
                    procs.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'] or 'N/A',
                        'cpu_percent': cpu_pct,
                        'memory_percent': mem_pct,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            procs.sort(key=lambda x: x['cpu_percent'], reverse=True)

            for proc in procs[:10]:
                table.add_row(
                    str(proc['pid']),
                    proc['name'][:15],
                    f"{proc['cpu_percent']:.1f}",
                    f"{proc['memory_percent']:.1f}"
                )
        except Exception:
            logger.exception("Error collecting process information")
        return table
