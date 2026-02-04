# Troubleshooting and Diagnostics

This guide provides technical resolutions for common operational anomalies within the Guro toolkit.

## 1. Temperature Data Unavailable

### Symptom
Thermal heatmap displays `0.0°C` or `N/A`.

### Resolutions
- **Windows**: Ensure the terminal is running as **Administrator**. WMI thermal zones are restricted by the OS.
- **Linux**: Verify that `lm-sensors` is installed and configured. Run `sudo sensors-detect` to discover motherboard sensor chips.
- **General**: Ensure your hardware exposes thermal data through standard interfaces (ACPI/SMC). Virtual machines often do not expose these sensors.

## 2. GPU Not Detected

### Symptom
`guro gpu` reports no available devices or falls back to integrated graphics only.

### Resolutions
- **NVIDIA**: Ensure `nvidia-smi` is in your system PATH and the latest NVIDIA drivers with NVML support are installed.
- **AMD**: On Linux, ensure the user has permissions to access `/dev/kfd` and that the ROCm stack is correctly initialized.
- **Integrated GPUs**: Guro utilizes WMI on Windows and `lspci` on Linux to detect integrated chips. Verify driver installation if the device is missing.

## 3. TUI Rendering Anomalies

### Symptom
Flickering, layout breakages, or overlapping text.

### Resolutions
- **Terminal Compatibility**: Guro requires a modern terminal emulator with UTF-8 support (e.g., Windows Terminal, iTerm2, Alacritty, or VS Code terminal).
- **Font Rendering**: Ensure your terminal uses a monospace font to prevent ASCII graph distortions.
- **Resolution**: A minimum terminal width of 80 characters is recommended for the dashboard layout.

## 4. Permission Denied Errors

### Symptom
Exceptions during initialization of the monitoring or benchmarking modules.

### Resolutions
- **WMI Errors**: Often resolved by elevating the user context.
- **Path Issues**: Ensure the installation directory is in your system PATH, especially when using `pip install --user`.
