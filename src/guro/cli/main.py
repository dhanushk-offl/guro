import json
import logging
from contextlib import nullcontext

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
from ..core.network import NetworkMonitor
from ..core.telemetry import Schedule, SampleWriter, timestamp
from ..core.diagnostics import capabilities

console = Console()
logger = logging.getLogger(__name__)


def output_options(func):
    func = click.option('--output', type=click.Path(dir_okay=False), help='Write output to this file')(func)
    return click.option('--format', 'fmt', type=click.Choice(['text', 'json', 'jsonl']), default='text', show_default=True)(func)


def emit_result(value, fmt, output):
    with (open(output, 'w', encoding='utf-8') if output else nullcontext(click.get_text_stream('stdout'))) as stream:
        if fmt == 'text':
            Console(file=stream).print_json(data=value)
        else:
            stream.write(json.dumps(value, allow_nan=False) + '\n')
            stream.flush()


def stream_samples(collect, interval, duration, fmt, output):
    schedule = Schedule(interval, duration)
    with (open(output, 'w', encoding='utf-8') if output else nullcontext(click.get_text_stream('stdout'))) as stream:
        with SampleWriter(stream, fmt) as writer:
            try:
                while not schedule.finished:
                    writer.write(collect())
                    schedule.wait()
            except KeyboardInterrupt:
                pass


def fail(action, error):
    logger.debug('%s failed', action, exc_info=True)
    raise click.ClickException(f'{action} failed: {error}') from error



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
    pass


