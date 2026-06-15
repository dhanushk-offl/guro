# Network Monitoring Architecture

The network module provides real-time bandwidth monitoring, TCP state analysis, and connection tracking directly from the terminal — with zero additional dependencies beyond psutil.

## Architecture Overview

The `NetworkMonitor` class in `guro.core.network` is built around three concurrent data pipelines:

### 1. Bandwidth Sampling
- **Source**: `psutil.net_io_counters(pernic=True)` — per-interface byte counters
- **Delta computation**: Bytes are sampled at each tick; the difference divided by elapsed time gives bytes/sec. Upload and download histories are stored in `collections.deque` ring buffers (default 60 samples).
- **Sparkline rendering**: A custom `_sparkline()` function maps the last N samples to Unicode block characters (` ▁▂▃▄▅▆▇█`) scaled to the local peak, producing compact ASCII trend graphs.

### 2. TCP State Inspection
- **Source**: `psutil.net_connections(kind='tcp')` — all TCP socket descriptors
- **Aggregation**: Connections are tallied by state (`ESTABLISHED`, `LISTEN`, `TIME_WAIT`, etc.) and displayed as a compact protocol panel.
- **Retransmission metrics**: On Linux, `/proc/net/snmp` is parsed to extract `RetransSegs/OutSegs` ratio and UDP datagram counts.

### 3. Connection Tracking
- **Process mapping**: Each connection is resolved to its owning process via `psutil.Process(pid).name()`, with graceful fallback to `?` on permission errors.
- **Filtering**: Listening sockets without a remote address and `NONE`-state connections are omitted. The top 10 connections are shown in the dashboard.

## Dashboard Layout

The `run_dashboard()` method uses a multi-pane `rich.layout`:

```
┌──────────────────────────────────────────────┐
│  [NET] Guro Network Monitor    Elapsed: 01:23 │
├──────────────────────────────────────────────┤
│  Interface  IP          Link  ↑ Up     ↓ Down │
│  eth0 [OK]  10.0.0.5   1000M  1.2MB/s  3.4MB/s│
├──────────────────────────────────────────────┤
│  Bandwidth History (last 60s)                │
│  ↑ eth0  ████▇▇▇▆▆▆▆▅▅▅▄▄▄▃▃▃▂▂▂▁▁▁  1.2 MB/s│
│  ↓ eth0  ████▇▇▇▆▆▆▆▅▅▅▄▄▄▃▃▃▂▂▂▁▁▁  3.4 MB/s│
├──────────────────────┬───────────────────────┤
│ TCP: ESTAB: 45       │ PID  Process  State   │
│ LISTEN: 12           │ 1234 nginx    LISTEN  │
│ Retrans: 0.02%       │ 5678 curl     ESTAB   │
└──────────────────────┴───────────────────────┘
```

## Subcommands

| Flag | Method | Behavior |
| :--- | :--- | :--- |
| *(none)* | `run_dashboard()` | Interactive live TUI with bandwidth history, protocols, and connections. |
| `--speed` | `show_speed()` | Single-shot upload/download snapshot across all active interfaces. |
| `--interfaces` | `list_interfaces()` | Tabular list of all adapters with IP, MAC, speed, duplex, status. |
| `--connections` | `show_connections()` | Active TCP connections table with PID, process name, and remote address. |

## Cross-Platform Notes

- **Linux**: Full support — `/proc/net/snmp` for protocol stats, `psutil` for everything else.
- **macOS**: Protocol stats (`/proc/net/snmp`) are Linux-only; the dashboard omits that section. All other features work.
- **Windows`: Same as macOS — no SNMP parsing, but bandwidth, connections, and interfaces work via psutil.
- All platforms: TCP connection inspection may require elevated privileges (sudo/Administrator).
