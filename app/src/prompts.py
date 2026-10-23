"""
Unified prompt builder for all analysis features.

All three tasks (categories, keywords/phrases, entities, concepts) are
requested in a single LLM call that returns one JSON blob.
"""
from typing import List


def build_unified_prompt(
    text: str,
    url: str,
    top_k_categories: List[str],
    examples: str,
    categories_limit: int = 3,
    keywords_limit: int = 20,
    entities_limit: int = 10,
    concepts_limit: int = 10,
) -> str:
    """
    Build a single Mistral-instruct prompt that returns all four features
    (categories, keywords, entities, concepts) in one JSON response.

    Args:
        text: Page text truncated to ~500 words.
        url: Original page URL.
        top_k_categories: Candidate category list from embedding retrieval.
        examples: Few-shot example string built during pipeline startup.
        categories_limit: Max number of category objects to return.
        keywords_limit: Max total keywords + phrases to return.
        entities_limit: Max entities per entity type.
        concepts_limit: Max concepts to return.

    Returns:
        Formatted prompt string ready to send to ModelInference.generate_text().
    """
    categories_str = "\n".join(f"  - {c}" for c in top_k_categories)

    return f"""[INST]
You are an expert content analysis system. Given a webpage URL and its text content, you must perform four analysis tasks simultaneously and return the results as a single valid JSON object.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — CATEGORIES (return at most {categories_limit})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Select the most relevant categories ONLY from the list below. Do NOT invent categories outside this list.
For each selected category:
- Format the label as a lowercase slug path using underscores and slashes, e.g. /home_&_garden/furniture/storage
- Assign a confidence score from 0.0 to 1.0 (higher = more confident)
- Return them sorted by score descending
- Return at most {categories_limit} categories

ALLOWED CATEGORIES:
{categories_str}

FEW-SHOT EXAMPLES (url → categories):
{examples}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — KEYWORDS & PHRASES (return at most {keywords_limit} items combined)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- theme: one concise phrase naming the main topic
- keywords: important single-word terms only (no duplicates)
- phrases: important multi-word expressions only (no duplicates)
- Do NOT repeat the same idea across keywords and phrases
- Combined keywords + phrases must not exceed {keywords_limit} items

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — NAMED ENTITIES (at most {entities_limit} per type)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extract named entities into these types:
- PERSON: individual people, authors, public figures
- ORGANIZATION: companies, institutions, brands
- LOCATION: countries, cities, regions, places
- DATE: specific dates, years, time references
- EVENT: conferences, product launches, historical events
- PRODUCT: software, tools, devices, frameworks, commercial products
- OTHER: named entities that don't fit above types

Rules:
- Extract only true named entities — not generic nouns
- No duplicates within or across types
- Prefer full names (e.g. "Stanford University" over "Stanford")
- Each type must not exceed {entities_limit} items

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — CONCEPTS (return at most {concepts_limit})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- High-level themes, domains, or core ideas discussed in the text
- Broader than keywords — e.g. "DIY modifications", "Product compatibility"
- Do NOT duplicate items already in keywords or phrases
- Return at most {concepts_limit} concepts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Return ONLY valid JSON — no markdown fences, no explanations, no notes
- Do NOT include any text before or after the JSON object
- If a list has no items, return an empty array []
- All string values must be properly escaped

RETURN EXACTLY THIS JSON STRUCTURE:
{{
  "categories": [
    {{"label": "/slug/path/here", "score": 0.9}},
    {{"label": "/slug/path/here", "score": 0.7}}
  ],
  "keywords": {{
    "theme": "main topic in a short phrase",
    "keywords": ["word1", "word2"],
    "phrases": ["multi word phrase 1", "multi word phrase 2"]
  }},
  "entities": {{
    "PERSON": [],
    "ORGANIZATION": [],
    "LOCATION": [],
    "DATE": [],
    "EVENT": [],
    "PRODUCT": [],
    "OTHER": []
  }},
  "concepts": ["concept 1", "concept 2"]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL: {url}

TEXT:
{text}
[/INST]"""
