# System Monitoring Architecture

The monitoring module in Guro is designed for periodic data acquisition and real-time visualization.

## Data Acquisition Layer

Guro interfaces with the operating system's kernel-level telemetry through the following interfaces:
- **Cross-Platform**: `psutil` is utilized for process management, CPU load average collection, and memory envelope analysis.
- **Real-Time Sampling**: Metrics are sampled at a configurable interval (default 1.0s). Monotonic deadlines account for collection time and skip missed ticks. Vendor subprocesses have timeouts but can still delay a frame.

## Visualization Engine

The monitoring interface is implemented using `rich.layout`, allowing for a multi-pane, structured display:
- **Header**: Displays system metadata (OS, uptime, current load).
- **Graphs Pane**: Renders real-time ASCII line charts using a custom historic data buffer (`ASCIIGraph`).
- **GPU Pane**: Dynamically scales to show metrics for all discovered Graphics Processing Units.
- **Process Pane**: Provides a sorted view of high-impact system processes.

## Update Logic

To prevent terminal flickering (splashing), Guro utilizes `rich.live`. This ensures that only the modified portions of the layout are re-rendered, providing a smooth, high-fidelity user experience.

## Collection and export

`SystemMonitor.collect_sample()` returns a plain snapshot used by both the TUI and structured output. Process CPU counters persist across sampling cycles, requiring one process scan without an artificial sleep. Hardware adapter discovery happens at startup; vendor GPU metrics refresh every five seconds. GPU hot-plug adapter discovery requires restarting monitoring.

CSV exports write and flush each row immediately; JSON and JSONL share the streaming writer. In-memory recent export history is capped at 60 samples. Exceptions close writers and preserve already-written rows. Static package metadata and dependencies live in pyproject.toml.
