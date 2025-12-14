"""
Paper Processing System

This script processes academic papers to extract information about regional resilience
to catastrophic risks using Claude.
"""

# Import required libraries
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import tiktoken
import csv
import json
from io import StringIO
import hashlib
import datetime
import time as sleep_time
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import PyPDF2
import anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Data Structures and Classes

@dataclass
class PaperMetadata:
    """Data class for paper metadata"""
    filename: str
    paper_citation: Optional[str] = None
    publication_type: Optional[str] = None
    gcr_types: Optional[str] = None
    geographic_focus: Optional[str] = None
    geographic_factors: Optional[str] = None
    institutional_factors: Optional[str] = None
    infrastructural_factors: Optional[str] = None
    other_resilience_factors: Optional[str] = None
    study_approach: Optional[str] = None
    resilience_phase: Optional[str] = None
    main_resilience_factors: Optional[str] = None
    resilience_tradeoffs: Optional[str] = None
    vulnerable_resilient_regions: Optional[str] = None
    overall_relevance: Optional[str] = None
    evidence_gaps: Optional[str] = None
    error: Optional[str] = None
    current_query: Optional[str] = None  # Added for token calculations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage, excluding current_query"""
        return {k: v for k, v in self.__dict__.items()
                if v is not None and k != 'current_query'}  # Exclude current_query


class PDFExtractor:
    """Extracts text from PDF files"""
    def extract(self, file_path: Path) -> str:
        """Extract text from a PDF file"""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text


class Tokenizer:
    """Handles text tokenization and truncation"""
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def truncate(self, text: str, ratio: float) -> str:
        """Truncate text to a given ratio of its original length"""
        tokens = self.encoding.encode(text)
        return self.encoding.decode(tokens[:int(len(tokens) * ratio)])


class ClaudeClient:
    """Client for Claude API"""
    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-20250219"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def process_text(self, text: str, query: str, **kwargs) -> str:
        """Process text with Claude"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get('max_tokens', 1000),
            temperature=kwargs.get('temperature', 0),
            system=[{"type": "text", "text": "You are an AI assistant tasked with analyzing documents."}],
            messages=[{"role": "user", "content": f"Document content:\n{text}\n\n{query}"}]
        )
        return response.content[0].text


class FileCache:
    """Simple file-based cache"""
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache: Dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)

    def _save_cache(self) -> None:
        """Save cache to file"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f)

    def get(self, key: str) -> Optional[str]:
        """Get cached response"""
        return self.cache.get(key)

    def set(self, key: str, value: str) -> None:
        """Cache a response"""
        self.cache[key] = value
        self._save_cache()


class CSVStorage:
    """Handles storage of results in CSV format"""

    def __init__(self, output_file: Path):
        self.output_file = output_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.output_file.exists():
            # Create empty file with headers
            df = pd.DataFrame(columns=PaperMetadata.__annotations__.keys())
            df.to_csv(self.output_file, index=False)

    def is_processed(self, filename: str) -> bool:
        """Check if a file has already been processed"""
        try:
            if not self.output_file.exists():
                return False
            df = pd.read_csv(self.output_file)
            return filename in df['filename'].values
        except (FileNotFoundError, pd.errors.EmptyDataError, KeyError, ValueError) as e:
            logger.error("Error checking if file is processed: %s", str(e))
            return False

    def get_processed_files(self) -> set:
        """Get set of all processed filenames"""
        try:
            if not self.output_file.exists():
                return set()
            df = pd.read_csv(self.output_file)
            return set(df['filename'].values)
        except (FileNotFoundError, pd.errors.EmptyDataError, KeyError, ValueError) as e:
            logger.error("Error getting processed files: %s", str(e))
            return set()

    def save_results(self, results: List[PaperMetadata]):
        """Save results to CSV file"""
        try:
            df = pd.DataFrame([r.to_dict() for r in results])
            df.to_csv(self.output_file, index=False)
        except (IOError, OSError, ValueError) as e:
            logger.error("Error saving results: %s", str(e))


