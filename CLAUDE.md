# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WaterTAP is a Python library for modeling and optimizing water treatment systems, built on IDAES-PSE and Pyomo. Developed as part of the National Alliance for Water Innovation (NAWI). Supports Python 3.10-3.13 on Linux, Windows, and macOS (ARM).

- **Docs**: https://watertap.readthedocs.io
- **Framework stack**: Pyomo (optimization) → IDAES-PSE (process modeling) → WaterTAP (water treatment)

## Common Commands

### Installation (development)
```bash
conda create --name watertap-dev --yes python=3.11
conda activate watertap-dev
pip install -r requirements-dev.txt
idaes get-extensions --extra petsc    # required solvers
pre-commit install
```

### Testing
```bash
pytest                                          # all tests
pytest watertap/unit_models/tests/test_cstr.py  # single file
pytest -m unit                                  # only unit tests (fast, no solver)
pytest -m component                             # tests that may need a solver
pytest -m integration                           # long-running tests
pytest -m "not requires_idaes_solver"           # skip tests needing IDAES solvers
pytest --cov=watertap --cov-report=html         # with coverage
```

Test markers are defined in `watertap/conftest.py` as `MarkerSpec`:
- `unit` — no solver, < 2s
- `component` — may require solver
- `integration` — long duration
- `requires_idaes_solver` — xfails if IDAES solver not installed

### Formatting and Linting
```bash
black .                    # format all files (enforced in CI)
black --check .            # check formatting without modifying
pylint watertap            # lint (many warnings disabled for Pyomo/IDAES compatibility)
pre-commit run --all-files # run pre-commit hooks
```

### Documentation
```bash
make -C docs html          # build docs
make -C docs doctest       # test code examples in docs
```

## Architecture

### Key Directories
- `watertap/core/` — Base classes, solvers, database, scaling/initialization utilities
- `watertap/unit_models/` — 40+ Pyomo-based unit operation models (RO, electrodialysis, GAC, etc.)
- `watertap/unit_models/zero_order/` — Simplified equation-free models using YAML parameter databases
- `watertap/flowsheets/` — Complete process flowsheets connecting unit models
- `watertap/property_models/` — Thermodynamic property packages
- `watertap/costing/` — Techno-economic costing framework (capital, operating costs, LCOW)
- `watertap/data/techno_economic/` — YAML parameter databases for zero-order models
- `watertap/tools/` — Utilities including OLI API integration

### Unit Model Pattern
Models inherit from `idaes.core.UnitModelBlockData`, use `@declare_process_block_class` decorator, declare configuration via `ConfigBlock`, and implement `build()` to define variables and constraints. Many have custom scalers (e.g., `CSTRScaler`) inheriting from `CustomScalerBase`.

### Flowsheet Pattern
Flowsheets follow: `build()` → `initialize()` → `optimize()`. They create a `ConcreteModel` with a `FlowsheetBlock`, instantiate unit models with property packages, connect them via `Arc`, then expand arcs with `TransformationFactory("network.expand_arcs")`. Flowsheets with `*_ui.py` files integrate with the Flowsheet Processor GUI via `export_to_ui()`.

### Zero-Order Models
Simplified models that load parameters from YAML databases via `watertap.core.wt_database.Database`. Configured with `process_subtype` to select parameter sets. Costed via `ZeroOrderCosting`.

### Testing Pattern
Unit model tests use `UnitTestHarness` base class from `watertap/unit_models/tests/unit_test_harness.py`. Subclasses implement `configure()` to set up the model and expected solutions. The harness provides standard tests: `test_units_consistent`, `test_dof`, `test_initialization`, `test_conservation`.

## CI Pipeline

Defined in `.github/workflows/checks.yml`, triggered on push to `main` and PRs:
1. `code-formatting` — `black --check .`
2. `pylint` — runs after formatting passes
3. `tests` — matrix of Python 3.10-3.13 × Linux/Windows, with coverage upload
4. `user-mode-pytest` — tests non-editable pip install
5. `notebooks` — runs Jupyter notebooks via nbmake

## pylint Configuration

Many pylint categories are disabled in `pyproject.toml` due to Pyomo/IDAES metaprogramming (e.g., `no-member`, `undefined-variable`, `invalid-unary-operand-type`). Only `unnecessary-pass` and `unused-import` are explicitly enabled.

## Flowsheet Entry Points

Flowsheets are registered as `watertap.flowsheets` entry points in `pyproject.toml` for discovery by the Flowsheet Processor GUI.
