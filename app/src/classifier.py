"""Text classification using IBM Watsonx AI"""
from ibm_watsonx_ai.credentials import Credentials
from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.foundation_models import ModelInference
from typing import List, Optional
import ast


class TextClassifier:
    """Classify text using IBM Watsonx AI LLM"""
    
    def __init__(
        self, 
        api_key: str, 
        project_id: str,
        url: str = "https://us-south.ml.cloud.ibm.com",
        model_id: str = "mistralai/mistral-small-3-1-24b-instruct-2503"
    ):
        credentials = Credentials(url=url, api_key=api_key)
        
        parameters = {
            "decoding_method": "sample",
            "temperature": 0.1,
            "max_new_tokens": 200,
            "min_new_tokens": 1,
            "repetition_penalty": 1,
            "stop_sequences": ["]"]
        }
        
        self.model = ModelInference(
            model_id=model_id,
            params=parameters,
            credentials=credentials,
            project_id=project_id
        )
    
    def predict_categories(
        self, 
        url: str, 
        text: str, 
        top_k_categories: List[str],
        examples: str
    ) -> List[str]:
        """Predict categories for given text"""
        prompt = f"""You are a researcher tasked with looking at a webpage url and deciding which category or 
    categories the webpage should be assigned based on provided url and text. The webpage can be assigned a minimum
    of 1 category and a maximum of 7 categories, but the average is 2.5 and the mode is 2.
    Make your selections ONLY from the following categories. Do not make up other categories, if the webpage url 
    and content do not fit a clear category, just pick the closest option from the given categories: 
        {top_k_categories}
        
        EXAMPLES:
        {examples}
        
        INPUT TO CATEGORIZE:
        url:
        {url}
        
        content: 
        {text}
        
        categories:"""
        
        result = self.model.generate_text(prompt=prompt, guardrails=False)
        return self._parse_result(result)
    
    def _parse_result(self, result: str) -> List[str]:
        """Parse LLM result to list of categories"""
        if isinstance(result, str):
            result = result.strip()
            if result.startswith('[') and not result.endswith(']'):
                result += ']'
            try:
                return ast.literal_eval(result)
            except (SyntaxError, ValueError):
                return []
        return result if isinstance(result, list) else []