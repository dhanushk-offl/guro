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

## Snyk SNYK-OS-PYTHON-0009

This error means dependency installation failed before a vulnerability scan could complete. It does not identify a specific vulnerable package. See [Snyk's error catalog](https://docs.snyk.io/scan-fix-and-prevent/prevent/error-catalog#snyk-os-python-0009).

The requirements files previously referenced the local project using `.`, `.[amd]`, and `.[test]`. These are valid local pip inputs, but Snyk's SCM scanner [does not support relative project paths or nested requirements](https://docs.snyk.io/supported-languages/supported-languages-list/python/scm-integrations-and-python#scm-repositories-and-pip). Each manifest now contains its complete public dependency list, generated from `pyproject.toml`. Run `python scripts/sync_requirements.py --check` to detect drift.

The root `.snyk` file explicitly selects Python 3.12 rather than relying on organization defaults. This is compatible with Guro's Python minimum and provides prebuilt AMD binding wheels. AMD packages remain Linux-only; Windows WMI dependencies are skipped on Linux. This removes the local-project installation dependency and avoids building Guro during a requirements scan.

If installation still fails, inspect the first failing package and installer error in Snyk. Missing wheels, compiler/system headers, registry access, and incompatible interpreter settings can also produce this generic code. Reproduce with Python 3.12 in a fresh environment using `pip install -r <manifest>` followed by `pip check`.
