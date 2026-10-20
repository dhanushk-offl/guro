import psutil
import platform
import datetime
import time
import csv
import logging
import subprocess
import shlex
import json
import math
from collections import deque
from contextlib import nullcontext
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box

from .utils import ASCIIGraph
from .telemetry import Schedule, SampleWriter, timestamp

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
        value = float(stripped)
        return value if math.isfinite(value) else None
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
                 "fan.speed,power.draw,pci.bus_id",
                 "--format=csv,noheader,nounits"],
                universal_newlines=False,
                timeout=SUBPROCESS_TIMEOUT,
            ).decode('utf-8')
            lines = output.strip().split('\n')
            gpus = []
            for line in lines:
                if not line.strip():
                    continue
                parts = [p.strip() for p in next(csv.reader([line]))]
                if len(parts) < 8:
                    continue
                name, total, used, free, temp, util, fan, power = parts[:8]
                gpus.append({
                    'name': name,
                    'id': parts[8] if len(parts) > 8 else name,
                    'memory_total': _safe_float(total) * (1024**2) if _safe_float(total) is not None else None,
                    'memory_used': _safe_float(used) * (1024**2) if _safe_float(used) is not None else None,
                    'memory_free': _safe_float(free) * (1024**2) if _safe_float(free) is not None else None,
                    'temperature': _safe_float(temp),
                    'utilization': _safe_float(util),
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
            output = subprocess.check_output(
                ['rocm-smi', '--showproductname', '--showuse', '--showmeminfo', 'vram',
                 '--showtemp', '--showbus', '--json'],
                universal_newlines=True, timeout=SUBPROCESS_TIMEOUT,
                stderr=subprocess.DEVNULL,
            )
            cards = json.loads(output)
            gpus = []
            for card, values in cards.items():
                if not isinstance(values, dict) or not card.startswith('card'):
                    continue
                def number(key):
                    return _safe_float(str(values.get(key, '')))
                total = number('VRAM Total Memory (B)')
                used = number('VRAM Total Used Memory (B)')
                gpus.append({
                    'id': values.get('PCI Bus', card), 'type': 'AMD',
                    'name': values.get('Card Series') or values.get('Card Model') or card,
                    'memory_total': total, 'memory_used': used,
                    'memory_free': total - used if total is not None and used is not None else None,
                    'temperature': number('Temperature (Sensor edge) (C)'),
                    'utilization': number('GPU use (%)'),
                })
            return gpus
        except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
            logger.debug('AMD GPU information unavailable', exc_info=True)
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
                        'id': video.PNPDeviceID,
                        'type': 'Display adapter',
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
                for line in output.splitlines():
                    try:
                        parts = shlex.split(line)
                    except ValueError:
                        continue
                    if len(parts) < 4 or not any(kind in parts[1].upper() for kind in ('VGA', '3D', 'DISPLAY')):
                        continue
                    gpus.append({
                        'id': parts[0], 'name': f'{parts[2]} {parts[3]}',
                        'type': 'Display adapter', 'memory_total': None,
                        'utilization': None, 'temperature': None,
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
    def get_all_gpus(include_adapters=True) -> Dict:
        gpu_info = {
            'available': False,
            'gpus': []
        }

        nvidia_gpus = GPUDetector.get_nvidia_info()
        amd_gpus = GPUDetector.get_amd_info()
        integrated_gpus = GPUDetector.get_integrated_info() if include_adapters else []

        all_gpus = nvidia_gpus + amd_gpus

        # PCI addresses are stable across tools; names are not.
        def identity(gpu):
            return str(gpu.get('id') or '').lower()[-7:]
        detected = {identity(g) for g in all_gpus if g.get('id')}
        names = {str(g.get('name') or '').casefold() for g in all_gpus}
        if not all_gpus:
            all_gpus.extend(integrated_gpus)
        else:
            for adapter in integrated_gpus:
                if identity(adapter) not in detected and str(adapter.get('name') or '').casefold() not in names:
                    all_gpus.append(adapter)

        if all_gpus:
            gpu_info['available'] = True
            gpu_info['gpus'] = all_gpus

        return gpu_info


class SystemMonitor:
    def __init__(self):
        self.console = Console()
        self.cpu_graph = ASCIIGraph(width=40, height=4)
        self.memory_graph = ASCIIGraph(width=40, height=4)
        self.monitoring_data = deque(maxlen=60)
        # Cache GPU info — subprocess calls are expensive
        self._gpu_info = GPUDetector.get_all_gpus()
        self._gpu_info_time = time.monotonic()
        self._gpu_info_ttl = 5.0  # Re-query metrics every 5 seconds
        self._adapters = [g for g in self._gpu_info['gpus'] if g.get('type') == 'Display adapter']
        from .heatmap import SystemHeatmap
        self._thermal = SystemHeatmap()
        psutil.cpu_percent()

    def _refresh_gpu_info(self) -> Dict:
        """Return cached GPU info if fresh, otherwise re-query."""
        now = time.monotonic()
        if now - self._gpu_info_time > self._gpu_info_ttl:
            try:
                info = GPUDetector.get_all_gpus(include_adapters=False)
                ids = {str(g.get('id') or '').lower()[-7:] for g in info['gpus']}
                names = {str(g.get('name') or '').casefold() for g in info['gpus']}
                for adapter in self._adapters:
                    if str(adapter.get('id') or '').lower()[-7:] not in ids and str(adapter.get('name') or '').casefold() not in names:
                        info['gpus'].append(adapter)
                info['available'] = bool(info['gpus'])
                self._gpu_info = info
                self._gpu_info_time = now
            except Exception:
                logger.exception("Error refreshing GPU info, using cached data")
        return self._gpu_info

    def _get_cpu_temperature(self) -> Optional[float]:
        if platform.system() == 'Linux':
            return self._thermal.get_linux_temps()['CPU']
        return None

    def get_system_info(self) -> Dict:
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()

        system_info: Dict = {
            'os': f"{platform.system()} {platform.release()}",
            'cpu_model': platform.processor(),
            'cpu_cores': psutil.cpu_count(logical=False),
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

    def run_performance_test(self, interval: float = 1.0, duration: Optional[int] = 30, export_data: bool = False, output_path: Optional[str] = None):
        schedule = Schedule(interval, duration)
        self.console.clear()

        # Initial GPU info (subprocess calls)
        gpu_info = self._refresh_gpu_info()
        gpu_graphs = [ASCIIGraph(width=40, height=4) for _ in gpu_info.get('gpus', [])]

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
            Layout(name="cpu_graph", size=7),
            Layout(name="mem_graph", size=7),
            Layout(name="gpu_graphs")
        )

        path = output_path or f'monitoring_data_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv'
        with (open(path, 'w', newline='', encoding='utf-8') if export_data else nullcontext()) as stream:
            writer_context = SampleWriter(stream, 'csv', ['timestamp', 'cpu_usage', 'memory_usage']) if stream else nullcontext()
            self._run_dashboard(layout, gpu_graphs, schedule, duration, export_data, writer_context)
        if export_data:
            self.console.print(f'[green]Monitoring data exported to {path}[/green]')

    def _run_dashboard(self, layout, gpu_graphs, schedule, duration, export_data, writer_context):
        try:
            with writer_context as writer, Live(layout, refresh_per_second=4, screen=True):
                while True:
                    elapsed = schedule.elapsed
                    if schedule.finished:
                        break

                    # Update System Stats
                    sample = self.collect_sample()
                    cpu_percent = sample['cpu_usage']
                    memory_percent = sample['memory_usage']
                    sys_info = sample['system_info']

                    self.cpu_graph.add_point(cpu_percent)
                    self.memory_graph.add_point(memory_percent)

                    if export_data:
                        row = {key: sample[key] for key in ('timestamp', 'cpu_usage', 'memory_usage')}
                        writer.write(row)
                        self.monitoring_data.append(row)

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
                    gpu_info = sample['gpu']
                    # Ensure enough graphs if GPU count changed
                    while len(gpu_graphs) < len(gpu_info.get('gpus', [])):
                        gpu_graphs.append(ASCIIGraph(width=40, height=4))

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
                            util = gpu.get('utilization')
                            if util is not None:
                                graph.add_point(util)
                            label = f'{util:.1f}%' if util is not None else 'N/A'
                            plot = graph.render(f"GPU {i} ({gpu.get('name', 'Unknown')}): {label}")
                            gpu_plots.append(plot or f"GPU {i}: utilization N/A")

                            gpu_details_table.add_row(
                                f"GPU {i}", "Name",
                                gpu.get('name', 'Unknown')[:20]
                            )
                            gpu_details_table.add_row(
                                "", "Temp",
                                f"{gpu['temperature']:.1f}°C" if gpu.get('temperature') is not None else 'N/A'
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
                        Layout(Panel(self._get_process_table(sample['processes']), title="Top Processes", border_style="white"))
                    )
                    layout["details"].update(details_layout)

                    # Footer
                    layout["footer"].update(Panel(
                        "[bold yellow]Press Ctrl+C to stop[/bold yellow]   "
                        f"[cyan]Export: {'On' if export_data else 'Off'}[/cyan]",
                        border_style="blue", box=box.SIMPLE
                    ))

                    schedule.wait()

        except KeyboardInterrupt:
            pass

        self.console.clear()
        self.console.print("[bold green]Monitoring completed.[/bold green]")

    def collect_sample(self):
        """Collect one snapshot independently of terminal rendering or export."""
        return {
            'timestamp': timestamp(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'system_info': self.get_system_info(),
            'gpu': self._refresh_gpu_info(),
            'processes': self._get_processes(),
        }

    def _get_processes(self):
        procs = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    procs.append({
                        'pid': proc.info['pid'], 'name': proc.info['name'] or 'N/A',
                        'cpu_percent': proc.cpu_percent(interval=None),
                        'memory_percent': proc.info.get('memory_percent', 0.0) or 0.0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            logger.exception('Error collecting process information')
        return sorted(procs, key=lambda p: p['cpu_percent'], reverse=True)[:10]

    def _get_process_table(self, processes=None) -> Table:
        """Render process deltas collected over the sampling interval."""
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column('PID', style='dim')
        table.add_column('Name')
        table.add_column('CPU%', justify='right')
        table.add_column('Mem%', justify='right')
        for proc in self._get_processes() if processes is None else processes:
            table.add_row(str(proc['pid']), proc['name'][:15],
                          f"{proc['cpu_percent']:.1f}", f"{proc['memory_percent']:.1f}")
        return table
