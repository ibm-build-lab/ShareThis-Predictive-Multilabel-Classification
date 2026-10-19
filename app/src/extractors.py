"""
Keyword and Entity Extraction Module
====================================

Extracts keywords, phrases, concepts, and named entities from text using IBM WatsonX.ai.

Features:
- Keyword extraction (single words, phrases, concepts, themes)
- Named entity recognition (PERSON, ORGANIZATION, LOCATION, DATE, EVENT, PRODUCT, OTHER)
- Structured JSON output
- Error handling and fallback mechanisms
"""

import json
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KeywordEntityExtractor:
    """
    Extract keywords and entities from text using IBM WatsonX.ai foundation models.
    """
    
    def __init__(self, model):
        """
        Initialize the extractor with a WatsonX.ai model.
        
        Args:
            model: IBM WatsonX.ai ModelInference instance
        """
        self.model = model
    
    def extract_keywords(self, text: str, url: str = "", max_keywords: int = 10) -> Dict[str, Any]:
        """
        Extract keywords, phrases, and concepts from text.
        
        Args:
            text (str): Text to analyze
            url (str): Optional URL for context
            max_keywords (int): Maximum number of keywords to extract
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - theme: Main topic of the text
                - keywords: List of important single-word terms
                - phrases: List of important multi-word key phrases
                - concepts: List of high-level themes and core ideas
        """
        prompt = f"""[INST]

You are an expert NLP information extraction system.

TASK:
Analyze the given text and extract the most important information into three distinct categories:

1. keywords → Important single-word terms only
2. phrases → Important multi-word key phrases only
3. concepts → High-level themes, categories, or core ideas discussed in the text

PRE-REQUIRED THEME UNDERSTANDING:
Before extraction, first understand:
- the main subject of the text
- the domain it belongs to
- the primary discussion theme
- the important technical context

Then perform extraction based on semantic importance, not just word frequency.

STRICT EXTRACTION RULES:
- Extract up to {max_keywords} total items across all categories combined
- keywords must contain only single meaningful words
- phrases must contain only multi-word expressions
- concepts must represent broader ideas, categories, or major themes
- Do NOT duplicate the same term across categories
- Do NOT repeat the same idea in slightly different forms
- Do NOT include sub-phrases if a stronger full phrase exists

Example:
Prefer "Natural Language Processing" over "Language Processing"

- Prefer complete and meaningful expressions
- Preserve exact technical names where relevant
- Exclude generic words, filler words, weak terms, and low-value tokens
- Prioritize domain-specific and contextually important information
- Keep output concise, clean, and highly relevant

STRICT OUTPUT RULES:
- Return ONLY valid JSON
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include notes
- Do NOT include additional text before or after JSON
- If unsure, return empty arrays instead of explanations

RETURN EXACTLY IN THIS JSON STRUCTURE:

{{
  "theme": "main topic of the text",
  "keywords": [
    "keyword1",
    "keyword2"
  ],
  "phrases": [
    "key phrase 1",
    "key phrase 2"
  ],
  "concepts": [
    "core concept 1",
    "core concept 2"
  ]
}}

TEXT:
{text}

[/INST]"""

        try:
            logger.info(f"Extracting keywords from text (length: {len(text)})")
            
            result = self.model.generate_text(
                prompt=prompt,
                guardrails=False
            )
            
            result = result.strip()
            logger.info(f"Raw keyword extraction result: {result[:200]}...")
            
            # Try to extract JSON from the response
            # Remove markdown code blocks if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            
            # Find JSON object in the response
            start_idx = result.find("{")
            end_idx = result.rfind("}")
            
            if start_idx != -1 and end_idx != -1:
                json_text = result[start_idx:end_idx + 1]
                
                try:
                    parsed_result = json.loads(json_text)
                    
                    # Safety fallback for missing keys
                    extracted = {
                        "theme": parsed_result.get("theme", ""),
                        "keywords": parsed_result.get("keywords", []),
                        "phrases": parsed_result.get("phrases", []),
                        "concepts": parsed_result.get("concepts", []),
                        "extraction_status": "success"
                    }
                    logger.info(f"Successfully extracted keywords: {len(extracted['keywords'])} keywords, {len(extracted['phrases'])} phrases")
                    return extracted
                    
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decode error: {str(je)}")
                    logger.error(f"Attempted to parse: {json_text[:200]}...")
            
            logger.warning(f"Invalid JSON response received for keyword extraction. Response: {result[:200]}...")
            return {
                "theme": "",
                "keywords": [],
                "phrases": [],
                "concepts": [],
                "extraction_status": "failed",
                "error": "Invalid JSON response",
                "raw_response": result[:500]
            }
        
        except Exception as e:
            logger.error(f"Keyword extraction error: {str(e)}")
            return {
                "theme": "",
                "keywords": [],
                "phrases": [],
                "concepts": [],
                "extraction_status": "error",
                "error": str(e)
            }
    
    def extract_entities(self, text: str, url: str = "") -> Dict[str, List[str]]:
        """
        Extract named entities from text.
        
        Args:
            text (str): Text to analyze
            url (str): Optional URL for context
            
        Returns:
            Dict[str, List[str]]: Dictionary containing entity categories:
                - PERSON: Individual people, authors, researchers, founders
                - ORGANIZATION: Companies, institutions, universities, agencies
                - LOCATION: Countries, cities, states, regions, landmarks
                - DATE: Specific dates, years, months, time references
                - EVENT: Conferences, wars, launches, festivals, historical events
                - PRODUCT: Software, tools, applications, devices, frameworks
                - OTHER: Important named entities that don't fit above categories
        """
        prompt = f"""[INST]

You are an expert Named Entity Recognition (NER) and entity extraction system.

TASK:
Analyze the given text and extract all important named entities, then categorize them into the appropriate entity types.

ENTITY CATEGORIES:
- PERSON → Individual people, authors, researchers, founders, public figures
- ORGANIZATION → Companies, institutions, universities, agencies, teams, brands
- LOCATION → Countries, cities, states, regions, landmarks, places
- DATE → Specific dates, years, months, time references
- EVENT → Conferences, wars, launches, festivals, historical events, major occurrences
- PRODUCT → Software, tools, applications, devices, frameworks, commercial products
- OTHER → Important named entities that do not clearly fit the above categories

PRE-ANALYSIS:
Before extraction, first understand:
- the main subject of the text
- the domain and context
- whether the term is truly a named entity or just a generic noun

Then perform entity extraction based on contextual meaning, not only capitalization.

STRICT EXTRACTION RULES:
- Extract only meaningful named entities
- Do NOT include generic words or common nouns
- Do NOT include duplicate entities
- Do NOT repeat the same entity in multiple categories
- Preserve exact entity names as written when possible
- Prefer full entity names over partial names

Example:
Prefer "Stanford University" over "Stanford"

- Ignore weak references unless they are contextually important
- Keep output clean, precise, and domain-relevant

STRICT OUTPUT RULES:
- Return ONLY valid JSON
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include notes
- Do NOT include additional text before or after JSON
- If no entities exist for a category, return an empty array
- If unsure, return empty arrays instead of explanations

RETURN EXACTLY IN THIS JSON STRUCTURE:

{{
  "PERSON": [],
  "ORGANIZATION": [],
  "LOCATION": [],
  "DATE": [],
  "EVENT": [],
  "PRODUCT": [],
  "OTHER": []
}}

TEXT:
{text}

[/INST]"""

        try:
            logger.info(f"Extracting entities from text (length: {len(text)})")
            
            result = self.model.generate_text(
                prompt=prompt,
                guardrails=False
            )
            
            result = result.strip()
            logger.info(f"Raw entity extraction result: {result[:200]}...")
            
            # Try to extract JSON from the response
            # Remove markdown code blocks if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            
            # Find JSON object in the response
            start_idx = result.find("{")
            end_idx = result.rfind("}")
            
            if start_idx != -1 and end_idx != -1:
                json_text = result[start_idx:end_idx + 1]
                
                try:
                    parsed_result = json.loads(json_text)
                    
                    # Ensure all required keys exist
                    extracted = {
                        "PERSON": parsed_result.get("PERSON", []),
                        "ORGANIZATION": parsed_result.get("ORGANIZATION", []),
                        "LOCATION": parsed_result.get("LOCATION", []),
                        "DATE": parsed_result.get("DATE", []),
                        "EVENT": parsed_result.get("EVENT", []),
                        "PRODUCT": parsed_result.get("PRODUCT", []),
                        "OTHER": parsed_result.get("OTHER", []),
                        "extraction_status": "success"
                    }
                    
                    total_entities = sum(len(v) for k, v in extracted.items() if k != "extraction_status")
                    logger.info(f"Successfully extracted {total_entities} entities")
                    return extracted
                    
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decode error: {str(je)}")
                    logger.error(f"Attempted to parse: {json_text[:200]}...")
            
            logger.warning(f"Invalid JSON response received for entity extraction. Response: {result[:200]}...")
            return {
                "PERSON": [],
                "ORGANIZATION": [],
                "LOCATION": [],
                "DATE": [],
                "EVENT": [],
                "PRODUCT": [],
                "OTHER": [],
                "extraction_status": "failed",
                "error": "Invalid JSON response",
                "raw_response": result[:500]
            }
        
        except Exception as e:
            logger.error(f"Entity extraction error: {str(e)}")
            return {
                "PERSON": [],
                "ORGANIZATION": [],
                "LOCATION": [],
                "DATE": [],
                "EVENT": [],
                "PRODUCT": [],
                "OTHER": [],
                "extraction_status": "error",
                "error": str(e)
            }
