import os
import pandas as pd
import yaml

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_file_stats(directory):
    stats = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                df = pd.read_csv(file_path)
                stats[file] = {
                    'total_articles': len(df),
                    'unique_authors': df['authors'].nunique(),
                    'year_range': f"{df['publication_year'].min()}-{df['publication_year'].max()}"
                }
    return stats

def generate_overview(config_path, output_dir):
    config = load_config(config_path)
    stats = get_file_stats(output_dir)
    
    overview = "# GCR Research Overview\n\n"
    overview += "## Query Results\n\n"
    
    for query_set in config['query_sets']:
        query_name = query_set['query_name']
        url = query_set['url']
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
    total_articles = sum(stat['total_articles'] for stat in stats.values())
    overview += f"- Total unique articles across all queries: {total_articles}\n"
    
    with open(os.path.join(output_dir, 'overview.md'), 'w') as f:
        f.write(overview)

if __name__ == "__main__":
    config_path = 'config/config.yml'
    output_dir = 'output'
    generate_overview(config_path, output_dir)