# GCR Resilience Map

This repository collects code and bibliographic data needed for a semi-systematic literature review of the literature on (the geographic distribution of) resilience and risk factors against Global Catastrophic Risk (GCR).

## Overview

The project consists of three main components:

1. **OpenAlex Query Processing**: Fetches academic papers from the OpenAlex API based on configurable search queries
2. **LLM Paper Processing**: Extracts structured information from PDF papers using Claude API
3. **Visualization**: Creates maps and visualizations of resilience factors and risk distributions

## Installation

### Option 1: Using Conda (Recommended)

```bash
conda env create -f environment.yml
conda activate resilience_map
```

### Option 2: Using pip

```bash
pip install -r requirements.txt
```

### Additional Dependencies

The project also requires:
- `PyYAML` (for YAML config parsing)
- `requests` (for API calls)
- `geopandas` (for map visualizations)
- `anthropic` (for LLM processing)
- `PyPDF2` (for PDF text extraction)
- `tqdm` (for progress bars)
- `tiktoken` (for token counting)

Install with:
```bash
pip install PyYAML requests geopandas anthropic PyPDF2 tqdm tiktoken
```

## Project Structure

```
gcr-resilience/
├── config/
│   ├── config.yml          # OpenAlex query configuration
│   └── api_key.txt         # Claude API key (create this file)
├── data/                   # Input data files
│   ├── 2021-GHS-Index-April-2022.csv
│   └── volcano_list.csv
├── src/
│   ├── main.py             # Main OpenAlex query processor
│   ├── utils.py            # Utility functions
│   ├── generate_overview.py # Overview report generator
│   ├── OpenAlex/
│   │   └── query_processor.py
│   ├── LLMParsing/
│   │   └── paper_processor.py
│   ├── plot_GHS.py         # Global Health Security Index map
│   ├── volcano_map.py      # Volcanic eruptions map
│   ├── easy_map_plotter.py # General purpose map plotting
│   └── overview_plots.py   # Stacked resilience maps
├── output/                 # Generated output files
│   ├── *.csv               # Query results
│   ├── *.ris               # RIS format bibliographic data
│   └── overview.md         # Overview report
└── results/
    ├── Data/               # Processed data
    └── figures/            # Generated visualizations
```

## Usage

### 1. OpenAlex Query Processing

Fetch academic papers from OpenAlex based on queries defined in `config/config.yml`:

```bash
# From project root
python -m src.main --config config/config.yml

# Or with absolute path
python src/main.py --config config/config.yml
```

**Options:**
- `--config PATH`: Path to config file (default: `config/config.yml`)
- `--force-refresh`: Force refresh all queries, ignoring cache
- `--symmetric-difference QUERY1 QUERY2`: Compare two queries and find unique articles

**Example:**
```bash
python -m src.main --config config/config.yml --force-refresh
```

**Output:**
- CSV files with query results in `output/` directory
- RIS file with all articles in `output/all_results.ris`
- Overview markdown report in `output/overview.md`
- Log file in `output/gcr_research.log`

### 2. LLM Paper Processing

Extract structured information from PDF papers using Claude:

```bash
cd src/LLMParsing
python paper_processor.py
```

**Requirements:**
- API key file at `../config/api_key.txt` (relative to script location)
- PDF files in a `pdf/` directory (relative to where script runs)

**Output:**
- `gcr_resilience_extraction_results.csv` with extracted metadata
- `prompt_cache/extraction_prompt_cache.json` for caching API responses

### 3. Visualization Scripts

Generate maps and visualizations:

```bash
# Global Health Security Index map
python src/plot_GHS.py

# Holocene volcanic eruptions map
python src/volcano_map.py

# General resilience maps
python src/easy_map_plotter.py
python src/overview_plots.py
```

**Output:**
- Maps saved to `results/figures/` directory

## Configuration

### OpenAlex Configuration (`config/config.yml`)

```yaml
api:
  base_url: "https://api.openalex.org/works?"
  per_page: 200

logging:
  level: INFO
  format: '%(asctime)s - %(levelname)s - %(message)s'
  file: 'output/gcr_research.log'

query_sets:
  - name: combined_gcr_query
    query_name: "Combined GCR and Resilience Query"
    url: "https://api.openalex.org/works?..."
    
output:
  directory: 'output'
  ris_file: 'all_results.ris'
```

### API Key Setup

For LLM processing, create `config/api_key.txt` with your Claude API key:
```bash
echo "your-api-key-here" > config/api_key.txt
```

## Features

- **Caching**: Query results are cached to avoid redundant API calls
- **RIS Export**: Bibliographic data exported in RIS format for reference managers
- **Symmetric Difference Analysis**: Compare query results to find unique articles
- **Rate Limiting**: LLM processor includes rate limiting and token management
- **Error Handling**: Robust error handling for API failures and data processing

## Dependencies

See `requirements.txt` and `environment.yml` for full dependency lists.

Key dependencies:
- Python 3.9+
- pandas
- numpy
- matplotlib
- geopandas
- anthropic (Claude API)
- PyPDF2
- requests
- PyYAML

## License

See LICENSE file for details.

## Contributing

This is a research project for collecting and analyzing GCR resilience literature. For questions or contributions, please open an issue or contact the maintainers.
