import psutil
import platform
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import os

class SystemMonitor:
    def __init__(self):
        self.console = Console()

    def get_cpu_info(self):
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        return {
            'percent': cpu_percent,
            'freq_current': cpu_freq.current if cpu_freq else 0,
            'freq_max': cpu_freq.max if cpu_freq else 0,
            'cores': psutil.cpu_count(),
            'threads': psutil.cpu_count(logical=True)
        }

    def get_memory_info(self):
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent,
            'used': memory.used
        }

    def get_disk_info(self):
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except:
                continue
        return partitions

    def display_system_info(self):
        layout = Layout()
        layout.split_column(
            Layout(name="upper"),
            Layout(name="lower")
        )

        # CPU Table
        cpu_info = self.get_cpu_info()
        cpu_table = Table(title="CPU Information", show_header=True, header_style="bold magenta")
        cpu_table.add_column("Metric", style="cyan")
        cpu_table.add_column("Value", style="green")
        
        cpu_table.add_row("Cores/Threads", f"{cpu_info['cores']}/{cpu_info['threads']}")
        cpu_table.add_row("Current Frequency", f"{cpu_info['freq_current']:.2f} MHz")
        cpu_table.add_row("Max Frequency", f"{cpu_info['freq_max']:.2f} MHz")
        
        for i, percent in enumerate(cpu_info['percent']):
            cpu_table.add_row(f"Core {i} Usage", f"{percent}%")

        # Memory Table
        mem_info = self.get_memory_info()
        mem_table = Table(title="Memory Information", show_header=True, header_style="bold magenta")
        mem_table.add_column("Metric", style="cyan")
        mem_table.add_row("Total", f"{mem_info['total'] / (1024**3):.2f} GB")
        mem_table.add_row("Used", f"{mem_info['used'] / (1024**3):.2f} GB")
        mem_table.add_row("Available", f"{mem_info['available'] / (1024**3):.2f} GB")
        mem_table.add_row("Usage", f"{mem_info['percent']}%")

        # Disk Table
        disk_info = self.get_disk_info()
        disk_table = Table(title="Disk Information", show_header=True, header_style="bold magenta")
        disk_table.add_column("Device", style="cyan")
        disk_table.add_column("Mount", style="green")
        disk_table.add_column("Total", style="blue")
        disk_table.add_column("Used", style="red")
        disk_table.add_column("Free", style="green")
        disk_table.add_column("Usage", style="yellow")

        for disk in disk_info:
            disk_table.add_row(
                disk['device'],
                disk['mountpoint'],
                f"{disk['total'] / (1024**3):.2f} GB",
                f"{disk['used'] / (1024**3):.2f} GB",
                f"{disk['free'] / (1024**3):.2f} GB",
                f"{disk['percent']}%"
            )

        self.console.print(Panel.fit(cpu_table))
        self.console.print(Panel.fit(mem_table))
        self.console.print(Panel.fit(disk_table))