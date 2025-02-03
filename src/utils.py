"""Utility functions for data processing and file operations."""

import logging
from typing import Dict, Any, List, Tuple
import pandas as pd


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """Set up logging based on configuration."""
    logging.basicConfig(
        level=config['level'],
        format=config['format'],
        filename=config['file']
    )
    return logging.getLogger(__name__)


def save_results(df: pd.DataFrame, filename: str):
    """Save results to a CSV file."""
    df.to_csv(filename, index=False)
    print(f"Results saved to {filename}")


def save_to_ris(articles: List[Dict[str, Any]], filename: str):
    """Save all articles to a single RIS file."""
    with open(filename, 'w', encoding='utf-8') as f:
        for article in articles:
            f.write("TY  - JOUR\n")
            f.write(f"TI  - {article['title']}\n")
            # Handle 'authors' field
            authors = article.get('authors', '')
            if isinstance(authors, str):
                for author in authors.split(', '):
                    f.write(f"AU  - {author}\n")
            elif isinstance(authors, list):
                for author in authors:
                    f.write(f"AU  - {author}\n")
            f.write(f"PY  - {article['publication_year']}\n")
            f.write(f"JO  - {article['journal']}\n")
            f.write(f"DO  - {article['doi']}\n")
            f.write(f"UR  - https://doi.org/{article['doi']}\n")
            f.write(f"ID  - {article['id']}\n")
            f.write("ER  - \n\n")
    print(f"All results saved to RIS file: {filename}")


def compute_symmetric_difference(
        df1: pd.DataFrame, df2: pd.DataFrame
                                 ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute the symmetric difference between two DataFrames."""
    df1_only = df1[~df1['id'].isin(df2['id'])]
    df2_only = df2[~df2['id'].isin(df1['id'])]
    return df1_only, df2_only


def analyze_symmetric_difference(
    df1: pd.DataFrame, df2: pd.DataFrame, name1: str, name2: str, output_dir: str
) -> Tuple[str, pd.DataFrame, pd.DataFrame]:
    """Analyze and return a string report of the symmetric difference between two DataFrames."""
    df1_only, df2_only = compute_symmetric_difference(df1, df2)
    report = f"Symmetric Difference Analysis between {name1} and {name2}:\n"
    report += f"Total articles in {name1}: {len(df1)}\n"
    report += f"Total articles in {name2}: {len(df2)}\n"
    report += f"Articles unique to {name1}: {len(df1_only)}\n"
    report += f"Articles unique to {name2}: {len(df2_only)}\n"
    report += f"Articles in common: {len(df1) - len(df1_only)}\n"
    # Save the symmetric differences
    save_results(df1_only, f"{output_dir}/symmetric_difference_{name1}_only.csv")
    save_results(df2_only, f"{output_dir}/symmetric_difference_{name2}_only.csv")
    return report, df1_only, df2_only
