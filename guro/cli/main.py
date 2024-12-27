import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from typing import Optional
from ..core.monitor import SystemMonitor
from ..core.optimizer import SystemOptimizer
from ..core.benchmark import SafeSystemBenchmark

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
[yellow]Advanced System Optimization Toolkit[/yellow]
    """
    console.print(banner)

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """🚀 Guro - Advanced System Optimization Toolkit"""
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
@click.option('--aggressive', '-a', is_flag=True, help='Use aggressive optimization (use with caution)')
@click.option('--silent', '-s', is_flag=True, help='Run optimization without prompts')
def optimize(aggressive: bool, silent: bool):
    """⚡ Optimize system performance"""
    try:
        optimizer = SystemOptimizer()
        
        if not silent:
            if aggressive:
                confirm = Confirm.ask("⚠️  Aggressive optimization might affect system stability. Continue?")
                if not confirm:
                    return

        with console.status("[bold green]Optimizing system performance..."):
            optimizer.optimize_cpu(aggressive=aggressive)
            optimizer.clean_system()
            
        console.print("[green]✅ System optimization completed successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error during optimization: {str(e)}[/red]")

@cli.command()
@click.option('--type', '-t', 'test_type',
              type=click.Choice(['mini', 'god'], case_sensitive=False),
              help='Type of benchmark test to run')
@click.option('--gpu-only', is_flag=True, help='Run only GPU benchmark')
@click.option('--cpu-only', is_flag=True, help='Run only CPU benchmark')
def benchmark(test_type: str, gpu_only: bool, cpu_only: bool, export: bool):
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

@cli.command(name='list')
def list_features():
    """📋 List all available features and commands"""
    table = Table(title="Guro Commands and Features")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Options", style="yellow")

    commands = {
        "monitor": ("📊 Real-time system monitoring", "-i/--interval, -d/--duration, -e/--export"),
        "optimize": ("⚡ System performance optimization", "-a/--aggressive, -s/--silent"),
        "benchmark": ("🔥 System benchmarking", "-t/--type [mini/god], --gpu-only, --cpu-only, -e/--export"),
        "about": ("ℹ️  About Guro", "None"),
        "list": ("📋 List all commands", "None")
    }

    for cmd, (desc, opts) in commands.items():
        table.add_row(cmd, desc, opts)

    console.print(table)

@cli.command(name='about')
def about():
    """ℹ️  Display information about Guro"""
    about_text = """[bold cyan]Guro - Advanced System Optimization Toolkit[/bold cyan]
        
[green]Version:[/green] 1.0.0
[green]Author:[/green] Dhanush Kandhan
[green]License:[/green] MIT
        
🛠️  A powerful toolkit for system monitoring and optimization.

[yellow]Key Features:[/yellow]
• 📊 Real-time system monitoring
• ⚡ CPU optimization
• 💾 Memory management
• 🧹 System cleaning
• 🔥 Performance benchmarking
• 📈 Resource tracking

[blue]GitHub:[/blue] https://github.com/dhanushk-offl/guro
[blue]Documentation:[/blue] https://guro.readthedocs.io"""

    console.print(Panel(about_text, title="About Guro", border_style="blue"))

if __name__ == '__main__':
    cli()