class PaperProcessor:
    """Main paper processing class"""

    def __init__(
        self,
        text_extractor: PDFExtractor,
        tokenizer: Tokenizer,
        llm_client: ClaudeClient,
        cache: FileCache,
        storage: CSVStorage,
        max_tokens: int = 4000,
        truncation_ratio: float = 0.8,
        tokens_per_minute: int = 20000,  # Claude's rate limit
        max_total_tokens: int = 200000   # Claude's total token limit
    ):
        self.text_extractor = text_extractor
        self.tokenizer = tokenizer
        self.llm_client = llm_client
        self.cache = cache
        self.storage = storage
        self.max_tokens = max_tokens
        self.truncation_ratio = truncation_ratio
        self.tokens_per_minute = tokens_per_minute
        self.max_total_tokens = max_total_tokens

        # Rate limiting tracking
        self.token_usage = []  # List of (timestamp, token_count) tuples
        self.current_query: Optional[str] = None  # Store current query for token calculations

        # Calculate prompt tokens once
        self.prompt_tokens = self.tokenizer.count_tokens(
            "Document content:\n\n" +  # Base prompt
            "You are an AI assistant tasked with analyzing documents."  # System prompt
        )

    def _calculate_max_paper_tokens(self) -> int:
        """Calculate maximum tokens allowed for the paper text"""
        # Reserve space for the query and other prompt elements
        query_tokens = self.tokenizer.count_tokens(self.current_query)
        reserved_tokens = self.prompt_tokens + query_tokens + 1000  # Add buffer
        return self.max_total_tokens - reserved_tokens

    def _cleanup_old_usage(self):
        """Remove token usage records older than 1 minute"""
        current_time = datetime.datetime.now()
        one_minute_ago = current_time - datetime.timedelta(minutes=1)
        self.token_usage = [(ts, count) for ts, count in self.token_usage if ts > one_minute_ago]

    def _get_current_token_usage(self) -> int:
        """Get total token usage in the last minute"""
        self._cleanup_old_usage()
        return sum(count for _, count in self.token_usage)

    def _wait_for_rate_limit(self, required_tokens: int):
        """Wait if necessary to stay within rate limits"""
        while True:
            current_usage = self._get_current_token_usage()
            if current_usage + required_tokens <= self.tokens_per_minute:
                break

            # Check if we have any usage records
            if not self.token_usage:
                # If no records, we can proceed
                break

            # Calculate how long to wait
            wait_time = 60
            if wait_time > 0:
                logger.info("Rate limit reached. Waiting %.1f seconds...", wait_time)
                sleep_time.sleep(wait_time)
            self._cleanup_old_usage()

    def _record_token_usage(self, token_count: int):
        """Record token usage for rate limiting"""
        self.token_usage.append((datetime.datetime.now(), token_count))

    def process_paper(self, file_path: Path, query: str) -> PaperMetadata:
        """Process a single paper"""
        # Store query for token calculations
        self.current_query = query

        # Extract text
        text = self.text_extractor.extract(file_path)
        logger.info("Extracted %d characters from %s", len(text), file_path.name)

        # Check cache
        cache_key = hashlib.md5((text + query).encode()).hexdigest()
        if cached_response := self.cache.get(cache_key):
            logger.info("Using cached response for %s", file_path.name)
            return self._parse_response(cached_response, file_path.name)

        # Process with LLM
        current_text = text
        while True:
            try:
                # Check rate limit and wait if necessary
                total_tokens = self.tokenizer.count_tokens(current_text) + self.prompt_tokens + self.tokenizer.count_tokens(query)
                self._wait_for_rate_limit(total_tokens)

                # Try to process
                response = self.llm_client.process_text(current_text, query)
                self._record_token_usage(total_tokens)
                self.cache.set(cache_key, response)
                return self._parse_response(response, file_path.name)

            except (ValueError, RuntimeError, AttributeError) as e:
                # Check for token limit errors (could be from various sources)
                error_str = str(e).lower()
                if "too long" in error_str or "token" in error_str and "limit" in error_str:
                    # Truncate to 80% of current length
                    current_tokens = self.tokenizer.count_tokens(current_text)
                    target_tokens = int(current_tokens * self.truncation_ratio)
                    target_tokens = max(1000, target_tokens)  # Ensure minimum length

                    logger.info("Token limit exceeded. Truncating from %d to %d tokens...",
                               current_tokens, target_tokens)
                    tokens = self.tokenizer.encoding.encode(current_text)
                    current_text = self.tokenizer.encoding.decode(tokens[:target_tokens])
                else:
                    raise

    def _parse_response(self, response: str, filename: str) -> PaperMetadata:
        """Parse CSV response into PaperMetadata object"""
        try:
            # Clean the response text
            clean_text = response.strip()

            # Find the first line that looks like a CSV row (has multiple commas)
            # and doesn't contain the prompt text
            lines = clean_text.split('\n')
            csv_line = None
            for line in lines:
                # Skip lines that contain parts of the prompt
                if "research question" in line.lower() or "csv format" in line.lower():
                    continue
                # Find the line with the most commas that's not the prompt
                if line.count(',') >= 10:  # We expect at least 10 commas for our CSV format
                    csv_line = line
                    break

            if not csv_line:
                raise ValueError("No valid CSV line found in response")

            # Parse CSV
            reader = csv.reader(StringIO(csv_line))
            row = next(reader)

            # Create PaperMetadata object with all fields
            return PaperMetadata(
                filename=filename,
                paper_citation=row[0] if len(row) > 0 else None,
                publication_type=row[1] if len(row) > 1 else None,
                gcr_types=row[2] if len(row) > 2 else None,
                geographic_focus=row[3] if len(row) > 3 else None,
                geographic_factors=row[4] if len(row) > 4 else None,
                institutional_factors=row[5] if len(row) > 5 else None,
                infrastructural_factors=row[6] if len(row) > 6 else None,
                other_resilience_factors=row[7] if len(row) > 7 else None,
                study_approach=row[8] if len(row) > 8 else None,
                resilience_phase=row[9] if len(row) > 9 else None,
                main_resilience_factors=row[10] if len(row) > 10 else None,
                resilience_tradeoffs=row[11] if len(row) > 11 else None,
                vulnerable_resilient_regions=row[12] if len(row) > 12 else None,
                overall_relevance=row[13] if len(row) > 13 else None,
                evidence_gaps=row[14] if len(row) > 14 else None,
                current_query=self.current_query
            )
        except (ValueError, IndexError, csv.Error) as e:
            logger.error("Error parsing response for %s: %s", filename, str(e))
            return PaperMetadata(filename=filename, error=str(e))

    def process_directory(self, directory: Path, query: str) -> None:
        """Process all PDF files in a directory"""
        results = []
        pdf_files = list(directory.glob("*.pdf"))

        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                # Skip if already processed
                if self.storage.is_processed(pdf_path.name):
                    logger.info("Loading cached results for: %s", pdf_path.name)
                    # Extract text to generate same cache key
                    text = self.text_extractor.extract(pdf_path)
                    cache_key = hashlib.md5((text + query).encode()).hexdigest()

                    if cached_response := self.cache.get(cache_key):
                        self.current_query = query
                        result = self._parse_response(cached_response, pdf_path.name)
                        results.append(result)
                        continue
                else:
                    logger.warning("File %s marked as processed but no cache found, reprocessing...",
                                 pdf_path.name)

                logger.info("Processing %s...", pdf_path.name)
                result = self.process_paper(pdf_path, query)
                results.append(result)

                # Save after each successful processing
                self.storage.save_results(results)
                logger.info("Successfully processed %s", pdf_path.name)

            except (IOError, OSError, ValueError, KeyError) as e:
                logger.error("Error processing %s: %s", pdf_path.name, str(e))
                # Add error record
                error_result = PaperMetadata(
                    filename=pdf_path.name,
                    error=str(e)
                )
                results.append(error_result)
                # Save even after errors
                self.storage.save_results(results)


