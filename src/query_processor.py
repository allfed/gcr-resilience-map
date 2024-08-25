"""Module for processing OpenAlex queries."""

import os
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
import pandas as pd

class QueryProcessor:
    """Processes API queries, fetches results, and manages caching."""

    def __init__(self, api_config: Dict[str, Any], logger, output_dir: str):
        self.per_page = api_config['per_page']
        self.logger = logger
        self.output_dir = output_dir

    def get_page(self, url: str) -> tuple[List[Dict[str, Any]], int, str]:
        """Fetch a single page of results from the API."""
        response = requests.get(url, timeout=30)  # Add a 30-second timeout
        response.raise_for_status()
        data = response.json()
        total_results = data['meta']['count']
        results = data.get('results', [])
        next_cursor = data['meta'].get('next_cursor')
        return results, total_results, next_cursor

    def process_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relevant information from API results."""
        processed = []
        for result in results:
            authors = [author['author']['display_name'] for author in result.get('authorships', [])]
            processed.append({
                'id': result['id'],
                'title': result['title'],
                'authors': ', '.join(authors),
                'publication_year': result['publication_year'],
                'journal': result.get('host_venue', {}).get('display_name', ''),
                'doi': result.get('doi', ''),
                'relevance_score': result.get('relevance_score', 0),  # Add relevance score
            })
        return processed

    def update_url_with_cursor(self, url: str, cursor: str) -> str:
        """Update the URL with a new cursor value and sorting parameter."""
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params['cursor'] = [cursor]
        query_params['per-page'] = [str(self.per_page)]
        query_params['sort'] = ['relevance_score:desc']  # Add sorting by relevance score
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed_url._replace(query=new_query))

    def get_cache_filename(self, query_name: str) -> str:
        """Generate a filename for caching based on the query name."""
        return os.path.join(self.output_dir, f"{query_name}_results.csv")

    def load_from_cache(self, query_name: str) -> pd.DataFrame:
        """Load results from a cached CSV file."""
        cache_file = self.get_cache_filename(query_name)
        if os.path.exists(cache_file):
            self.logger.info(f"Loading cached results for {query_name}")
            return pd.read_csv(cache_file)
        return None

    def save_to_cache(self, df: pd.DataFrame, query_name: str):
        """Save results to a CSV file for caching."""
        cache_file = self.get_cache_filename(query_name)
        df.to_csv(cache_file, index=False)
        self.logger.info(f"Cached results saved for {query_name}")

    def fetch_all_data(self, url: str, query_name: str) -> pd.DataFrame:
        """Fetch all pages of results for given URL, using cache if available."""
        cached_results = self.load_from_cache(query_name)
        if cached_results is not None:
            return cached_results

        all_results = []
        cursor = '*'
        while cursor:
            current_url = self.update_url_with_cursor(url, cursor)
            self.logger.info(f"Fetching URL: {current_url}")
            results, total_count, next_cursor = self.get_page(current_url)
            if not results:
                break
            processed_results = self.process_results(results)
            all_results.extend(processed_results)
            self.logger.info(f"Fetched {len(all_results)} out of {total_count} results")
            cursor = next_cursor
            if not cursor:
                break
        df = pd.DataFrame(all_results)
        # Check if 'relevance_score' column exists
        if 'relevance_score' in df.columns:
            df = df.sort_values(by='relevance_score', ascending=False)
        else:
            print(f"Warning: 'relevance_score' column not found in results for "
                  f"query '{query_name}'. Skipping sorting.")
        self.save_to_cache(df, query_name)
        return df
    