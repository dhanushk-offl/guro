from setuptools import setup, find_packages
import sys

common_packages = [
    'click>=8.0.0',
    'rich>=10.0.0',
    'psutil>=5.8.0',
    'gputil>=1.4.0',
    'matplotlib>=3.5.0',
    'nvidia-ml-py>=11.515.0',
    'pandas>=1.3.0',
    'plotly>=5.5.0',
    'termcolor>=2.0.0',
    'tabulate>=0.8.9',
    'py-cpuinfo>=8.0.0',
    'setproctitle>=1.2.2',
    'keyboard>=0.13.5',
    'pytest>=7.0.0',
    'pytest-mock>=3.10.0',
    'pytest-cov>=4.0.0',
    'pytest-timeout>=2.1.0',
]

if sys.platform.startswith('linux'):
    common_packages.append('pyamdgpuinfo>=2.1.6')
    common_packages.append('distro>=1.7.0')

# Test requirements
test_requires = [
    'pytest>=7.0.0',
    'pytest-mock>=3.10.0',
    'pytest-cov>=4.0.0',
    'pytest-timeout>=2.1.0',
]

setup(
    name="guro",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=common_packages,
    entry_points={
        'console_scripts': [
            'guro=guro.cli.main:cli',
        ],
    },
    author="Dhanush Kandhan",
    author_email="dhanushkandhan75@gmail.com",
    description="A Simple System Monitoring & Benchmarking Toolkit",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dhanushk-offl/guro",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: System :: Hardware",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Operating System",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Natural Language :: English"
    ],
    python_requires=">=3.7",
    keywords=[
        "system-monitoring",
        "gpu-optimization",
        "performance-tuning",
        "hardware-monitoring",
        "system-administration",
        "nvidia-gpu",
        "amd-gpu",
        "intel-gpu",
        "resource-monitoring",
        "system-optimization"
    ],
    project_urls={
        "Bug Reports": "https://github.com/dhanushk-offl/guro/issues",
        "Source": "https://github.com/dhanushk-offl/guro",
        "Documentation": "https://github.com/dhanushk-offl/guro/wiki"
    },
    extras_require={
        'nvidia': ['py3nvml>=0.2.7', 'nvidia-ml-py>=11.515.0'],
        'amd': ['pyamdgpuinfo>=2.1.0'],
        'all': [
            'py3nvml>=0.2.7',
            'nvidia-ml-py>=11.515.0',
            'pyamdgpuinfo>=2.1.0',
            'matplotlib>=3.5.0',
            'plotly>=5.5.0'
        ],
        'test': test_requires
    }
)
