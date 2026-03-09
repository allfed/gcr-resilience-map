# GCR Resilience Map

A semi-systematic literature review of the geographic distribution of resilience and risk factors against Global Catastrophic Risk (GCR). The project queries the OpenAlex academic API for relevant literature and generates world map visualizations of GCR-relevant country-level data.

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

Install uv if you don't have it yet:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

From the root of the repository, create a virtual environment and install all dependencies:
```bash
uv sync --extra dev
```

## Usage

**Run the literature query pipeline** (fetches from OpenAlex API, caches results, exports RIS):
```bash
uv run python src/main.py
uv run python src/main.py --force-refresh  # bypass cache
```

**Generate visualizations:**
```bash
uv run python src/overview_plots.py    # GCR resilience maps (ASRS, GCIL, GCBR)
uv run python src/plot_GHS.py          # Global Health Security Index choropleth
uv run python src/volcano_map.py       # Holocene + VEI 8 volcanic eruptions map
uv run python src/easy_map_plotter.py  # Nuclear alliances map
```

## Data Sources

- **OpenAlex** — academic literature on GCR resilience, queried via the [OpenAlex API](https://openalex.org/)
- **Global Health Security Index 2021** — NTI/Johns Hopkins Center for Health Security
- **Holocene volcanic eruptions** — NOAA NGDC Significant Volcanic Eruptions Database
- **VEI 7–8 eruptions (~2.5 Ma)** — LaMEVE database (VOGRIPA): Crosweller et al. (2012), *Journal of Applied Volcanology*, 1, 4. https://doi.org/10.1186/2191-5040-1-4

## Structure

```
config/          # OpenAlex query configuration
data/            # Input data files
results/
  figures/       # Generated map outputs
  Data/          # Intermediate screening and LLM extraction results
src/             # Python scripts
```
