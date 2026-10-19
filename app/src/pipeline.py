"""Main classification pipeline"""
import pandas as pd
from collections import Counter
from typing import List, Dict, Optional, Any
from .embeddings import EmbeddingGenerator
from .category_matcher import CategoryMatcher
from .classifier import TextClassifier
from .cos_reader import COSReader
from .web_scraper import WebScraper
from .extractors import KeywordEntityExtractor


class ClassificationPipeline:
    """End-to-end text classification pipeline"""
    
    def __init__(
        self,
        watsonx_api_key: str,
        watsonx_project_id: str,
        data_path: str = "with_label.csv",
        use_cos: bool = False,
        cos_api_key: Optional[str] = None,
        cos_endpoint: Optional[str] = None,
        cos_bucket: Optional[str] = None,
        cos_object_key: Optional[str] = None
    ):
        self.data_path = data_path
        self.use_cos = use_cos
        self.cos_bucket = cos_bucket
        self.cos_object_key = cos_object_key
        
        self.embedding_generator = EmbeddingGenerator()
        self.classifier = TextClassifier(
            api_key=watsonx_api_key,
            project_id=watsonx_project_id
        )
        
        # Initialize COS reader if needed
        self.cos_reader = None
        if use_cos:
            if not all([cos_api_key, cos_endpoint, cos_bucket, cos_object_key]):
                raise ValueError(
                    "When use_cos=True, cos_api_key, cos_endpoint, cos_bucket, "
                    "and cos_object_key must be provided"
                )
            self.cos_reader = COSReader(
                api_key=cos_api_key,
                endpoint_url=cos_endpoint
            )
        
        # Initialize data structures
        self.df = None
        self.unique_categories = None
        self.category_matcher = None
        self.bucket_map = None
        self.examples_string = None
        
        # Initialize web scraper and extractor
        self.web_scraper = WebScraper(timeout=30, max_retries=3)
        self.extractor = None  # Will be initialized after model is created
    
    def load_and_prepare_data(self):
        """Load and prepare training data"""
        # Load data from COS or local file
        if self.use_cos and self.cos_reader:
            self.df = self.cos_reader.read_csv(
                bucket=self.cos_bucket,
                object_key=self.cos_object_key
            )
        else:
            self.df = pd.read_csv(self.data_path)
        
        self.df['label'] = self.df['label'].apply(eval)
        self.df['text'] = self.df['text'].apply(lambda x: ' '.join(str(x).split()[:500]))
        
        # Replace underscores with spaces
        self.df['label'] = self.df['label'].apply(
            lambda labels: [label.replace("_", " ") for label in labels] if isinstance(labels, list) else labels
        )
        
        # Extract third-level categories
        self.df['categories'] = self.df['label'].apply(lambda lst: [
            '/'.join(s.strip('/').split('/')[2:3])
            for s in lst
            if len(s.strip('/').split('/')) >= 3
        ])
        
        # Remove duplicates and filter empty categories
        self.df['categories'] = self.df['categories'].apply(lambda lst: list(dict.fromkeys(lst)))
        self.df['categories_count'] = self.df['categories'].apply(len)
        self.df = self.df[self.df['categories_count'] != 0]
        
        # Get unique categories
        self.unique_categories = sorted(set(cat for row in self.df['categories'] for cat in row))
        
        return self
    
    def generate_embeddings(self):
        """Generate embeddings for categories and text"""
        # Embed categories
        category_embeddings = self.embedding_generator.encode(self.unique_categories)
        
        # Embed text
        content = self.df['text'].astype(str).tolist()
        content_embeddings = self.embedding_generator.encode(content)
        self.df['text_embedding'] = list(content_embeddings)
        
        # Initialize category matcher
        self.category_matcher = CategoryMatcher(
            categories=self.unique_categories,
            category_embeddings=list(category_embeddings)
        )
        
        return self
    
    def create_frequency_buckets(self):
        """Create frequency buckets for categories"""
        all_labels = self.df['categories'].explode()
        label_counts = Counter(all_labels)
        self.bucket_map = self.category_matcher.create_frequency_buckets(label_counts)
        
        return self
    
    def prepare_examples(self, n_samples: int = 10):
        """Prepare example strings for prompting"""
        sample = self.df.sample(n=n_samples, random_state=42)
        sample = sample[['url', 'text', 'categories']]
        
        result_string = []
        for i, r in sample.iterrows():
            row_string = f"url:{r['url']}, page content:{r['text']}, Categories:{r['categories']}"
            result_string.append(row_string)
        
        self.examples_string = "\n".join(result_string)
        
        return self
    
    def classify_text(self, url: str, text: str, k: int = 55) -> List[str]:
        """Classify a single text"""
        # Truncate text to 500 words
        text = ' '.join(str(text).split()[:500])
        
        # Generate embedding
        text_embedding = self.embedding_generator.encode([text])[0]
        
        # Get top k categories
        top_k_categories = self.category_matcher.get_top_k_categories(
            text_embedding=text_embedding,
            bucket_map=self.bucket_map,
            k=k
        )
        
        # Predict final categories
        predicted_categories = self.classifier.predict_categories(
            url=url,
            text=text,
            top_k_categories=top_k_categories,
            examples=self.examples_string
        )
        
        # Filter valid categories
        valid_set = set(s.strip() for s in self.unique_categories)
        predicted_categories = [
            p.strip() for p in predicted_categories
            if isinstance(p, str) and p.strip() in valid_set
        ]
        
        return predicted_categories
    
    def initialize_extractor(self):
        """Initialize the keyword and entity extractor with the classifier's model"""
        if self.classifier and self.classifier.model:
            self.extractor = KeywordEntityExtractor(self.classifier.model)
        return self
    
    def extract_keywords_from_text(self, text: str, url: str = "", max_keywords: int = 10) -> Dict[str, Any]:
        """
        Extract keywords, phrases, and concepts from text.
        
        Args:
            text (str): Text to analyze
            url (str): Optional URL for context
            max_keywords (int): Maximum number of keywords to extract
            
        Returns:
            Dict[str, Any]: Dictionary containing theme, keywords, phrases, and concepts
        """
        if not self.extractor:
            self.initialize_extractor()
        
        if not self.extractor:
            raise ValueError("Extractor not initialized. Ensure classifier is properly set up.")
        
        return self.extractor.extract_keywords(text, url, max_keywords)
    
    def extract_entities_from_text(self, text: str, url: str = "") -> Dict[str, List[str]]:
        """
        Extract named entities from text.
        
        Args:
            text (str): Text to analyze
            url (str): Optional URL for context
            
        Returns:
            Dict[str, List[str]]: Dictionary containing entity categories
        """
        if not self.extractor:
            self.initialize_extractor()
        
        if not self.extractor:
            raise ValueError("Extractor not initialized. Ensure classifier is properly set up.")
        
        return self.extractor.extract_entities(text, url)
    
    def analyze_url(self, url: str, k: int = 55, max_keywords: int = 10) -> Dict[str, Any]:
        """
        Comprehensive analysis of a URL: scrape content, classify, extract keywords and entities.
        
        Args:
            url (str): URL to analyze
            k (int): Number of top categories to consider
            max_keywords (int): Maximum number of keywords to extract
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - url: Original URL
                - status: 'success' or 'error'
                - categories: List of predicted categories
                - keywords: Extracted keywords information
                - entities: Extracted named entities
                - metadata: Basic metadata from scraping
                - raw_text: Raw extracted text before cleaning
                - cleaned_text: Cleaned text used for analysis
                - error: Error message (if status is 'error')
        """
        result = {
            'url': url,
            'status': 'error',
            'categories': [],
            'keywords': {},
            'entities': {},
            'metadata': {},
            'raw_text': None,
            'cleaned_text': None,
            'error': None
        }
        
        # Step 1: Scrape the URL
        scrape_result = self.web_scraper.scrape(url)
        
        if scrape_result['status'] != 'success':
            result['error'] = scrape_result.get('error', 'Failed to scrape URL')
            return result
        
        # Store raw text (before cleaning)
        raw_text = scrape_result.get('raw_text', '')
        cleaned_text = scrape_result['cleaned_text']
        
        if not cleaned_text:
            result['error'] = 'No text content extracted from URL'
            return result
        
        # Store both raw and cleaned text
        result['raw_text'] = raw_text
        result['cleaned_text'] = cleaned_text
        
        # Store basic metadata
        result['metadata'] = {
            'title': scrape_result['metadata'].get('title'),
            'description': scrape_result['metadata'].get('description'),
            'domain': scrape_result['metadata'].get('domain'),
            'word_count': scrape_result['metadata'].get('word_count')
        }
        
        try:
            # Use cleaned_text for all operations for consistency
            text = cleaned_text
            
            # Step 2: Classify text into categories
            categories = self.classify_text(url=url, text=text, k=k)
            result['categories'] = categories
            
            # Step 3: Extract keywords
            keywords = self.extract_keywords_from_text(text=text, url=url, max_keywords=max_keywords)
            result['keywords'] = keywords
            
            # Step 4: Extract entities
            entities = self.extract_entities_from_text(text=text, url=url)
            result['entities'] = entities
            
            result['status'] = 'success'
            
        except Exception as e:
            result['error'] = f"Analysis error: {str(e)}"
            return result
        
        return result
