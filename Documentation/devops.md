# Installation and packaging

## Requirements

Runtime:

- Python 3.9 or newer
- SymPy 1.13 or newer and below version 2

Build:

- pip with PEP 517 support
- Setuptools 61 or newer
- wheel

Testing uses Python's built-in `unittest`; there are no additional test-only
dependencies.

## Install

From the repository root:

```bash
python3 -m pip install .
```

Pip reads `pyproject.toml`, creates an isolated build environment, installs the
build requirements, evaluates `setup.py`, and installs SymPy automatically.

For editable development:

```bash
python3 -m pip install -e .
python3 -m unittest -v
```

## Installed interfaces

Python:

```python
from crntanalysis import ReactionFileParser, calculate_deficiency
```

Console:

```bash
crntanalysis model.react
```

## Build distributions

With the standard `build` frontend installed:

```bash
python3 -m pip install build
python3 -m build
```

This creates source and wheel distributions in `dist/`.
