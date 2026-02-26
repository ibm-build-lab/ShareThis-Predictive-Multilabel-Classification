"""Category matching using cosine similarity with frequency bucketing"""
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
from typing import List, Dict, Tuple
import pandas as pd


class CategoryMatcher:
    """Match text to categories using cosine similarity with frequency bucketing"""
    
    def __init__(self, categories: List[str], category_embeddings: list):
        self.category_df = pd.DataFrame({
            "category": categories,
            "embedding": category_embeddings
        })
        self.bucket_weights = {
            "very high": 0.25,
            "high": 0.2,
            "medium": 0.15,
            "low": 0.05,
            "none": 0.0,
        }
    
    def create_frequency_buckets(self, label_counts: Counter) -> Dict[str, str]:
        """Create frequency buckets for categories"""
        bucket_map = {}
        for cat, freq in label_counts.items():
            if freq >= 30:
                bucket_map[cat] = "very high"
            elif freq >= 20:
                bucket_map[cat] = "high"
            elif freq >= 9:
                bucket_map[cat] = "medium"
            elif freq >= 4:
                bucket_map[cat] = "low"
            else:
                bucket_map[cat] = "none"
        return bucket_map
    
    def get_top_k_categories(
        self, 
        text_embedding: list, 
        bucket_map: Dict[str, str], 
        k: int = 55
    ) -> List[str]:
        """Get top k categories using cosine similarity with frequency bucketing"""
        sims = cosine_similarity([text_embedding], list(self.category_df['embedding']))[0]
        
        adjusted_scores = []
        for idx, cat_row in self.category_df.iterrows():
            cat = cat_row['category']
            sim = sims[idx]
            bucket = bucket_map.get(cat, "low")
            bonus = self.bucket_weights.get(bucket, 0.0)
            adjusted = sim + bonus
            adjusted_scores.append((cat, adjusted))
        
        top_k = sorted(adjusted_scores, key=lambda x: x[1], reverse=True)[:k]
        return [cat for cat, _ in top_k]
