import psutil
import os
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from typing import Dict, List, Optional
import json
import time
from datetime import datetime
import getpass

console = Console()

def show_sudo_warning():
    """Display warning about sudo usage"""
    console.print(Panel.fit(
        "[bold red]⚠️  WARNING: Sudo Required[/bold red]\n\n"
        "This command must be run with sudo privileges.\n"
        "Please use: [bold white]sudo guro optimize[/bold white] instead of direct command.\n\n"
        "Example usage:\n"
        "✓ [green]sudo guro optimize --aggressive[/green]\n"
        "✓ [green]sudo guro optimize --silent[/green]\n"
        "✗ [red]guro optimize[/red]\n",
        title="🔐 Sudo Required",
        border_style="red"
    ))

class PermissionChecker:
    @staticmethod
    def is_root() -> bool:
        return getpass.getuser()  == 0

    @staticmethod
    def check_command_availability(command: str) -> bool:
        try:
            subprocess.run(['which', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def show_permission_warning(console: Console):
        console.print(Panel.fit(
            "[bold yellow]⚠️  Permission Requirements[/bold yellow]\n\n"
            "This optimizer requires administrative privileges to perform system optimizations.\n\n"
            "[bold cyan]Options to run the optimizer:[/bold cyan]\n"
            "1. Run the script with sudo: [white]sudo python optimizer.py[/white]\n"
            "2. Run with limited optimizations: Some features will be disabled\n\n"
            "[bold red]Required permissions for full optimization:[/bold red]\n"
            "• GPU settings modification\n"
            "• CPU governor adjustment\n"
            "• System cache management\n"
            "• Process priority modification\n",
            title="🔐 System Permissions Required",
            border_style="yellow"
        ))

class GPUOptimizer:
    def __init__(self, console: Console):
        self.optimization_status = []
        self.console = console
        
    def _detect_gpu_vendor(self) -> str:
        try:
            # Check NVIDIA
            if self._check_nvidia():
                return 'nvidia'
            # Check AMD
            elif self._check_amd():
                return 'amd'
            # Check Intel
            elif self._check_intel():
                return 'intel'
        except:
            pass
        return 'unknown'

    def _check_nvidia(self) -> bool:
        return PermissionChecker.check_command_availability('nvidia-smi')

    def _check_amd(self) -> bool:
        return PermissionChecker.check_command_availability('rocm-smi')

    def _check_intel(self) -> bool:
        return os.path.exists('/sys/class/drm/card0/device/vendor')

    def _run_command(self, command: List[str], action: str) -> Dict:
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return {"action": action, "status": "success"}
        except subprocess.CalledProcessError as e:
            return {"action": action, "status": "failed", "error": f"Permission denied or command failed: {e}"}
        except Exception as e:
            return {"action": action, "status": "failed", "error": str(e)}

    def optimize_nvidia_gpu(self) -> Dict:
        status = {"type": "NVIDIA GPU", "optimizations": []}
        
        if not PermissionChecker.is_root():
            status["optimizations"].append({
                "action": "GPU optimization",
                "status": "skipped",
                "error": "Root permissions required"
            })
            return status

        commands = [
            (['nvidia-smi', '--persistence-mode=1'], "Enable persistence mode"),
            (['nvidia-smi', '--power-limit=0'], "Optimize power limit"),
            (['nvidia-smi', '-c', '3'], "Enable compute mode")
        ]

        for cmd, action in commands:
            status["optimizations"].append(self._run_command(cmd, action))
        
        return status

    def optimize_amd_gpu(self) -> Dict:
        status = {"type": "AMD GPU", "optimizations": []}
        
        if not PermissionChecker.is_root():
            status["optimizations"].append({
                "action": "GPU optimization",
                "status": "skipped",
                "error": "Root permissions required"
            })
            return status

        commands = [
            (['rocm-smi', '--setperflevel', 'high'], "Set performance level"),
            (['rocm-smi', '--setpoweroverdrive', '100'], "Optimize power limit"),
            (['rocm-smi', '--setcomputemode', '1'], "Enable compute mode")
        ]

        for cmd, action in commands:
            status["optimizations"].append(self._run_command(cmd, action))

        return status

    def optimize_intel_gpu(self) -> Dict:
        status = {"type": "Intel GPU", "optimizations": []}
        
        if not PermissionChecker.is_root():
            status["optimizations"].append({
                "action": "GPU optimization",
                "status": "skipped",
                "error": "Root permissions required"
            })
            return status

        try:
            paths = {
                '/sys/class/drm/card0/device/power_dpm_force_performance_level': 'high',
                '/sys/class/drm/card0/device/power_dpm_state': 'performance'
            }
            
            for path, value in paths.items():
                if os.path.exists(path):
                    with open(path, 'w') as f:
                        f.write(value)
                    status["optimizations"].append({
                        "action": f"Optimize {path.split('/')[-1]}",
                        "status": "success"
                    })
                
        except Exception as e:
            status["optimizations"].append({
                "action": "GPU optimization",
                "status": "failed",
                "error": str(e)
            })
        
        return status

class SystemOptimizer:
    def __init__(self):
        self.console = Console()
        self.gpu_optimizer = GPUOptimizer(self.console)
        self.optimization_history = []
        self.is_root = PermissionChecker.is_root()

    def create_status_table(self, optimization_data: Dict) -> Table:
        table = Table(title=f"Optimization Results for {optimization_data['type']}")
        table.add_column("Action", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        for opt in optimization_data["optimizations"]:
            status_color = {
                "success": "green",
                "skipped": "yellow",
                "failed": "red"
            }.get(opt["status"], "red")
            
            details = opt.get("error", "Completed successfully")
            table.add_row(
                opt["action"],
                f"[{status_color}]{opt['status']}[/{status_color}]",
                details
            )
        
        return table

    def optimize_gpu(self):
        try:
            vendor = self.gpu_optimizer._detect_gpu_vendor()
            optimization_results = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            
            if not self.is_root:
                self.console.print(Panel.fit(
                    "[yellow]⚠️  Running GPU optimization with limited permissions[/yellow]",
                    border_style="yellow"
                ))
            
            if vendor == 'nvidia':
                optimization_results.update(self.gpu_optimizer.optimize_nvidia_gpu())
            elif vendor == 'amd':
                optimization_results.update(self.gpu_optimizer.optimize_amd_gpu())
            elif vendor == 'intel':
                optimization_results.update(self.gpu_optimizer.optimize_intel_gpu())
            else:
                optimization_results.update({"type": "Unknown GPU", "optimizations": [
                    {"action": "GPU detection", "status": "failed", "error": "No supported GPU found"}
                ]})
            
            self.optimization_history.append(optimization_results)
            self.console.print(Panel.fit(self.create_status_table(optimization_results)))
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error optimizing GPU: {str(e)}[/red]")
            return False

    def optimize_cpu(self, aggressive: bool = False):
        try:
            optimization_results = {
                "type": "CPU",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "optimizations": []
            }
            
            if not self.is_root:
                optimization_results["optimizations"].append({
                    "action": "CPU optimization",
                    "status": "skipped",
                    "error": "Root permissions required"
                })
            else:
                # Standard optimizations
                commands = [
                    (['cpupower', 'frequency-set', '-g', 'performance'], "Set CPU governor"),
                    (['sysctl', '-w', 'kernel.sched_min_granularity_ns=10000000'], "Optimize CPU scheduler")
                ]
                
                # Add aggressive optimizations if enabled
                if aggressive:
                    commands.extend([
                        (['sysctl', '-w', 'kernel.sched_migration_cost_ns=5000000'], "Aggressive scheduler tuning"),
                        (['sysctl', '-w', 'kernel.sched_autogroup_enabled=0'], "Disable autogroup"),
                        (['sysctl', '-w', 'kernel.sched_latency_ns=5000000'], "Minimize scheduling latency")
                    ])

                for cmd, action in commands:
                    try:
                        subprocess.run(cmd, check=True)
                        optimization_results["optimizations"].append({
                            "action": action,
                            "status": "success"
                        })
                    except Exception as e:
                        optimization_results["optimizations"].append({
                            "action": action,
                            "status": "failed",
                            "error": str(e)
                        })

            self.optimization_history.append(optimization_results)
            self.console.print(Panel.fit(self.create_status_table(optimization_results)))
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error optimizing CPU: {str(e)}[/red]")
            return False

    def clean_system(self):
        try:
            optimization_results = {
                "type": "System Cleanup",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "optimizations": []
            }
            
            if not self.is_root:
                optimization_results["optimizations"].append({
                    "action": "System cleanup",
                    "status": "skipped",
                    "error": "Root permissions required"
                })
            else:
                cleanup_commands = [
                    (['sync'], "Sync file systems"),
                    (['swapoff', '-a'], "Disable swap"),
                    (['swapon', '-a'], "Enable swap"),
                    (['apt-get', 'clean'], "Clean package cache"),
                    (['apt-get', 'autoremove', '-y'], "Remove unused packages"),
                    (['sysctl', '-w', 'vm.swappiness=10'], "Set swappiness"),
                    (['sysctl', '-w', 'vm.vfs_cache_pressure=50'], "Set cache pressure")
                ]

                for cmd, action in cleanup_commands:
                    try:
                        subprocess.run(cmd, check=True)
                        optimization_results["optimizations"].append({
                            "action": action,
                            "status": "success"
                        })
                    except Exception as e:
                        optimization_results["optimizations"].append({
                            "action": action,
                            "status": "failed",
                            "error": str(e)
                        })
            
            self.optimization_history.append(optimization_results)
            self.console.print(Panel.fit(self.create_status_table(optimization_results)))
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error cleaning system: {str(e)}[/red]")
            return False

    def optimize_all(self):
        """Perform all optimizations and show combined results"""
        if not self.is_root:
            PermissionChecker.show_permission_warning(self.console)
            if not Confirm.ask("[yellow]Continue with limited optimizations?[/yellow]"):
                return

        self.console.print(Panel.fit(
            "[bold blue]Starting system-wide optimization...[/bold blue]",
            border_style="blue"
        ))
        
        self.optimize_gpu()
        self.optimize_cpu()
        self.clean_system()
        
        # Show summary table
        summary_table = Table(title="Optimization Summary")
        summary_table.add_column("Component", style="cyan")
        summary_table.add_column("Status", style="green")
        summary_table.add_column("Timestamp", style="yellow")
        
        for result in self.optimization_history:
            success_count = len([opt for opt in result["optimizations"] if opt["status"] == "success"])
            skip_count = len([opt for opt in result["optimizations"] if opt["status"] == "skipped"])
            total_count = len(result["optimizations"])
            
            if skip_count == total_count:
                status = f"[yellow]Skipped - Root required[/yellow]"
            else:
                status = f"[green]{success_count}/{total_count} optimizations successful[/green]"
            
            summary_table.add_row(
                result["type"],
                status,
                result["timestamp"]
            )
        
        self.console.print(Panel.fit(summary_table))

if __name__ == "__main__":
    optimizer = SystemOptimizer()
    optimizer.optimize_all()
# import psutil
# import os
# import subprocess
# from rich.console import Console
# from rich.table import Table
# from rich.panel import Panel
# from typing import Dict, List, Optional
# import json
# import time
# from datetime import datetime

# class GPUOptimizer:
#     def __init__(self):
#         self.optimization_status = []
        
#     def _detect_gpu_vendor(self) -> str:
#         try:
#             # Check NVIDIA
#             if subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
#                 return 'nvidia'
#             # Check AMD
#             elif subprocess.run(['rocm-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
#                 return 'amd'
#             # Check Intel
#             elif os.path.exists('/sys/class/drm/card0/device/vendor') and 'Intel' in open('/sys/class/drm/card0/device/vendor').read():
#                 return 'intel'
#         except:
#             pass
#         return 'unknown'

#     def optimize_nvidia_gpu(self) -> Dict:
#         status = {"type": "NVIDIA GPU", "optimizations": []}
        
#         try:
#             # Set maximum performance mode
#             subprocess.run(['nvidia-smi', '--persistence-mode=1'], check=True)
#             status["optimizations"].append({"action": "Enable persistence mode", "status": "success"})
            
#             # Set power limit to maximum
#             subprocess.run(['nvidia-smi', '--power-limit=0'], check=True)
#             status["optimizations"].append({"action": "Optimize power limit", "status": "success"})
            
#             # Set GPU clock to maximum
#             subprocess.run(['nvidia-settings', '-a', '[gpu:0]/GpuPowerMizerMode=1'], check=True)
#             status["optimizations"].append({"action": "Set maximum performance mode", "status": "success"})
            
#             # Enable compute mode
#             subprocess.run(['nvidia-smi', '-c', '3'], check=True)
#             status["optimizations"].append({"action": "Enable compute mode", "status": "success"})
            
#         except Exception as e:
#             status["optimizations"].append({"action": "GPU optimization", "status": "failed", "error": str(e)})
        
#         return status

#     def optimize_amd_gpu(self) -> Dict:
#         status = {"type": "AMD GPU", "optimizations": []}
        
#         try:
#             # Set performance level to high
#             subprocess.run(['rocm-smi', '--setperflevel', 'high'], check=True)
#             status["optimizations"].append({"action": "Set performance level", "status": "success"})
            
#             # Set power limit to maximum
#             subprocess.run(['rocm-smi', '--setpoweroverdrive', '100'], check=True)
#             status["optimizations"].append({"action": "Optimize power limit", "status": "success"})
            
#             # Enable compute mode
#             subprocess.run(['rocm-smi', '--setcomputemode', '1'], check=True)
#             status["optimizations"].append({"action": "Enable compute mode", "status": "success"})
            
#         except Exception as e:
#             status["optimizations"].append({"action": "GPU optimization", "status": "failed", "error": str(e)})
        
#         return status

#     def optimize_intel_gpu(self) -> Dict:
#         status = {"type": "Intel GPU", "optimizations": []}
        
#         try:
#             # Set maximum performance mode
#             if os.path.exists('/sys/class/drm/card0/device/power_dpm_force_performance_level'):
#                 with open('/sys/class/drm/card0/device/power_dpm_force_performance_level', 'w') as f:
#                     f.write('high')
#                 status["optimizations"].append({"action": "Set performance level", "status": "success"})
            
#             # Optimize frequency scaling
#             if os.path.exists('/sys/class/drm/card0/device/power_dpm_state'):
#                 with open('/sys/class/drm/card0/device/power_dpm_state', 'w') as f:
#                     f.write('performance')
#                 status["optimizations"].append({"action": "Optimize frequency scaling", "status": "success"})
                
#         except Exception as e:
#             status["optimizations"].append({"action": "GPU optimization", "status": "failed", "error": str(e)})
        
#         return status

# class SystemOptimizer:
#     def __init__(self):
#         self.console = Console()
#         self.gpu_optimizer = GPUOptimizer()
#         self.optimization_history = []

#     def create_status_table(self, optimization_data: Dict) -> Table:
#         table = Table(title=f"Optimization Results for {optimization_data['type']}")
#         table.add_column("Action", style="cyan")
#         table.add_column("Status", style="green")
#         table.add_column("Details", style="yellow")
        
#         for opt in optimization_data["optimizations"]:
#             status_color = "green" if opt["status"] == "success" else "red"
#             details = opt.get("error", "Completed successfully")
#             table.add_row(
#                 opt["action"],
#                 f"[{status_color}]{opt['status']}[/{status_color}]",
#                 details
#             )
        
#         return table

#     def optimize_gpu(self):
#         try:
#             vendor = self.gpu_optimizer._detect_gpu_vendor()
#             optimization_results = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            
#             if vendor == 'nvidia':
#                 optimization_results.update(self.gpu_optimizer.optimize_nvidia_gpu())
#             elif vendor == 'amd':
#                 optimization_results.update(self.gpu_optimizer.optimize_amd_gpu())
#             elif vendor == 'intel':
#                 optimization_results.update(self.gpu_optimizer.optimize_intel_gpu())
#             else:
#                 optimization_results.update({"type": "Unknown GPU", "optimizations": [
#                     {"action": "GPU detection", "status": "failed", "error": "No supported GPU found"}
#                 ]})
            
#             self.optimization_history.append(optimization_results)
#             self.console.print(Panel.fit(self.create_status_table(optimization_results)))
#             return True
            
#         except Exception as e:
#             self.console.print(f"[red]Error optimizing GPU: {str(e)}[/red]")
#             return False

#     def optimize_cpu(self):
#         try:
#             optimization_results = {
#                 "type": "CPU",
#                 "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "optimizations": []
#             }
            
#             # Set CPU governor to performance
#             if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'):
#                 subprocess.run(['sudo', 'cpupower', 'frequency-set', '-g', 'performance'], check=True)
#                 optimization_results["optimizations"].append({
#                     "action": "Set CPU governor",
#                     "status": "success"
#                 })

#             # Optimize CPU scheduler
#             subprocess.run(['sudo', 'sysctl', '-w', 'kernel.sched_min_granularity_ns=10000000'], check=True)
#             subprocess.run(['sudo', 'sysctl', '-w', 'kernel.sched_wakeup_granularity_ns=15000000'], check=True)
#             optimization_results["optimizations"].append({
#                 "action": "Optimize CPU scheduler",
#                 "status": "success"
#             })

#             # Adjust process priorities
#             high_cpu_processes = []
#             for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
#                 try:
#                     if proc.info['cpu_percent'] > 50:
#                         os.system(f'sudo renice -n -10 -p {proc.info["pid"]}')
#                         high_cpu_processes.append(proc.info["name"])
#                 except:
#                     continue
            
#             optimization_results["optimizations"].append({
#                 "action": "Adjust process priorities",
#                 "status": "success",
#                 "details": f"Optimized {len(high_cpu_processes)} processes"
#             })
            
#             self.optimization_history.append(optimization_results)
#             self.console.print(Panel.fit(self.create_status_table(optimization_results)))
#             return True
            
#         except Exception as e:
#             self.console.print(f"[red]Error optimizing CPU: {str(e)}[/red]")
#             return False

#     def clean_system(self):
#         try:
#             optimization_results = {
#                 "type": "System Cleanup",
#                 "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "optimizations": []
#             }
            
#             # Clear system caches
#             subprocess.run(['sudo', 'sync'], check=True)
#             with open('/proc/sys/vm/drop_caches', 'w') as f:
#                 f.write('3')
#             optimization_results["optimizations"].append({
#                 "action": "Clear system caches",
#                 "status": "success"
#             })
            
#             # Clear swap
#             subprocess.run(['sudo', 'swapoff', '-a'], check=True)
#             subprocess.run(['sudo', 'swapon', '-a'], check=True)
#             optimization_results["optimizations"].append({
#                 "action": "Clear swap",
#                 "status": "success"
#             })
            
#             # Clean package cache
#             subprocess.run(['sudo', 'apt-get', 'clean'], check=True)
#             subprocess.run(['sudo', 'apt-get', 'autoremove', '-y'], check=True)
#             optimization_results["optimizations"].append({
#                 "action": "Clean package cache",
#                 "status": "success"
#             })
            
#             # Optimize memory management
#             subprocess.run(['sudo', 'sysctl', '-w', 'vm.swappiness=10'], check=True)
#             subprocess.run(['sudo', 'sysctl', '-w', 'vm.vfs_cache_pressure=50'], check=True)
#             optimization_results["optimizations"].append({
#                 "action": "Optimize memory management",
#                 "status": "success"
#             })
            
#             self.optimization_history.append(optimization_results)
#             self.console.print(Panel.fit(self.create_status_table(optimization_results)))
#             return True
            
#         except Exception as e:
#             self.console.print(f"[red]Error cleaning system: {str(e)}[/red]")
#             return False

#     def optimize_all(self):
#         """Perform all optimizations and show combined results"""
#         self.console.print("[bold blue]Starting system-wide optimization...[/bold blue]")
        
#         self.optimize_gpu()
#         self.optimize_cpu()
#         self.clean_system()
        
#         # Show summary table
#         summary_table = Table(title="Optimization Summary")
#         summary_table.add_column("Component", style="cyan")
#         summary_table.add_column("Status", style="green")
#         summary_table.add_column("Timestamp", style="yellow")
        
#         for result in self.optimization_history:
#             success_count = len([opt for opt in result["optimizations"] if opt["status"] == "success"])
#             total_count = len(result["optimizations"])
#             status = f"[green]{success_count}/{total_count} optimizations successful[/green]"
            
#             summary_table.add_row(
#                 result["type"],
#                 status,
#                 result["timestamp"]
#             )
        
#         self.console.print(Panel.fit(summary_table))

# if __name__ == "__main__":
#     optimizer = SystemOptimizer()
#     optimizer.optimize_all()