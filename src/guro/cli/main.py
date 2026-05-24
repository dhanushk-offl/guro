import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from typing import Optional

from .._version import __version__
from ..core.monitor import SystemMonitor
from ..core.benchmark import SafeSystemBenchmark
from ..core.heatmap import SystemHeatmap

console = Console()


def print_banner():
    """Display the Guro banner"""
    banner = """
[bold cyan]
   ██████╗ ██╗   ██╗██████╗  ██████╗
  ██╔════╝ ██║   ██║██╔══██╗██╔═══██╗
  ██║  ███╗██║   ██║██████╔╝██║   ██║
  ██║   ██║██║   ██║██╔══██╗██║   ██║
  ╚██████╔╝╚██████╔╝██║  ██║╚██████╔╝
   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝
[/bold cyan]
[yellow]A Simple System Monitoring & Benchmarking Toolkit[/yellow]
    """
    console.print(banner)


@click.group()
@click.version_option(version=__version__)
def cli():
    """🚀 Guro - A Simple System Monitoring & Benchmarking Toolkit"""
    print_banner()


@cli.command()
@click.option('--interval', '-i', default=1.0, help='Monitoring interval in seconds')
@click.option('--duration', '-d', default=None, type=int, help='Monitoring duration in seconds')
@click.option('--export', '-e', is_flag=True, help='Export monitoring data to CSV')
def monitor(interval: float, duration: Optional[int], export: bool):
    """📊 Monitor system resources and performance in real-time"""
    try:
        mon = SystemMonitor()
        if export:
            click.echo("📝 Monitoring data will be exported to a timestamped CSV file")

        with console.status("[bold green]Initializing system monitor..."):
            mon.run_performance_test(
                interval=interval,
                duration=duration,
                export_data=export
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception:
        console.print("\n[red]Error during monitoring. Check logs for details.[/red]")


@cli.command()
@click.option('--type', '-t', 'test_type',
              type=click.Choice(['mini', 'god'], case_sensitive=False),
              help='Type of benchmark test to run')
@click.option('--gpu-only', is_flag=True, help='Run only GPU benchmark')
@click.option('--cpu-only', is_flag=True, help='Run only CPU benchmark')
def benchmark(test_type: str, gpu_only: bool, cpu_only: bool):
    """🔥 Run system benchmarks"""
    try:
        bench = SafeSystemBenchmark()

        if not test_type:
            test_type = Prompt.ask(
                "Select benchmark type",
                choices=["mini", "god"],
                default="mini"
            )

        with console.status("[bold green]Preparing benchmark..."):
            if test_type == "mini":
                bench.mini_test(gpu_only=gpu_only, cpu_only=cpu_only)
            else:
                bench.god_test(gpu_only=gpu_only, cpu_only=cpu_only)

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark stopped by user[/yellow]")
    except Exception:
        console.print(Panel(
            "[red]Error during benchmark. Check logs for details.[/red]",
            title="⚠️ Benchmark Error",
            border_style="red"
        ))


@cli.command()
def gpu():
    """🚀 Quickly check all available GPUs and their current status"""
    from ..core.monitor import GPUDetector
    from rich.table import Table
    from rich import box

    with console.status("[bold green]Detecting GPUs..."):
        gpu_info = GPUDetector.get_all_gpus()

    if gpu_info['available']:
        gpu_table = Table(title="Detected GPUs", box=box.HEAVY)
        gpu_table.add_column("GPU", style="cyan")
        gpu_table.add_column("Metric", style="cyan")
        gpu_table.add_column("Value", style="green")

        for i, gpu_data in enumerate(gpu_info['gpus']):
            gpu_table.add_row(f"GPU {i}", "Type", gpu_data.get('type', 'Unknown'))
            gpu_table.add_row("", "Name", gpu_data.get('name', 'Unknown'))
            if gpu_data.get('memory_total') is not None:
                gpu_table.add_row("", "Memory Total", f"{gpu_data['memory_total'] / (1024**3):.2f} GB")
            if gpu_data.get('utilization') is not None:
                gpu_table.add_row("", "Utilization", f"{gpu_data['utilization']}%")
            if gpu_data.get('temperature') is not None:
                gpu_table.add_row("", "Temperature", f"{gpu_data['temperature']}°C")
            if i < len(gpu_info['gpus']) - 1:
                gpu_table.add_section()

        console.print(gpu_table)
    else:
        console.print("[yellow]GPU not found in your device[/yellow]")


@cli.command()
@click.option('--interval', '-i',
              type=click.FloatRange(min=0.1, min_open=False),
              default=1.0,
              help='Update interval in seconds')
@click.option('--duration', '-d',
              type=click.IntRange(min=1, min_open=False),
              default=10,
              help='Duration to run in seconds')
def heatmap(interval: float, duration: int):
    """🌡️ Display unified system temperature heatmap"""
    try:
        hm = SystemHeatmap()

        with console.status("[bold green]Initializing system heatmap..."):
            updates = hm.run(
                interval=interval,
                duration=duration
            )

        console.print(f"\n[green]Heatmap completed after {updates} updates[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Heatmap visualization stopped by user[/yellow]")
    except Exception:
        console.print("[red]Error during heatmap visualization. Check logs for details.[/red]")


@cli.command(name='list')
def list_features():
    """📋 List all available features and commands"""
    table = Table(title="Guro Commands and Features")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Options", style="yellow")

    commands = {
        "monitor": ("📊 Real-time system monitoring", "-i, -d, -e"),
        "gpu": ("🚀 Dedicated GPU status check", "None"),
        "benchmark": ("🔥 System benchmarking", "-t [mini/god], --gpu-only"),
        "heatmap": ("🌡️ Hardware Heatmap Analysis", "-i, -d"),
        "about": ("ℹ️  About Guro", "None"),
        "list": ("📋 List all commands", "None")
    }

    for cmd, (desc, opts) in commands.items():
        table.add_row(cmd, desc, opts)

    console.print(table)


@cli.command(name='about')
def about():
    """ℹ️  Display information about Guro"""
    about_text = f"""[bold cyan]Guro - A Simple System Monitoring & Benchmarking Toolkit[/bold cyan]

[green]Version:[/green] {__version__}
[green]Author:[/green] Dhanush Kandhan
[green]License:[/green] MIT

🛠️  A Simple powerful toolkit for system monitoring and benchmarking.

[yellow]Key Features:[/yellow]
• 📊 Real-time system monitoring
• 💅 Catchy CL Interface
• 🔥 Performance benchmarking (with Multi-GPU support)
• 🌡️ Hardware Heatmap Analysis (Hottest component tracking)

[blue]GitHub:[/blue] https://github.com/dhanushk-offl/guro
[blue]Documentation:[/blue] https://github.com/dhanushk-offl/guro/wiki"""

    console.print(Panel(about_text, title="About Guro", border_style="blue"))


if __name__ == '__main__':
    cli()
