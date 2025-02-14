"""Main script for processing OpenAlex queries for GCR research."""

import os
import argparse
from collections import defaultdict
import yaml
from query_processor import QueryProcessor
from utils import setup_logging, save_to_ris, analyze_symmetric_difference
from generate_overview import generate_overview


def analyze_results(all_results):
    """
    Analyze query results to count article occurrences across different searches.

    Args:
        all_results (dict): Dictionary of DataFrames containing query results.

    Returns:
        tuple: Total unique articles, articles in multiple searches, articles in single search.
    """
    article_occurrences = defaultdict(list)
    for query_name, df in all_results.items():
        for _, row in df.iterrows():
            article_occurrences[row["id"]].append(query_name)
    multiple_searches = [
        id for id, queries in article_occurrences.items() if len(queries) > 1
    ]
    single_search = [
        id for id, queries in article_occurrences.items() if len(queries) == 1
    ]
    return len(article_occurrences), len(multiple_searches), len(single_search)


def main():
    """Process OpenAlex queries for GCR research based on configuration."""
    parser = argparse.ArgumentParser(
        description="Process OpenAlex queries for GCR research."
    )
    parser.add_argument(
        "--config", default="config/config.yml", help="Path to config file"
    )
    parser.add_argument(
        "--symmetric-difference",
        nargs=2,
        metavar=("QUERY1", "QUERY2"),
        help="Compute symmetric difference between two queries",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh all queries, ignoring cache",
    )
    args = parser.parse_args()

    # Print current working directory
    print(f"Current working directory: {os.getcwd()}")

    # Print full path of the config file
    config_path = os.path.abspath(args.config)
    print(f"Attempting to open config file: {config_path}")

    # Check if the file exists
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger = setup_logging(config["logging"])

    output_dir = config["output"]["directory"]
    os.makedirs(output_dir, exist_ok=True)

    processor = QueryProcessor(config["api"], logger, output_dir)

    all_results = {}
    all_articles = []

    for query_set in config["query_sets"]:
        logger.info("Processing query: %s", query_set["query_name"])
        if args.force_refresh:
            results = processor.fetch_all_data(query_set["url"], query_set["name"])
        else:
            results = processor.load_from_cache(query_set["name"])
            if results is None:
                results = processor.fetch_all_data(query_set["url"], query_set["name"])
        all_results[query_set["query_name"]] = results
        all_articles.extend(results.to_dict("records"))
        logger.info(
            "Number of articles for %s: %d", query_set["query_name"], len(results)
        )

    total_articles, multiple_searches, single_search = analyze_results(all_results)

    logger.info("Total unique articles: %d", total_articles)
    logger.info("Articles appearing in multiple searches: %d", multiple_searches)
    logger.info("Articles appearing in only one search: %d", single_search)

    save_to_ris(all_articles, os.path.join(output_dir, config["output"]["ris_file"]))
    logger.info("All results saved to RIS file: %s", config["output"]["ris_file"])

    if args.symmetric_difference:
        query1, query2 = args.symmetric_difference
        if query1 in all_results and query2 in all_results:
            report, df1_only, df2_only = analyze_symmetric_difference(
                all_results[query1], all_results[query2], query1, query2, output_dir
            )
            logger.info("\nSymmetric Difference Analysis:\n%s", report)
            # Output overview for symmetric difference
            logger.info("\nOverview of articles unique to each query:")
            logger.info("Articles unique to %s:", query1)
            for _, row in df1_only.iterrows():
                logger.info("Title: %s", row["title"])
                logger.info("Authors: %s", row["authors"])
                logger.info("Year: %d", row["publication_year"])
                logger.info("DOI: %s", row["doi"])
                logger.info("---")
            logger.info("Articles unique to %s:", query2)
            for _, row in df2_only.iterrows():
                logger.info("Title: %s", row["title"])
                logger.info("Authors: %s", row["authors"])
                logger.info("Year: %d", row["publication_year"])
                logger.info("DOI: %s", row["doi"])
                logger.info("---")
            report_file = os.path.join(
                output_dir, f"symmetric_difference_{query1}_{query2}_report.txt"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
                f.write("\n\nOverview of articles unique to each query:\n")
                f.write(f"\nArticles unique to {query1}:\n")
                for _, row in df1_only.iterrows():
                    f.write(f"Title: {row['title']}\n")
                    f.write(f"Authors: {row['authors']}\n")
                    f.write(f"Year: {row['publication_year']}\n")
                    f.write(f"DOI: {row['doi']}\n")
                    f.write("---\n")
                f.write(f"\nArticles unique to {query2}:\n")
                for _, row in df2_only.iterrows():
                    f.write(f"Title: {row['title']}\n")
                    f.write(f"Authors: {row['authors']}\n")
                    f.write(f"Year: {row['publication_year']}\n")
                    f.write(f"DOI: {row['doi']}\n")
                    f.write("---\n")
        else:
            logger.error(
                "One or both of the specified queries for symmetric "
                "difference are not found."
            )

    logger.info("All queries processed.")
    generate_overview("config/config.yml", output_dir)


if __name__ == "__main__":
    main()
