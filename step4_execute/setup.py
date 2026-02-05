"""
Setup script for Step 4: Test Execution

Installs the tbeval-run command.

Author: TB Eval Team
Version: 0.1.0
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    long_description = readme_file.read_text()
else:
    long_description = "TB Eval Framework - Test Execution (Step 4)"

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
else:
    requirements = [
        "pyyaml>=6.0",
        "psutil>=5.9.0",
    ]

setup(
    name="tbeval-step4-execute",
    version="0.1.0",
    description="TB Eval Framework - Test Execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TB Eval Team",
    author_email="team@tbeval.org",
    url="https://github.com/tbeval/framework",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "tbeval-run=step4_execute.cli.main:sync_main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="verification testing hdl verilog vhdl cocotb vunit",
    project_urls={
        "Documentation": "https://tbeval.readthedocs.io/",
        "Source": "https://github.com/tbeval/framework",
        "Bug Reports": "https://github.com/tbeval/framework/issues",
    },
)