def main():
    """Main function to run the paper processing system"""
    # Load API key
    with open("../config/api_key.txt", 'r', encoding='utf-8') as f:
        api_key = f.read().strip()

    # Define extraction query
    query = """I need you to analyze the provided research paper and extract specific information about regional resilience to catastrophic risks. Our research question is: "What specific geographical, institutional, and infrastructural factors have been empirically or theoretically identified as enhancing regional resilience to nuclear winter, large magnitude volcanic eruptions, extreme pandemics, and infrastructure collapse catastrophes, and how do these resilience factors vary across catastrophe types?"

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

CRITICAL CSV FORMATTING REQUIREMENTS:

- Wrap ALL text fields in double quotes, even if they don't contain commas
- If a text field contains double quotes, escape them by doubling them ("")
- Use commas ONLY as field separators between fields
- Do not use any quotes within the field content except for properly escaped ones
- Each field must be enclosed in double quotes: "field content"

Example format: "text field 1","text field 2","text field 3"
The entire row should look like: "field1","field2","field3",...,"field15"

For fields with multiple options, use the exact values specified in brackets. Please analyze the paper thoroughly before extracting the information.
Respond with ONLY the CSV row (no column headers, no additional text).

For text fields, place the content in double quotes to properly handle any commas. For fields with multiple options, use the exact values specified in brackets. Please analyze the paper thoroughly before extracting the information. Respond with ONLY the CSV row (no column headers)."""

    # Initialize components
    text_extractor = PDFExtractor()
    tokenizer = Tokenizer()
    llm_client = ClaudeClient(api_key)
    cache = FileCache(Path("prompt_cache/extraction_prompt_cache.json"))
    storage = CSVStorage(Path("gcr_resilience_extraction_results.csv"))

    # Create processor
    processor = PaperProcessor(
        text_extractor=text_extractor,
        tokenizer=tokenizer,
        llm_client=llm_client,
        cache=cache,
        storage=storage
    )

    # Process papers
    processor.process_directory(Path("pdf"), query)


if __name__ == "__main__":
    main()
