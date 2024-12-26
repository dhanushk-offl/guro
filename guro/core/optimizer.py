# guro/core/optimizer.py
import psutil
import os
import subprocess
from rich.console import Console

class SystemOptimizer:
    def __init__(self):
        self.console = Console()

    def optimize_cpu(self):
        try:
            # Set CPU governor to performance
            if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'):
                subprocess.run(['sudo', 'cpupower', 'frequency-set', '-g', 'performance'])
                self.console.print("[green]CPU governor set to performance mode[/green]")

            # Adjust process nice values for better performance
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > 50:
                        os.system(f'sudo renice -n -10 -p {proc.info["pid"]}')
                except:
                    continue
            
            self.console.print("[green]Process priorities optimized[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Error optimizing CPU: {str(e)}[/red]")
            return False

    def clean_system(self):
        try:
            # Clear system caches
            subprocess.run(['sudo', 'sync'])
            with open('/proc/sys/vm/drop_caches', 'w') as f:
                f.write('3')
            
            # Clear swap
            subprocess.run(['sudo', 'swapoff', '-a'])
            subprocess.run(['sudo', 'swapon', '-a'])
            
            # Clean package cache
            subprocess.run(['sudo', 'apt-get', 'clean'])
            subprocess.run(['sudo', 'apt-get', 'autoremove', '-y'])
            
            self.console.print("[green]System cleaned successfully[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Error cleaning system: {str(e)}[/red]")
            return False