@cli.command()
@click.option('--interval', '-i', type=click.FloatRange(min=0.1), default=1.0, help='Monitoring interval in seconds')
@click.option('--duration', '-d', default=None, type=click.IntRange(min=1), help='Monitoring duration in seconds')
@click.option('--export', '-e', is_flag=True, help='Export monitoring data to CSV')
@output_options
def monitor(interval: float, duration: Optional[int], export: bool, fmt: str, output: Optional[str]):
    """📊 Monitor system resources and performance in real-time"""
    try:
        if export and fmt != 'text':
            raise ValueError('Use --export for CSV or --format for structured output')
        if output and fmt == 'text' and not export:
            raise ValueError('--output requires --export or a structured --format')
        mon = SystemMonitor()
        if fmt != 'text':
            stream_samples(mon.collect_sample, interval, duration, fmt, output)
            return
        if export:
            click.echo("📝 Monitoring data will be exported to a timestamped CSV file")

        with console.status("[bold green]Initializing system monitor..."):
            mon.run_performance_test(
                interval=interval,
                duration=duration,
                export_data=export, output_path=output
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as exc:
        fail('Monitoring', exc)


@cli.command()
@click.option('--type', '-t', 'test_type',
              type=click.Choice(['mini', 'god'], case_sensitive=False),
              help='Type of benchmark test to run')
@click.option('--gpu-only', is_flag=True, help='Request a GPU workload (currently unsupported)')
@click.option('--cpu-only', is_flag=True, help='Run only CPU benchmark')
@output_options
def benchmark(test_type: str, gpu_only: bool, cpu_only: bool, fmt: str, output: Optional[str]):
    """🔥 Run system benchmarks"""
    if gpu_only and cpu_only:
        raise click.UsageError('Use only one of --gpu-only or --cpu-only')
    if output and fmt == 'text':
        raise click.UsageError('--output requires --format json or jsonl')
    try:
        bench = SafeSystemBenchmark()

        if not test_type and fmt != 'text':
            test_type = 'mini'
        if not test_type:
            test_type = Prompt.ask(
                "Select benchmark type",
                choices=["mini", "god"],
                default="mini"
            )

        method = bench.mini_test if test_type.lower() == 'mini' else bench.god_test
        results = method(gpu_only=gpu_only, cpu_only=cpu_only, display=fmt == 'text')
        if fmt != 'text':
            emit_result(results, fmt, output)
        if results['status'] in ('aborted', 'unsupported', 'failed'):
            raise click.ClickException(results.get('stop_reason') or results['status'])
    except KeyboardInterrupt:
        raise click.Abort()
    except click.ClickException:
        raise
    except Exception as exc:
        fail('Benchmark', exc)


@cli.command()
@output_options
def gpu(fmt: str, output: Optional[str]):
    """🚀 Quickly check all available GPUs and their current status"""
    from ..core.monitor import GPUDetector
    from rich.table import Table
    from rich import box

    if fmt != 'text':
        emit_result(GPUDetector.get_all_gpus(), fmt, output)
        return
    if output:
        raise click.UsageError('--output requires --format json or jsonl')

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
@click.option('--estimates', is_flag=True, help='Explicitly enable labeled estimates for unavailable sensors')
@output_options
def heatmap(interval: float, duration: int, estimates: bool, fmt: str, output: Optional[str]):
    """🌡️ Display unified system temperature heatmap"""
    try:
        hm = SystemHeatmap(estimates=estimates)
        if fmt != 'text':
            stream_samples(lambda: {'timestamp': timestamp(), 'temperatures': {
                c: reading.to_dict() for c, reading in hm.get_readings().items()
            }}, interval, duration, fmt, output)
            return
        if output:
            raise ValueError('--output requires --format json or jsonl')

        with console.status("[bold green]Initializing system heatmap..."):
            updates = hm.run(
                interval=interval,
                duration=duration
            )

        console.print(f"\n[green]Heatmap completed after {updates} updates[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Heatmap visualization stopped by user[/yellow]")
    except Exception as exc:
        fail('Heatmap', exc)


@cli.command()
@click.option('--interfaces', is_flag=True, help='List all network interfaces')
@click.option('--speed', is_flag=True, help='Show current network speed')
@click.option('--connections', 'show_connections', is_flag=True, help='Show active TCP connections')
@click.option('--interval', '-i',
              type=click.FloatRange(min=0.1, min_open=False),
              default=1.0,
              help='Update interval in seconds')
@click.option('--duration', '-d',
              type=click.IntRange(min=1, min_open=False),
              default=None,
              help='Monitoring duration in seconds')
@click.option('--export', '-e', is_flag=True, help='Export monitoring data to CSV')
@output_options
def network(interfaces: bool, speed: bool, show_connections: bool,
            interval: float, duration: Optional[int], export: bool, fmt: str, output: Optional[str]):
    """[NET] Monitor network interfaces, bandwidth, and connections"""
    mode_flags = [interfaces, speed, show_connections]
    if sum(bool(v) for v in mode_flags) > 1:
        raise click.UsageError(
            "Use only one of --interfaces, --speed, or --connections"
        )

    try:
        if export and (fmt != 'text' or any(mode_flags)):
            raise ValueError('--export is supported by the text dashboard; use --format for other output')
        if output and fmt == 'text' and not export:
            raise ValueError('--output requires --export or a structured --format')
        net = NetworkMonitor()
        if fmt != 'text':
            if interfaces:
                emit_result(net.get_interfaces(), fmt, output)
            elif show_connections:
                connections = net.get_connections()
                emit_result({'connections': connections, 'status': net.connection_status}, fmt, output)
            elif speed:
                net.get_speeds()
                import time
                time.sleep(1)
                emit_result(net.get_speeds(), fmt, output)
            else:
                stream_samples(net.collect_sample, interval, duration, fmt, output)
            return

        if interfaces:
            net.list_interfaces()
        elif speed:
            net.show_speed()
        elif show_connections:
            net.show_connections()
        else:
            net.run_dashboard(
                interval=interval,
                duration=duration,
                export=export, output_path=output
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Network monitoring stopped by user[/yellow]")
    except Exception as exc:
        fail('Network monitoring', exc)


@cli.command()
@output_options
def doctor(fmt: str, output: Optional[str]):
    """Explain available tools, sensors, and permissions without changing the system."""
    try:
        emit_result(capabilities(), fmt, output)
    except Exception as exc:
        fail('Diagnostics', exc)


@cli.command(name='list')
def list_features():
    """📋 List all available features and commands"""
    table = Table(title="Guro Commands and Features")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Options", style="yellow")

    commands = {
        "doctor": ("Sensor and tool diagnostics", "--format, --output"),
        "monitor": ("📊 Real-time system monitoring", "-i, -d, -e"),
        "gpu": ("🚀 Dedicated GPU status check", "None"),
        "benchmark": ("🔥 System benchmarking", "-t [mini/god], --gpu-only"),
        "heatmap": ("🌡️ Hardware Heatmap Analysis", "-i, -d"),
        "network": ("[NET] Network monitoring dashboard", "--interfaces, --speed, --connections"),
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
• [NET] Real-time network monitoring (bandwidth, connections, protocols)

[blue]GitHub:[/blue] https://github.com/dhanushk-offl/guro
[blue]Website:[/blue] https://guro.pages.dev/
[blue]Documentation:[/blue] https://guro.pages.dev/"""

    console.print(Panel(about_text, title="About Guro", border_style="blue"))


if __name__ == '__main__':
    cli()
