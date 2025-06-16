# PDF Information Extractor 
import os
from pathlib import Path
import PyPDF2
import anthropic
import pandas as pd
from tqdm import tqdm
import tiktoken
import csv
import json
from io import StringIO
import hashlib
import datetime
import time as sleep_time

# Setup Anthropic Client
# read the API key from the file    
with open("../config/api_key.txt", 'r') as f:
    api_key = f.read().strip()

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=api_key)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def process_with_claude(text: str, query: str, temperature: float = 0, max_tokens: int = 1000) -> str:
    """Process text with Claude model using prefix caching"""
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(text))
    token_count = int(token_count * 1.1)
    print(f"Token count is approximately {token_count}")

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=max_tokens,
        temperature=temperature,
        system=[
            {
                "type": "text",
                "text": "You are an AI assistant tasked with analyzing documents.",
            },
            {
                "type": "text",
                "text": f"Document content:\n{text}",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[
            {
                "role": "user",
                "content": query
            }
        ]
    )

    # Log cache information if available
    if hasattr(response, 'usage'):
        print(f"API Response Token Usage:")
        print(f"  - Total input tokens: {response.usage.input_tokens}")
        print(f"  - Cache creation tokens: {getattr(response.usage, 'cache_creation_input_tokens', 0)}")
        print(f"  - Cache read tokens: {getattr(response.usage, 'cache_read_input_tokens', 0)}")

        # Calculate percentage saved if using cache
        cache_read = getattr(response.usage, 'cache_read_input_tokens', 0)
        if cache_read > 0:
            total_possible = response.usage.input_tokens + cache_read
            percentage_saved = (cache_read / total_possible) * 100
            print(f"  - Approximate cache savings: {percentage_saved:.1f}% of input tokens")

    return response.content[0].text

def parse_csv_response(response_text, columns):
    """Parse the CSV response from Claude and return a dictionary with column names as keys"""
    # Clean the response text
    clean_text = response_text.strip()

    # If there are multiple lines, take only the CSV line
    if "\n" in clean_text:
        # Find the line that has the most commas (likely the CSV data)
        lines = clean_text.split('\n')
        clean_text = max(lines, key=lambda x: x.count(','))

    # Parse CSV using the csv module which handles quoted fields properly
    reader = csv.reader(StringIO(clean_text))
    try:
        row = next(reader)
        # Map values to column names
        result = {col: val for col, val in zip(columns, row)}
        return result
    except StopIteration:
        # If parsing fails, return the original text
        return {"error": "Failed to parse CSV response", "original_text": clean_text}

# Extraction prompt
extraction_query = """I need you to analyze the provided research paper and extract specific information about regional resilience to catastrophic risks. Our research question is: "What specific geographical, institutional, and infrastructural factors have been empirically or theoretically identified as enhancing regional resilience to nuclear winter, large magnitude volcanic eruptions, extreme pandemics, and infrastructure collapse catastrophes, and how do these resilience factors vary across catastrophe types?"

After analyzing the paper thoroughly, provide your output in a single row CSV format with the following structure:

1. paper_citation: Full citation (author, year, title)
2. publication_type: [Journal article/Preprint/Report/Book chapter]
3. gcr_types: Types of catastrophic risks addressed [Nuclear/Volcanic/Asteroid/Infrastructure/Pandemic/Climate/Multiple]
4. geographic_focus: [Global/Regional/National/Local/Islands - specify]
5. geographic_factors: List key geographic factors (location, climate, resources, etc.)
6. institutional_factors: List key institutional factors (governance, policies, social systems, etc.)
7. infrastructural_factors: List key infrastructure factors (energy, food, communications, etc.)
8. other_resilience_factors: Any resilience factors not fitting above categories
9. study_approach: [Model/Empirical/Review/Case study/Theoretical]
10. resilience_phase: [Preparedness/Robustness/Recovery/Adaptation]
11. main_resilience_factors: Brief summary of main resilience-enhancing factors
12. resilience_tradeoffs: [Yes/No] with description of any identified trade-offs
13. vulnerable_resilient_regions: List of particularly vulnerable or resilient regions identified
14. overall_relevance: [Low/Medium/High] relevance to our research question
15. evidence_gaps: Brief description of critical missing validation elements

For text fields, place the content in double quotes to properly handle any commas. For fields with multiple options, use the exact values specified in brackets. Please analyze the paper thoroughly before extracting the information. Respond with ONLY the CSV row (no column headers)."""

# Define the column names based on the structure
extraction_columns = [
    "paper_citation", "publication_type", "gcr_types", "geographic_focus",
    "geographic_factors", "institutional_factors", "infrastructural_factors",
    "other_resilience_factors", "study_approach", "resilience_phase",
    "main_resilience_factors", "resilience_tradeoffs", "vulnerable_resilient_regions",
    "overall_relevance", "evidence_gaps"
]

# Process PDFs
pdf_dir = "pdf"  # Directory containing PDF files
temperature = 0   # Keep it as deterministic as possible
max_tokens = 4000  # Increased token limit for more detailed responses
cache_dir = "prompt_cache"  # Directory for caching prompts and responses

# Define configuration for extraction process
config = {
    'output_file': "gcr_resilience_extraction_results.csv",
    'cache_file': os.path.join(cache_dir, "extraction_prompt_cache.json"),
    'query': extraction_query,
    'columns': extraction_columns
}

# Create directories if they don't exist
os.makedirs(pdf_dir, exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)

# Initialize cache and results
cache = {}
results = []
processed_files = set()

# Load cache and existing results
cache_file = config['cache_file']
if os.path.exists(cache_file):
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached responses")
    except Exception as e:
        print(f"Error loading cache: {str(e)}")
else:
    # Create empty cache file if it doesn't exist
    with open(cache_file, 'w') as f:
        json.dump({}, f)
    print("Created new empty cache file")

# Load results
output_file = config['output_file']
if os.path.exists(output_file):
    try:
        df = pd.read_csv(output_file)
        results = df.to_dict('records')
        processed_files = set(df['filename'].tolist())
        print(f"Loaded {len(results)} existing results")
    except Exception as e:
        print(f"Error loading existing results: {str(e)}")

# Process PDFs
pdf_files = list(Path(pdf_dir).glob('*.pdf'))

for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
    if pdf_path.name not in processed_files:
        try:
            print(f"Processing {pdf_path.name}...")
            
            # Extract text
            text = extract_text_from_pdf(str(pdf_path))
            print(f"Extracted {len(text)} characters from PDF.")
            
            # Create cache key
            cache_key = hashlib.md5((text + config['query']).encode()).hexdigest()
            
            # Check for cached response
            if cache_key in cache:
                print(f"Using cached response for {pdf_path.name}")
                response = cache[cache_key]
            else:
                # Process with Claude
                response = process_with_claude(text, config['query'], temperature, max_tokens)
                print(f"Received response of length {len(response)}")
                
                # Cache the response
                cache[cache_key] = response
                
                # Save cache after each new response
                with open(config['cache_file'], 'w') as f:
                    json.dump(cache, f)
                
                # Sleep for 1 minute to avoid rate limits
                print(f"Sleeping for 60 seconds to avoid rate limits...")
                sleep_time.sleep(60)
            
            # Parse the CSV response
            parsed_result = parse_csv_response(response, config['columns'])
            
            # Add the filename for reference
            parsed_result['filename'] = pdf_path.name
            
            # Add to results
            results.append(parsed_result)
            
            # Save intermediate results
            interim_df = pd.DataFrame(results)
            interim_df.to_csv(config['output_file'], index=False)
            
            print(f"Successfully processed {pdf_path.name}")
        
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {str(e)}")
            # Add error record
            error_result = {
                "error": str(e),
                "filename": pdf_path.name
            }
            results.append(error_result)
            
            # Save intermediate results even after errors
            interim_df = pd.DataFrame(results)
            interim_df.to_csv(config['output_file'], index=False)
    else:
        print(f"Skipping already processed file: {pdf_path.name}")

# Create final DataFrame from the results
extraction_df = pd.DataFrame(results)

# Add timestamp for versioned output
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
versioned_extraction_csv = f"{os.path.splitext(config['output_file'])[0]}_{timestamp}.csv"

# Save versioned output
extraction_df.to_csv(config['output_file'], index=False)
extraction_df.to_csv(versioned_extraction_csv, index=False)

print(f"Extraction results saved to {config['output_file']} and {versioned_extraction_csv}")

# Display results
print("Extraction results:")
print(extraction_df.head()) 