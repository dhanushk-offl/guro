# guro/cli/main.py
import click
from rich.console import Console
from rich.panel import Panel
from ..core.monitor import SystemMonitor
from ..core.optimizer import SystemOptimizer

console = Console()

@click.group()
def cli():
    """Guro - Advanced System Optimization Toolkit"""
    pass

@cli.command()
def monitor():
    """Monitor system resources and performance"""
    monitor = SystemMonitor()
    monitor.display_system_info()

@cli.command()
def optimize():
    """Optimize system performance"""
    optimizer = SystemOptimizer()
    optimizer.optimize_cpu()
    optimizer.clean_system()

@cli.command(name='about')
def about():
    """Display information about Guro"""
    console.print(Panel.fit(
        """[bold cyan]Guro - Advanced System Optimization Toolkit[/bold cyan]
        
[green]Version:[/green] 1.0.0
[green]Author:[/green] Dhanush Kandhan
[green]License:[/green] MIT
        
A powerful toolkit for system monitoring and optimization.
Features include:
• Real-time system monitoring
• CPU optimization
• Memory management
• System cleaning
• Performance tuning
        
[yellow]GitHub:[/yellow] https://github.com/dhanushk-offl/guro""",
        title="About Guro",
        border_style="blue"
    ))
