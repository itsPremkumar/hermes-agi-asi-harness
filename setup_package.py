"""
Setup script for HERMES-ASI-MASTER harness.

Installs the harness as a proper Python package that can be imported
from anywhere, including Hermes Agent.
"""

from setuptools import setup, find_packages

setup(
    name="hermes-agi-asi-harness",
    version="11.0.0",
    description="HERMES-ASI-MASTER: Advanced Autonomous Software Engineering & Coding Intelligence",
    author="itsPremkumar",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pyyaml>=6.0",
        "httpx>=0.27.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-asyncio>=0.21"],
    },
    entry_points={
        "console_scripts": [
            "hermes-harness=core.runtime.kernel:main",
        ],
    },
)
