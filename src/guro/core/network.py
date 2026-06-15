import time
import threading
import platform
import csv
import datetime
import urllib.request
import socket
import ssl
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

import psutil
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align

SPARKLINE_CHARS = ' ▁▂▃▄▅▆▇█'
SUBPROCESS_TIMEOUT = 5
SPEED_TEST_DL_URL = "https://speed.cloudflare.com/__down?bytes={}"
SPEED_TEST_UL_URL = "https://speed.cloudflare.com/__up"
SPEED_TEST_CHUNK = 262144
SPEED_TEST_DL_SIZE = 26214400
SPEED_TEST_UL_SIZE = 10485760
SPEED_TEST_TIMEOUT = 15
USE_CASES = [
    ("4K Streaming", 25),
    ("8K Streaming", 50),
    ("Online Gaming", 5),
    ("Video Calls", 4),
    ("Web Browsing", 1),
]
_SYSTEM = platform.system()


def _format_bytes(n: float) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def _format_speed(n: float) -> str:
    return _format_bytes(n) + '/s'


def _sparkline(values: List[float], width: int = 20) -> str:
    if not values:
        return ' ' * width
    recent = list(values)[-width:]
    peak = max(recent) or 1
    max_idx = len(SPARKLINE_CHARS) - 1
    return ''.join(SPARKLINE_CHARS[min(int((v / peak) * max_idx), max_idx)] for v in recent).rjust(width)


def _get_proc_net_snmp() -> Dict:
    stats = {'tcp': {}, 'udp': {}}
    if _SYSTEM != 'Linux':
        return stats
    try:
        with open('/proc/net/snmp') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if parts[0] == 'Tcp:' and i + 1 < len(lines):
                headers = parts[1:]
                values = lines[i + 1].strip().split()[1:]
                for h, v in zip(headers, values):
                    try:
                        stats['tcp'][h] = int(v)
                    except ValueError:
                        stats['tcp'][h] = v
            elif parts[0] == 'Udp:' and i + 1 < len(lines):
                headers = parts[1:]
                values = lines[i + 1].strip().split()[1:]
                for h, v in zip(headers, values):
                    try:
                        stats['udp'][h] = int(v)
                    except ValueError:
                        stats['udp'][h] = v
    except (FileNotFoundError, PermissionError, IndexError):
        pass
    return stats


