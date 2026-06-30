# GCR Resilience Map

A semi-systematic literature review of the geographic distribution of resilience and risk factors against Global Catastrophic Risk (GCR). The project queries the OpenAlex academic API for relevant literature, extracts country-level resilience/vulnerability factors, and generates world-map and chart visualizations.

Three catastrophe families are covered: **ASRS** (Abrupt Sunlight Reduction Scenarios), **GCIL** (Global Catastrophic Infrastructure Loss), and **GCBR** (Global Catastrophic Biological Risks).

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # install uv if needed
uv sync --extra dev                               # create venv and install deps
```

## Usage

**Run the literature query pipeline** (fetches from OpenAlex API, caches results, exports RIS):
```bash
uv run python src/main.py
uv run python src/main.py --force-refresh  # bypass cache
```

**Generate visualizations:**
```bash
uv run python src/overview_plots.py            # Stacked ASRS/GCIL/GCBR maps (top-5 countries each)
uv run python src/factor_count_comparison.py   # Factor-count bar charts per scope
uv run python src/plot_GHS.py                  # Global Health Security Index choropleth
uv run python src/volcano_map.py               # Holocene volcanic eruptions map (by VEI)
uv run python src/easy_map_plotter.py          # Nuclear weapon states and alliances map
uv run python src/visual_abstract.py           # Graphical abstract (Venn diagram)
```

The `overview_plots.py` maps and `factor_count_comparison.py` charts are both driven by the evidence ledger and highlight the same top-5 countries per scope.

## Data Sources

- **OpenAlex** — academic literature on GCR resilience, queried via the [OpenAlex API](https://openalex.org/) (query in `config/config.yml`).
- **Anthropic Claude** — extracts structured resilience/vulnerability factors from screened papers (`src/LLMParsing/paper_processor.py`).
- **GCR resilience evidence ledger** (`results/Data/gcr_resilience_evidence_ledger.xlsx`) — curated synthesis of the extraction (country, GCR category, factor, direction, provenance, source); drives the country maps and factor-count charts.
- **Global Health Security Index 2021** — NTI / Johns Hopkins Center for Health Security.
- **Volcanic eruptions** — Smithsonian Global Volcanism Program (GVP) *Volcanoes of the World v5.2.8*, Holocene-filtered, supplemented for VEI 7+ by the LaMEVE database (VOGRIPA): Crosweller et al. (2012), *Journal of Applied Volcanology*, 1, 4. https://doi.org/10.1186/2191-5040-1-4
- **Nuclear weapon states and alliances** — compiled from public sources in `src/easy_map_plotter.py`.
- **Natural Earth** boundaries and **ALLFED** map style/border — fetched at runtime for the maps.

## Structure

```
config/          # OpenAlex query configuration
data/            # External datasets (GHS Index, GVP, LaMEVE)
results/
  figures/       # Generated maps and charts
  Data/          # Raw OpenAlex export, screening results, LLM extraction, evidence ledger
src/             # Pipeline (main.py, OpenAlex/, LLMParsing/) and plotting scripts
```
