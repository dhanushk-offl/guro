# Troubleshooting and diagnostics

Run `guro doctor` first. Use `guro doctor --format json --output diagnostics.json` to save available tools, sensors, connection permissions, and GPU workload capabilities for inspection.

## Missing temperatures

`N/A` means the component has no valid exposed reading. Linux collection uses psutil/hwmon; Windows requires OpenHardwareMonitor WMI temperature sensors. macOS attempts powermetrics with the existing permissions. NVIDIA temperatures can also come from nvidia-smi. Virtual machines and some hardware do not expose these sensors.

Guro never installs drivers or invokes sudo automatically. Check the sensor provider and current access permissions on the host. `guro heatmap --estimates` optionally fills missing readings with labeled estimates; those values cannot substitute for measured temperatures or benchmark thermal protection.

## GPU not detected or workload unsupported

Check whether nvidia-smi, rocm-smi, or lspci is available in the environment where Guro runs. Windows has a WMI adapter fallback. Adapter discovery may provide a name without utilization, memory, or temperature measurements. There is no native Apple GPU discovery provider.

GPU workload execution is not implemented. `guro benchmark --gpu-only` returns an unsupported outcome with a nonzero status. Use `guro gpu` for telemetry. Restart monitoring after attaching a GPU because hardware adapter discovery is cached at startup.

## Benchmark aborts

Reports include `status`, `stop_reason`, actual elapsed time, and thermal coverage. The default limits stop at 90% system memory use or a measured component temperature of 90 Celsius. CPU utilization reaching 100% alone does not abort a run. An unavailable sensor provides no thermal protection. Throughput depends on the NumPy/BLAS build, threading configuration, cache effects, and other system activity.

## Permission failures

An empty TCP connection list and denied connection inspection have different statuses in diagnostics and structured output. Host or sandbox policy may also deny interface queries; the command then reports an error with a nonzero exit status. Review the relevant host permissions before changing how the command is launched.

## Terminal layout or automation output

Use a UTF-8 terminal, a monospace font, and sufficient terminal space for the dashboard. For scripts, select `--format json` or `--format jsonl` to avoid terminal rendering. JSON monitoring writes an array; JSONL writes one sample per line. Use JSONL when a session may be terminated abruptly.

CSV exports use `--export`; structured exports use `--format`. Both support `--output PATH`, replacing an existing destination. Already-written samples are flushed, and handled collection errors close the writer. Fix unwritable paths or insufficient storage before retrying an export.

## Installation compatibility

Python 3.9 or later is required. The minimum follows the Pygments 2.20 security requirement. Install development dependencies with `pip install -e ".[test]"` and use the package's `pyproject.toml` as the dependency source.
