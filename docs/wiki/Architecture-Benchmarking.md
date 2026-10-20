# CPU and memory benchmarking

The mini and god presets request total elapsed budgets of 30 and 60 seconds. Default runs split the budget between CPU and memory; CPU-only uses the complete budget for matrix multiplication. Actual elapsed time is reported separately, since collection and an in-progress operation can exceed the deadline.

CPU work repeatedly multiplies a deterministic 256 by 256 float64 matrix by its transpose into a reusable output buffer. Reports include iteration count and GFLOP/s, computed using 2N³ operations per multiply and time spent in the multiplication calls. NumPy/BLAS settings determine thread usage and influence results. The report records NumPy version and common BLAS thread environment variables.

Memory work copies a pre-touched buffer to a reusable destination. Both buffers together are limited to 32 MiB and 1% of currently available memory. Allocation is rejected at 90% system memory usage or when the budget is too small. Payload bytes copied divided by time spent in copy calls gives decimal MB/s. This is a cached memory copy microbenchmark; it is not a claim of peak DRAM bandwidth or VRAM performance.

Safety checks run between operations, at most four times per second. A measured component temperature at or above 90 Celsius or memory usage at or above 90% aborts the run with a reason. High CPU utilization alone does not abort. Sensor coverage is recorded; unavailable sensors provide no thermal protection. Individual operations and external sensor queries are not preempted.

GPU workload execution is unsupported. GPU-only requests return an explicit unsupported result immediately; default runs report that limitation alongside CPU and memory results. Use the GPU command for telemetry.

Reports distinguish completed, aborted, cancelled, failed, and unsupported outcomes. CLI aborts, failures, and unsupported GPU requests have nonzero exit statuses. Tests substitute controlled workloads and clocks instead of running full stress tests.
