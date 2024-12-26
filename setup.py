# setup.py
from setuptools import setup, find_packages

setup(
    name="guro",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'rich',
        'psutil',
    ],
    entry_points={
        'console_scripts': [
            'guro=guro.cli.main:cli',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Advanced System Optimization Toolkit",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dhanushk-offl/guro",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
)