class NetworkMonitor:
    def __init__(self):
        self._stop_event = threading.Event()
        self._speed_history: Dict[str, deque] = {}
        self._prev_io: Dict = {}
        self._prev_time = time.time()
        self._start_time = time.time()
        self._console = Console()
        self._export_data: List[Dict] = []

    @property
    def running(self):
        return not self._stop_event.is_set()

    @running.setter
    def running(self, value: bool):
        if value:
            self._stop_event.clear()
        else:
            self._stop_event.set()

    def _ensure_history(self, ifaces: List[str], width: int = 60):
        for name in ifaces:
            for suffix in ('_up', '_down'):
                key = name + suffix
                if key not in self._speed_history:
                    self._speed_history[key] = deque(maxlen=width)

    def get_interfaces(self) -> List[Dict]:
        result = []
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for name, stat in stats.items():
            iface = {
                'name': name,
                'isup': stat.isup,
                'duplex': stat.duplex,
                'speed': stat.speed,
                'mtu': stat.mtu,
                'mac': None,
                'ipv4': [],
                'ipv6': [],
            }
            if name in addrs:
                for addr in addrs[name]:
                    if addr.family == psutil.AF_LINK:
                        iface['mac'] = addr.address
                    elif addr.family == 2:
                        iface['ipv4'].append(addr.address)
                    elif addr.family == 23:
                        iface['ipv6'].append(addr.address)
            result.append(iface)
        return result

    def get_active_interfaces(self) -> List[str]:
        return [i['name'] for i in self.get_interfaces() if i['isup']]

    def get_speeds(self) -> Dict[str, Tuple[float, float]]:
        current = psutil.net_io_counters(pernic=True)
        now = time.time()
        elapsed = now - self._prev_time
        if elapsed <= 0:
            elapsed = 0.001
        speeds = {}
        for name, io in current.items():
            if name in self._prev_io:
                up = (io.bytes_sent - self._prev_io[name].bytes_sent) / elapsed
                down = (io.bytes_recv - self._prev_io[name].bytes_recv) / elapsed
                speeds[name] = (max(0, up), max(0, down))
                if name + '_up' in self._speed_history:
                    self._speed_history[name + '_up'].append(max(0, up))
                    self._speed_history[name + '_down'].append(max(0, down))
            else:
                speeds[name] = (0.0, 0.0)
        self._prev_io = current
        self._prev_time = now
        return speeds

    def get_tcp_states(self) -> Dict[str, int]:
        states = {}
        try:
            for conn in psutil.net_connections(kind='tcp'):
                status = conn.status or 'NONE'
                states[status] = states.get(status, 0) + 1
        except (psutil.AccessDenied, PermissionError):
            pass
        return states

    def get_protocol_stats(self) -> Dict:
        return _get_proc_net_snmp()

    def get_connections(self) -> List[Dict]:
        conns = []
        try:
            for c in psutil.net_connections(kind='tcp'):
                if c.status == 'NONE' and not c.raddr:
                    continue
                pname = ''
                try:
                    if c.pid:
                        pname = psutil.Process(c.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                conns.append({
                    'pid': c.pid or 0,
                    'process': pname or '?',
                    'local': f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else '',
                    'remote': f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else '',
                    'status': c.status,
                })
        except (psutil.AccessDenied, PermissionError):
            pass
        return conns

    def _build_header(self, elapsed: float) -> Panel:
        m, s = divmod(int(elapsed), 60)
        elapsed_str = f"{m:02d}:{s:02d}"
        text = f"[bold cyan]🖧  Guro Network Monitor[/bold cyan]    [dim]Elapsed: {elapsed_str}[/dim]"
        return Panel(Align.center(text), style="bold")

    def _build_adapters_panel(self, interfaces: List[Dict], speeds: Dict) -> Panel:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Interface", style="cyan")
        table.add_column("", justify="center", width=3)
        table.add_column("IP", width=15)
        table.add_column("Link", width=8)
        table.add_column("↑ Upload", width=10)
        table.add_column("↓ Download", width=10)
        table.add_column("History", width=22)

        for iface in interfaces:
            name = iface['name']
            status = "✅" if iface['isup'] else "❌"
            ip = iface['ipv4'][0] if iface['ipv4'] else (iface['ipv6'][0] if iface['ipv6'] else "—")
            speed_str = f"{iface['speed']}M" if iface['speed'] > 0 else "?"
            up_speed = _format_speed(speeds.get(name, (0, 0))[0])
            down_speed = _format_speed(speeds.get(name, (0, 0))[1])
            up_hist = _sparkline(list(self._speed_history.get(name + '_up', [])), width=10)
            down_hist = _sparkline(list(self._speed_history.get(name + '_down', [])), width=10)
            hist = f"[green]{up_hist}[/green][blue]{down_hist}[/blue]"
            table.add_row(name, status, ip, speed_str, up_speed, down_speed, hist)

        return Panel(table, title="🖧 Network Adapters", border_style="blue")

    def _build_protocol_panel(self, tcp_states: Dict[str, int], proto_stats: Dict) -> Panel:
        content = []
        state_order = ['ESTABLISHED', 'LISTEN', 'TIME_WAIT', 'CLOSE_WAIT',
                       'SYN_SENT', 'FIN_WAIT1', 'FIN_WAIT2', 'LAST_ACK', 'CLOSING']
        parts = []
        for s in state_order:
            if s in tcp_states:
                parts.append(f"{s}: {tcp_states[s]}")
        if not parts:
            parts = [f"{k}: {v}" for k, v in sorted(tcp_states.items())]
        content.append("TCP: " + " | ".join(parts) if parts else "TCP: —")

        tcp = proto_stats.get('tcp', {})
        if 'RetransSegs' in tcp and 'OutSegs' in tcp:
            retrans_pct = (tcp['RetransSegs'] / max(tcp['OutSegs'], 1)) * 100
            content.append(f"Retrans: {retrans_pct:.2f}% | "
                           f"InSegs: {tcp.get('InSegs', '?')} | "
                           f"OutSegs: {tcp.get('OutSegs', '?')}")
        udp = proto_stats.get('udp', {})
        if 'InDatagrams' in udp:
            content.append(f"UDP: {udp.get('InDatagrams', 0)} in | "
                           f"{udp.get('OutDatagrams', 0)} out | "
                           f"{udp.get('InErrors', 0)} err")

        text = "\n".join(content) if content else "No protocol stats available"
        return Panel(text, title="📊 Protocol Stats", border_style="green")

    def _build_connections_panel(self, connections: List[Dict]) -> Panel:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("PID", width=6, no_wrap=True)
        table.add_column("Process", width=14)
        table.add_column("State", width=11)
        table.add_column("Remote", width=21)

        for c in connections[:10]:
            style = {
                'ESTABLISHED': 'green',
                'LISTEN': 'yellow',
                'TIME_WAIT': 'dim white',
                'CLOSE_WAIT': 'red',
            }.get(c['status'], 'white')
            table.add_row(
                str(c['pid']),
                c['process'][:14],
                Text(c['status'], style=style),
                c['remote'][:21],
            )
        return Panel(table, title="🔌 Top Connections", border_style="magenta")

    def _measure_latency(self) -> Dict:
        result = {'latency_ms': None, 'jitter_ms': None, 'reachable': False}
        times = []
        for _ in range(3):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                start = time.time()
                sock.connect(("1.1.1.1", 443))
                elapsed = (time.time() - start) * 1000
                sock.close()
                times.append(elapsed)
            except (socket.timeout, OSError):
                pass
        if times:
            result['reachable'] = True
            result['latency_ms'] = min(times)
            result['jitter_ms'] = max(times) - min(times) if len(times) > 1 else 0
        return result

    def _download_test(self) -> Dict:
        result = {'speed_bps': 0, 'speed_mbps': 0, 'samples': [], 'error': None}
        url = SPEED_TEST_DL_URL.format(SPEED_TEST_DL_SIZE)
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': '*/*',
            })
            start = time.time()
            with urllib.request.urlopen(req, timeout=SPEED_TEST_TIMEOUT) as resp:
                total = 0
                chunk_start = time.time()
                while True:
                    chunk = resp.read(SPEED_TEST_CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)
                    now = time.time()
                    if now - chunk_start >= 0.2:
                        elapsed = now - chunk_start or 0.001
                        sample_bps = len(chunk) * 8 / elapsed
                        result['samples'].append(sample_bps)
                        chunk_start = now
            elapsed = time.time() - start
            if elapsed > 0:
                result['speed_bps'] = (total * 8) / elapsed
                result['speed_mbps'] = result['speed_bps'] / 1_000_000
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            result['error'] = str(e)
        return result

    def _upload_test(self) -> Dict:
        result = {'speed_bps': 0, 'speed_mbps': 0, 'samples': [], 'error': None}
        data = os.urandom(SPEED_TEST_UL_SIZE)
        try:
            req = urllib.request.Request(
                SPEED_TEST_UL_URL, data=data,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/octet-stream',
                },
                method='POST',
            )
            start = time.time()
            with urllib.request.urlopen(req, timeout=SPEED_TEST_TIMEOUT) as resp:
                total = 0
                chunk_start = time.time()
                while True:
                    chunk = resp.read(SPEED_TEST_CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)
                    now = time.time()
                    if now - chunk_start >= 0.2:
                        elapsed = now - chunk_start or 0.001
                        sample_bps = len(chunk) * 8 / elapsed
                        result['samples'].append(sample_bps)
                        chunk_start = now
            elapsed = time.time() - start
            if elapsed > 0:
                result['speed_bps'] = (SPEED_TEST_UL_SIZE * 8) / elapsed
                result['speed_mbps'] = result['speed_bps'] / 1_000_000
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            result['error'] = str(e)
        return result

    def run_speed_test(self, interface_name: Optional[str] = None):
        interfaces = self.get_interfaces()
        if interface_name:
            target = [i for i in interfaces if i['name'] == interface_name]
        else:
            target = [i for i in interfaces if i['isup'] and i['ipv4']]
        if not target:
            self._console.print("[red]No active network interface found[/red]")
            return
        iface = target[0]

        with self._console.status("[bold yellow]Measuring latency..."):
            latency = self._measure_latency()

        if not latency['reachable']:
            self._console.print("[red]No internet connection detected[/red]")
            return

        with self._console.status("[bold yellow]Testing download speed..."):
            dl = self._download_test()
            if dl['error']:
                self._console.print(f"[red]Download test failed: {dl['error']}[/red]")

        with self._console.status("[bold yellow]Testing upload speed..."):
            ul = self._upload_test()
            if ul['error']:
                self._console.print(f"[red]Upload test failed: {ul['error']}[/red]")

        self._print_speed_report(iface, dl, ul, latency)

    def _format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _print_speed_report(self, iface: Dict, dl: Dict, ul: Dict, latency: Dict):
        renderables = []

        adapter_line = f"[bold cyan]{iface['name']}[/bold cyan]"
        if iface['mac']:
            adapter_line += f"  MAC: {iface['mac']}"
        renderables.append(adapter_line)

        ip_line = f"IP: {iface['ipv4'][0] if iface['ipv4'] else '—'}"
        speed_cap = iface['speed']
        if speed_cap > 0:
            ip_line += f"    Max Link: {speed_cap} Mbps"
        renderables.append(ip_line)

        renderables.append(Text(""))

        dl_mbps = dl.get('speed_mbps', 0)
        ul_mbps = ul.get('speed_mbps', 0)
        dl_samples = dl.get('samples', [])
        ul_samples = ul.get('samples', [])

        speed_table = Table(box=box.SIMPLE, show_header=False)
        speed_table.add_column(justify="right", width=8)
        speed_table.add_column(width=22)
        speed_table.add_column(width=22)

        dl_str = f"[bold green]{dl_mbps:.1f}[/bold green] Mbps" if dl_mbps else "[red]Failed[/red]"
        ul_str = f"[bold green]{ul_mbps:.1f}[/bold green] Mbps" if ul_mbps else "[red]Failed[/red]"
        dl_spark = f"[green]{_sparkline([s / 1_000_000 for s in dl_samples], width=15)}[/green]"
        ul_spark = f"[blue]{_sparkline([s / 1_000_000 for s in ul_samples], width=15)}[/blue]"

        speed_table.add_row("📥 Download", dl_str, dl_spark)
        speed_table.add_row("📤 Upload", ul_str, ul_spark)

        lat_str = f"{latency['latency_ms']:.0f} ms" if latency['latency_ms'] is not None else "—"
        jitter_str = f"{latency['jitter_ms']:.0f} ms" if latency['jitter_ms'] is not None else "—"
        speed_table.add_row("⏱ Latency", f"  {lat_str}", "")
        speed_table.add_row("📊 Jitter", f"  {jitter_str}", "")
        renderables.append(speed_table)

        renderables.append(Text(""))
        renderables.append(Text("[bold]📋 Use Case Suitability[/bold]"))

        cases_table = Table(box=box.SIMPLE, show_header=False)
        cases_table.add_column(width=28)
        cases_table.add_column(width=20)
        dl_mbps_val = dl_mbps if dl_mbps > 0 else 0

        for name, threshold in USE_CASES:
            status = "✅ [green]Supported[/green]" if dl_mbps_val >= threshold else "❌ [red]Needs faster speed[/red]"
            cases_table.add_row(f"  {name} ({threshold} Mbps)", status)

        if dl_mbps_val > 0:
            per_gb_sec = (8 * 1024) / (dl_mbps_val * 1_000_000 / 8) if dl_mbps_val > 0 else 0
            per_10gb_sec = per_gb_sec * 10
            cases_table.add_row("")
            cases_table.add_row("  💾 1 GB file", f"~{self._format_time(per_gb_sec)}")
            cases_table.add_row("  💾 10 GB file", f"~{self._format_time(per_10gb_sec)}")

        renderables.append(cases_table)

        self._console.print(Panel(
            Group(*renderables),
            title="🌐 Network Speed Test Report",
            border_style="blue",
        ))

    def export_csv(self, filepath: Optional[str] = None):
        if not self._export_data:
            self._console.print("[yellow]No data to export[/yellow]")
            return
        if not filepath:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"network_monitor_{ts}.csv"
        with open(filepath, 'w', newline='') as f:
            fields = ['timestamp', 'interface', 'upload_bps', 'download_bps']
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self._export_data)
        self._console.print(f"[green]Data exported to {filepath}[/green]")

    def run_dashboard(self, interval: float = 1.0,
                      duration: Optional[int] = None,
                      export: bool = False):
        interfaces = self.get_interfaces()
        active = [i['name'] for i in interfaces if i['isup']]
        self._ensure_history(active)

        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="adapters"),
            Layout(name="bottom"),
        )
        layout["bottom"].split_row(
            Layout(name="protocols"),
            Layout(name="connections"),
        )

        start = time.time()

        try:
            with Live(layout, refresh_per_second=4, screen=True) as live:
                while self.running:
                    elapsed = time.time() - start
                    if duration and elapsed >= duration:
                        break

                    speeds = self.get_speeds()
                    tcp_states = self.get_tcp_states()
                    proto_stats = self.get_protocol_stats()
                    conns = self.get_connections()

                    if export:
                        for name, (up, down) in speeds.items():
                            self._export_data.append({
                                'timestamp': round(elapsed, 2),
                                'interface': name,
                                'upload_bps': round(up, 2),
                                'download_bps': round(down, 2),
                            })

                    layout["header"].update(self._build_header(elapsed))
                    layout["adapters"].update(
                        self._build_adapters_panel(interfaces, speeds))
                    layout["protocols"].update(
                        self._build_protocol_panel(tcp_states, proto_stats))
                    layout["connections"].update(
                        self._build_connections_panel(conns))

                    time.sleep(interval)

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if export:
                self.export_csv()

    def list_interfaces(self):
        interfaces = self.get_interfaces()
        table = Table(title="Network Adapters", box=box.HEAVY)
        table.add_column("Interface", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("MAC")
        table.add_column("IPv4")
        table.add_column("IPv6")
        table.add_column("Speed")
        table.add_column("Duplex")

        for iface in interfaces:
            status = "✅ Up" if iface['isup'] else "❌ Down"
            mac = iface['mac'] or "—"
            ipv4 = iface['ipv4'][0] if iface['ipv4'] else "—"
            ipv6 = iface['ipv6'][0] if iface['ipv6'] else "—"
            speed = f"{iface['speed']} Mbps" if iface['speed'] > 0 else "—"
            duplex_map = {0: "Half", 1: "Full", 2: "Unknown"}
            duplex = duplex_map.get(iface['duplex'], "—")
            table.add_row(iface['name'], status, mac, ipv4, ipv6, speed, duplex)

        self._console.print(table)

    def show_speed(self):
        self._prev_io = psutil.net_io_counters(pernic=True)
        self._prev_time = time.time()
        time.sleep(1)
        speeds = self.get_speeds()

        table = Table(title="Current Network Speed", box=box.HEAVY)
        table.add_column("Interface", style="cyan")
        table.add_column("Upload", justify="right")
        table.add_column("Download", justify="right")
        total_up = 0.0
        total_down = 0.0

        stats = psutil.net_if_stats()
        for name, (up, down) in sorted(speeds.items()):
            if name in stats and stats[name].isup:
                table.add_row(name, _format_speed(up), _format_speed(down))
                total_up += up
                total_down += down

        table.add_section()
        table.add_row("[bold]Total[/bold]",
                      f"[bold]{_format_speed(total_up)}[/bold]",
                      f"[bold]{_format_speed(total_down)}[/bold]")
        self._console.print(table)

    def show_connections(self):
        conns = self.get_connections()
        if not conns:
            self._console.print("[yellow]No active TCP connections found "
                                "(try running with elevated permissions)[/yellow]")
            return

        table = Table(title=f"Active TCP Connections ({len(conns)} total)",
                      box=box.HEAVY)
        table.add_column("PID", width=6)
        table.add_column("Process", width=16)
        table.add_column("Local", width=22)
        table.add_column("Remote", width=22)
        table.add_column("State", width=12)

        style_map = {
            'ESTABLISHED': 'green',
            'LISTEN': 'yellow',
            'TIME_WAIT': 'dim white',
        }
        for c in conns[:30]:
            table.add_row(
                str(c['pid']),
                c['process'][:16],
                c['local'],
                c['remote'],
                Text(c['status'], style=style_map.get(c['status'], 'white')),
            )

        self._console.print(table)
        if len(conns) > 30:
            self._console.print(
                f"[dim]Showing 30 of {len(conns)} connections[/dim]")
