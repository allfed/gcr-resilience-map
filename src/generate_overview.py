"""Module for generating an overview of GCR research based on config and CSV files."""

import os
import pandas as pd
import yaml


def load_config(config_path):
    """Load and return the configuration from the specified YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_file_stats(directory):
    """Calculate statistics for CSV files in the given directory."""
    stats = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)
                    if "authors" in df.columns and "publication_year" in df.columns:
                        stats[file] = {
                            "total_articles": len(df),
                            "unique_authors": df["authors"].nunique(),
                            "year_range": f"{df['publication_year'].min()}-{df['publication_year'].max()}",
                        }
                except (pd.errors.EmptyDataError, KeyError):
                    # Skip files that can't be read or don't have required columns
                    continue
    return stats


def generate_overview(config_path, output_dir):
    """Generate an overview of GCR research based on config and CSV files."""
    config = load_config(config_path)
    stats = get_file_stats(output_dir)
    overview = "# GCR Research Overview\n\n"
    overview += "## Query Results\n\n"
    for query_set in config["query_sets"]:
        query_name = query_set["query_name"]
        url = query_set["url"]
        file_name = f"{query_set['name']}_results.csv"
        overview += f"### {query_name}\n\n"
        overview += f"URL: {url}\n\n"
        if file_name in stats:
            file_stats = stats[file_name]
            overview += f"- Total articles: {file_stats['total_articles']}\n"
            overview += f"- Unique authors: {file_stats['unique_authors']}\n"
            overview += f"- Year range: {file_stats['year_range']}\n"
        else:
            overview += "No data available for this query.\n"
        overview += "\n"
    overview += "## Overall Statistics\n\n"
    total_articles = sum(stat["total_articles"] for stat in stats.values())
    overview += f"- Total unique articles across all queries: {total_articles}\n"
    with open(os.path.join(output_dir, "overview.md"), "w", encoding="utf-8") as f:
        f.write(overview)


if __name__ == "__main__":
    CONFIG_PATH = "config/config.yml"
    OUTPUT_DIR = "output"
    generate_overview(CONFIG_PATH, OUTPUT_DIR)
