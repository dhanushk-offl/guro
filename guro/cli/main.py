import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from typing import Optional
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
@click.version_option(version='1.0.0')
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
        monitor = SystemMonitor()
        if export:
            click.echo("📝 Monitoring data will be exported to 'monitoring_data.csv'")
        
        with console.status("[bold green]Initializing system monitor..."):
            monitor.run_performance_test(
                interval=interval,
                duration=duration,
                export_data=export
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error during monitoring: {str(e)}[/red]")

@cli.command()
@click.option('--type', '-t', 'test_type',
              type=click.Choice(['mini', 'god'], case_sensitive=False),
              help='Type of benchmark test to run')
@click.option('--gpu-only', is_flag=True, help='Run only GPU benchmark')
@click.option('--cpu-only', is_flag=True, help='Run only CPU benchmark')
def benchmark(test_type: str, gpu_only: bool, cpu_only: bool):
    """🔥 Run system benchmarks"""
    try:
        benchmark = SafeSystemBenchmark()
        
        if not test_type:
            test_type = Prompt.ask(
                "Select benchmark type",
                choices=["mini", "god"],
                default="mini"
            )

        with console.status("[bold green]Preparing benchmark..."):
            if test_type == "mini":
                benchmark.mini_test(gpu_only=gpu_only, cpu_only=cpu_only)
            else:
                benchmark.god_test(gpu_only=gpu_only, cpu_only=cpu_only)

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark stopped by user[/yellow]")
    except Exception as e:
        console.print(Panel(
            f"[red]Error during benchmark: {str(e)}[/red]",
            title="⚠️ Benchmark Error",
            border_style="red"
        ))

@cli.command()  # Added the cli decorator here
@click.option('--interval', '-i', 
              type=click.FloatRange(min=0.1, min_open=False),
              default=1.0, 
              help='Update interval in seconds (must be greater than 0.1)')
@click.option('--duration', '-d', 
              type=click.IntRange(min=1, min_open=False),
              default=10, 
              help='Duration to run in seconds (default: 10)')
def heatmap(interval: float, duration: int):
    """🌡️ Display unified system temperature heatmap"""
    try:
        heatmap = SystemHeatmap()
        
        with console.status("[bold green]Initializing system heatmap..."):
            updates = heatmap.run(
                interval=interval,
                duration=duration
            )
            
        console.print(f"\n[green]Heatmap completed after {updates} updates[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Heatmap visualization stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during heatmap visualization: {str(e)}[/red]")

@cli.command(name='list')
def list_features():
    """📋 List all available features and commands"""
    table = Table(title="Guro Commands and Features")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Options", style="yellow")

    commands = {
        "monitor": ("📊 Real-time system monitoring", "-i/--interval, -d/--duration, -e/--export"),
        "benchmark": ("🔥 System benchmarking", "-t/--type [mini/god], --gpu-only, --cpu-only"),
        "heatmap": ("🌡️ Hardware Heatmap Analysis", "-i/--interval, -d/--duration"),
        "about": ("ℹ️  About Guro", "None"),
        "list": ("📋 List all commands", "None")
    }

    for cmd, (desc, opts) in commands.items():
        table.add_row(cmd, desc, opts)

    console.print(table)

@cli.command(name='about')
def about():
    """ℹ️  Display information about Guro"""
    about_text = """[bold cyan]Guro - A Simple System Monitoring & Benchmarking Toolkit[/bold cyan]
        
[green]Version:[/green] 1.0.0
[green]Author:[/green] Dhanush Kandhan
[green]License:[/green] MIT
        
🛠️  A Simple powerful toolkit for system monitoring and optimization.

[yellow]Key Features:[/yellow]
• 📊 Real-time system monitoring
• 💾 Memory management
• 🔥 Performance benchmarking
• 🌡️ Hardware Heatmap Analysis

[blue]GitHub:[/blue] https://github.com/dhanushk-offl/guro
[blue]Documentation:[/blue] https://github.com/dhanushk-offl/guro/wiki"""

    console.print(Panel(about_text, title="About Guro", border_style="blue"))

if __name__ == '__main__':
    cli()