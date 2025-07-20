"""
Paper processing system for extracting information from academic papers using Claude.
Simple, focused implementation with clear separation of concerns.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict
import json
import hashlib
import logging
from datetime import datetime
import csv
from io import StringIO
import time as sleep_time

import anthropic
import PyPDF2
import tiktoken
import pandas as pd
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PaperMetadata:
    """Data class for paper metadata"""
    filename: str
    citation: str
    publication_type: str
    gcr_types: str
    geographic_focus: str
    geographic_factors: str
    institutional_factors: str
    infrastructural_factors: str
    other_resilience_factors: str
    study_approach: str
    resilience_phase: str
    main_resilience_factors: str
    resilience_tradeoffs: str
    vulnerable_resilient_regions: str
    overall_relevance: str
    evidence_gaps: str

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
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
    
    def _save_cache(self) -> None:
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    def get(self, key: str) -> Optional[str]:
        """Get cached response"""
        return self.cache.get(key)
    
    def set(self, key: str, value: str) -> None:
        """Cache a response"""
        self.cache[key] = value
        self._save_cache()

class CSVStorage:
    """Handles saving and loading results to/from CSV"""
    def __init__(self, output_file: Path):
        self.output_file = output_file
    
    def save(self, results: list[PaperMetadata]) -> None:
        """Save results to CSV"""
        df = pd.DataFrame([vars(r) for r in results])
        df.to_csv(self.output_file, index=False)
        
        # Also save a timestamped version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        versioned_file = self.output_file.parent / f"{self.output_file.stem}_{timestamp}.csv"
        df.to_csv(versioned_file, index=False)
    
    def load(self) -> list[PaperMetadata]:
        """Load results from CSV"""
        if not self.output_file.exists():
            return []
        
        df = pd.read_csv(self.output_file)
        return [PaperMetadata(**row) for row in df.to_dict('records')]

class PaperProcessor:
    """Main paper processing class"""
    def __init__(
        self,
        text_extractor: PDFExtractor,
        tokenizer: Tokenizer,
        llm_client: ClaudeClient,
        cache: FileCache,
        storage: CSVStorage,
        max_tokens: int = 150000,
        truncation_ratio: float = 0.8,
        tokens_per_minute: int = 20000  # Claude's rate limit
    ):
        self.text_extractor = text_extractor
        self.tokenizer = tokenizer
        self.llm_client = llm_client
        self.cache = cache
        self.storage = storage
        self.max_tokens = max_tokens
        self.truncation_ratio = truncation_ratio
        self.tokens_per_minute = tokens_per_minute
        
        # Rate limiting tracking
        self.token_usage = []  # List of (timestamp, token_count) tuples
    
    def _cleanup_old_usage(self):
        """Remove token usage records older than 1 minute"""
        current_time = datetime.now()
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
            
            # Calculate how long to wait
            oldest_record = min(ts for ts, _ in self.token_usage)
            wait_time = 60 - (datetime.now() - oldest_record).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                sleep_time.sleep(wait_time)
            self._cleanup_old_usage()
    
    def _record_token_usage(self, token_count: int):
        """Record token usage for rate limiting"""
        self.token_usage.append((datetime.now(), token_count))
    
    def process_paper(self, file_path: Path, query: str) -> PaperMetadata:
        """Process a single paper"""
        # Extract text
        text = self.text_extractor.extract(file_path)
        logger.info(f"Extracted {len(text)} characters from {file_path.name}")
        
        # Check cache
        cache_key = hashlib.md5((text + query).encode()).hexdigest()
        if cached_response := self.cache.get(cache_key):
            logger.info(f"Using cached response for {file_path.name}")
            return self._parse_response(cached_response, file_path.name)
        
        # Process with LLM
        current_text = text
        while True:
            try:
                token_count = self.tokenizer.count_tokens(current_text)
                logger.info(f"Trying with {token_count} tokens...")
                
                # Check rate limit and wait if necessary
                self._wait_for_rate_limit(token_count)
                
                response = self.llm_client.process_text(current_text, query)
                self._record_token_usage(token_count)
                self.cache.set(cache_key, response)
                return self._parse_response(response, file_path.name)
                
            except Exception as e:
                if "too many tokens" in str(e).lower():
                    # Calculate how much to truncate to stay within rate limit
                    max_allowed_tokens = self.tokens_per_minute - self._get_current_token_usage()
                    if max_allowed_tokens <= 0:
                        logger.info("Rate limit reached. Waiting for next minute...")
                        sleep_time.sleep(60)
                        continue
                    
                    # Truncate to either 80% of current length or max allowed tokens, whichever is smaller
                    current_tokens = self.tokenizer.count_tokens(current_text)
                    target_tokens = min(
                        int(current_tokens * self.truncation_ratio),
                        max_allowed_tokens
                    )
                    
                    # Truncate to target tokens
                    tokens = self.tokenizer.encoding.encode(current_text)
                    current_text = self.tokenizer.encoding.decode(tokens[:target_tokens])
                    logger.info(f"Truncating to {target_tokens} tokens to stay within rate limit...")
                else:
                    raise e
    
    def _parse_response(self, response: str, filename: str) -> PaperMetadata:
        """Parse the CSV response from Claude into a PaperMetadata object"""
        # Clean the response text
        clean_text = response.strip()

        # If there are multiple lines, take only the CSV line
        if "\n" in clean_text:
            # Find the line that has the most commas (likely the CSV data)
            lines = clean_text.split('\n')
            clean_text = max(lines, key=lambda x: x.count(','))

        # Parse CSV using the csv module which handles quoted fields properly
        reader = csv.reader(StringIO(clean_text))
        try:
            row = next(reader)
            # Map values to PaperMetadata fields
            return PaperMetadata(
                filename=filename,
                citation=row[0].strip('"'),
                publication_type=row[1].strip('"'),
                gcr_types=row[2].strip('"'),
                geographic_focus=row[3].strip('"'),
                geographic_factors=row[4].strip('"'),
                institutional_factors=row[5].strip('"'),
                infrastructural_factors=row[6].strip('"'),
                other_resilience_factors=row[7].strip('"'),
                study_approach=row[8].strip('"'),
                resilience_phase=row[9].strip('"'),
                main_resilience_factors=row[10].strip('"'),
                resilience_tradeoffs=row[11].strip('"'),
                vulnerable_resilient_regions=row[12].strip('"'),
                overall_relevance=row[13].strip('"'),
                evidence_gaps=row[14].strip('"')
            )
        except (StopIteration, IndexError) as e:
            logger.error(f"Failed to parse CSV response for {filename}: {str(e)}")
            logger.error(f"Raw response: {clean_text}")
            raise ValueError(f"Invalid CSV response format for {filename}") from e
    
    def process_directory(self, directory: Path, query: str) -> None:
        """Process all papers in a directory"""
        # Load existing results
        existing_results = self.storage.load()
        processed_files = {r.filename for r in existing_results}
        
        # Process new files
        for pdf_path in tqdm(list(directory.glob('*.pdf')), desc="Processing PDFs"):
            if pdf_path.name not in processed_files:
                try:
                    result = self.process_paper(pdf_path, query)
                    existing_results.append(result)
                    self.storage.save(existing_results)
                except Exception as e:
                    logger.error(f"Error processing {pdf_path.name}: {str(e)}")

def main():
    """Main entry point"""
    # Load configuration
    with open("config/api_key.txt", 'r') as f:
        api_key = f.read().strip()
    
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
    
    # Define extraction query
    query = """I need you to analyze the provided research paper and extract specific information..."""  # Your full query here
    
    # Process papers
    processor.process_directory(Path("pdf"), query)

if __name__ == "__main__":
    main() 