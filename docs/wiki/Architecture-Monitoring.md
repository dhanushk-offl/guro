# System Monitoring Architecture

The monitoring module in Guro is designed for high-concurrency data acquisition and real-time visualization.

## Data Acquisition Layer

Guro interfaces with the operating system's kernel-level telemetry through the following interfaces:
- **Cross-Platform**: `psutil` is utilized for process management, CPU load average collection, and memory envelope analysis.
- **Real-Time Sampling**: Metrics are sampled at a configurable interval (default 1.0s) using non-blocking I/O to ensure the TUI remains responsive.

## Visualization Engine

The monitoring interface is implemented using `rich.layout`, allowing for a multi-pane, structured display:
- **Header**: Displays system metadata (OS, uptime, current load).
- **Graphs Pane**: Renders real-time ASCII line charts using a custom historic data buffer (`ASCIIGraph`).
- **GPU Pane**: Dynamically scales to show metrics for all discovered Graphics Processing Units.
- **Process Pane**: Provides a sorted view of high-impact system processes.

## Update Logic

To prevent terminal flickering (splashing), Guro utilizes `rich.live`. This ensures that only the modified portions of the layout are re-rendered, providing a smooth, high-fidelity user experience.
