import time
import psutil
from rich.console import Console
from rich.table import Table

class NetworkMonitor:
    def __init__(self):
        self.console = Console()

    def get_network_stats(self):
        try:
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            }
        except Exception as e:
            self.console.print(f"[red]Error fetching network stats: {str(e)}[/red]")
            return {}

    def run(self, interval: float = 1.0, duration: int = None):
        if interval <= 0:
            self.console.print("[red]Interval must be greater than zero.[/red]")
            return
        if duration and duration <= 0:
            self.console.print("[red]Duration must be greater than zero if provided.[/red]")
            return

        print(f"Monitoring with interval: {interval}s and duration: {duration if duration else 'No limit'}")
        
        start_time = time.time()
        prev_stats = self.get_network_stats()

        self.console.print("[cyan]Starting Network Monitoring... Press Ctrl+C to stop.[/cyan]")

        try:
            while True:
                elapsed_time = time.time() - start_time
                if duration and elapsed_time > duration:
                    break

                current_stats = self.get_network_stats()

                # Additional error handling
                if not current_stats:
                    self.console.print("[red]Failed to retrieve current network stats.[/red]")
                    break

                sent_speed = (current_stats["bytes_sent"] - prev_stats["bytes_sent"]) / interval if current_stats["bytes_sent"] != prev_stats["bytes_sent"] else 0
                recv_speed = (current_stats["bytes_recv"] - prev_stats["bytes_recv"]) / interval if current_stats["bytes_recv"] != prev_stats["bytes_recv"] else 0

                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Metric")
                table.add_column("Value", justify="right")

                table.add_row("Upload Speed", f"{sent_speed / 1024:.2f} KB/s")
                table.add_row("Download Speed", f"{recv_speed / 1024:.2f} KB/s")
                table.add_row("Total Packets Sent", str(current_stats["packets_sent"]))
                table.add_row("Total Packets Received", str(current_stats["packets_recv"]))

                self.console.clear()
                self.console.print(table)

                prev_stats = current_stats

                time.sleep(interval)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Monitoring stopped by user.[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error occurred during monitoring: {str(e)}[/red]")
