"""Main classification pipeline"""
import pandas as pd
from collections import Counter
from typing import List, Dict, Optional
from .embeddings import EmbeddingGenerator
from .category_matcher import CategoryMatcher
from .classifier import TextClassifier
from .cos_reader import COSReader


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
