# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Always use the project's virtual environment. Never install packages globally.

**Setup (first time):**
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# From repo root — creates .venv and installs all dependencies
uv sync --extra dev
```

**Run any script via uv:**
```bash
uv run python src/main.py
uv run pytest
```

**Add a new dependency:**
```bash
uv add <package>          # runtime dependency
uv add --optional dev <package>  # dev-only
```

## Project Purpose

Semi-systematic literature review on the geographic distribution of resilience and risk factors against Global Catastrophic Risks (GCRs). The project queries the OpenAlex academic API, processes results, and generates world map visualizations.

## Commands

**Run the main literature query pipeline** (from repo root):
```bash
uv run python src/main.py
uv run python src/main.py --force-refresh         # Bypass cache and re-fetch from API
uv run python src/main.py --symmetric-difference "Query1" "Query2"  # Compare two query sets
```

**Generate individual visualizations** (run from repo root):
```bash
uv run python src/overview_plots.py    # Stacked maps: ASRS, GCIL, GCBR country groupings
uv run python src/easy_map_plotter.py  # Nuclear alliances map
uv run python src/plot_GHS.py          # Global Health Security Index choropleth
uv run python src/volcano_map.py       # Holocene volcanic eruptions by VEI
```

**Lint:**
```bash
uv run black src/
uv run flake8 src/   # max line length: 100
```

## Architecture

### Data pipeline (`src/main.py`)
Reads query URLs from `config/config.yml`, fetches academic articles from the OpenAlex API (`https://api.openalex.org/works`), caches results locally in `output/`, and exports all results to a RIS file for use in reference managers. It imports `QueryProcessor`, `utils`, and `generate_overview` — these modules are not currently in `src/` and may need to be added.

### Visualization scripts (`src/`)
Each script is standalone and runnable directly. They all use:
- **Winkel Tripel projection** (`+proj=wintri`) for all world maps
- **ALLFED matplotlib style** loaded from GitHub at runtime
- **ALLFED map border** GeoJSON loaded from GitHub at runtime
- Natural Earth 110m country boundaries loaded from naciscdn.org (with fallback to geopandas built-in)

**`easy_map_plotter.py`** — The main reusable map class. `WorldMap` accepts country groups as `{name: (country_list, color, label)}` dicts and matches by country name, ISO A2, or ISO A3 code. Use `WorldMap.plot()` for a single map or `WorldMap.plot_stacked()` for vertically stacked maps.

**`overview_plots.py`** — Uses `WorldMap` to generate the primary output figure: three stacked maps showing which countries have studied resilience for ASRS (abrupt sunlight reduction), GCIL (global catastrophic infrastructure loss), and GCBR (global catastrophic biological risks).

**`plot_GHS.py`** — Choropleth of the 2021 Global Health Security Index. Reads `data/2021-GHS-Index-April-2022.csv` and merges with Natural Earth geometries using a hardcoded country name mapping.

**`volcano_map.py`** — Reads `data/volcano_list.csv` (NOAA NGDC format) and plots Holocene eruptions colored by VEI level. Optionally uses `adjustText` for label placement.

### Data and outputs
- `data/` — Input CSVs (GHS Index, volcano list) and xlsx files
- `output/` — API query cache and RIS export (gitignored)
- `results/figures/` — Generated PNG/SVG map outputs
- `results/Data/` — Intermediate screening and LLM extraction CSVs
- `config/config.yml` — OpenAlex API query URLs and output settings
