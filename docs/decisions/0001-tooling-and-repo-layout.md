# 0001: Tooling and repository layout

Date: 2026-11-07. Status: accepted (Phase 0).

## Context
The brief asks for pinned dependencies, script-based parametric CAD, and
tested physics code. The machine has Python 3.12.3 but no `python3-venv`
(installing it needs sudo), and Ubuntu blocks user-level pip installs (PEP 668).

## Options
1. Ask the user to `sudo apt install python3.12-venv`, then use venv + pip-tools.
2. Install `uv` (a single self-contained binary) into `~/.local`, and let uv
   manage `.venv/` and `uv.lock`.
3. Conda/mamba for CadQuery. Heavier, and a second package manager.

## Decision
Option 2. `uv` was installed with `pip3 install --user --break-system-packages uv`.
That only writes to `~/.local`, and uv has no Python dependencies. Direct
dependencies are pinned with `==` in `pyproject.toml`; `uv.lock` pins every
transitive dependency.

Pinned versions: cadquery 2.8.0, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2,
pyyaml 6.0.3, ezdxf 1.4.5, pint 0.26.2, pytest 9.2.0 (dev).
A CadQuery smoke test (box volume) passed on this machine.

Layout: top-level packages `materials/`, `geometry/`, `simulation/`,
`validation/`, importable from the repo root (pytest `pythonpath = ["."]`).
Data and outputs live next to the code that owns them.

## Consequences
- Run everything as `~/.local/bin/uv run ...`.
- `pint` is used to convert units at the materials-database boundary only.
  Solver internals use plain floats/arrays with unit-suffixed names, for speed.
