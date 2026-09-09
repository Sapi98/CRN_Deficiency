"""Setuptools configuration for installing crntanalysis."""

from pathlib import Path

from setuptools import find_packages, setup


PROJECT_ROOT = Path(__file__).parent


setup(
    name="crntanalysis",
    version="0.1.0",
    description="Parse chemical reaction networks and calculate CRNT deficiency",
    long_description=(PROJECT_ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["crntanalysis", "crntanalysis.*"]),
    python_requires=">=3.9",
    install_requires=["sympy>=1.13,<2"],
    extras_require={"visualization": ["networkx>=3.2,<4", "matplotlib>=3.8,<4"]},
    entry_points={
        "console_scripts": [
            "crntanalysis=crntanalysis.orchestrator:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
)
