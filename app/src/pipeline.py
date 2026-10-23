"""
Main classification pipeline.

Loads training data, builds embeddings, and exposes analyze_url() which
scrapes a URL, retrieves candidate categories via embedding similarity,
calls WatsonX with a single unified prompt, and parses the response.
"""
import json
import logging
import re
import traceback
from collections import Counter
from typing import Any, Dict, List, Optional

import pandas as pd

from .category_matcher import CategoryMatcher
from .embeddings import EmbeddingGenerator
from .prompts import build_unified_prompt
from .watsonx_client import WatsonxClient
from .web_scraper import WebScraper

logger = logging.getLogger(__name__)

# Entity types expected in the model response
_ENTITY_TYPES = ("PERSON", "ORGANIZATION", "LOCATION", "DATE", "EVENT", "PRODUCT", "OTHER")


class ClassificationPipeline:
    """End-to-end text analysis pipeline (scrape → embed → prompt → parse)."""

    def __init__(
        self,
        watsonx_api_key: str,
        watsonx_project_id: str,
        watsonx_url: str = "https://us-south.ml.cloud.ibm.com",
        model_id: str = "mistralai/mistral-small-3-2-24b-instruct-2506",
        data_path: str = "with_label.csv",
        max_retries: int = 3,
    ):
        self.data_path = data_path

        self.embedding_generator = EmbeddingGenerator()
        self.watsonx_client = WatsonxClient(
            api_key=watsonx_api_key,
            project_id=watsonx_project_id,
            url=watsonx_url,
            model_id=model_id,
            max_retries=max_retries,
        )
        self.web_scraper = WebScraper(timeout=30, max_retries=3)

        # Populated by prepare()
        self.df: Optional[pd.DataFrame] = None
        self.unique_categories: Optional[List[str]] = None
        self.category_matcher: Optional[CategoryMatcher] = None
        self.bucket_map: Optional[Dict[str, str]] = None
        self.examples_string: Optional[str] = None
        self._ready = False

    # ------------------------------------------------------------------ #
    # Startup preparation                                                   #
    # ------------------------------------------------------------------ #

    def prepare(self) -> "ClassificationPipeline":
        """Load data, build embeddings, and prepare few-shot examples."""
        self._load_and_prepare_data()
        self._generate_embeddings()
        self._create_frequency_buckets()
        self._prepare_examples()
        self._ready = True
        logger.info("Pipeline ready | categories=%d", len(self.unique_categories))
        return self

    @property
    def is_ready(self) -> bool:
        return self._ready

    def _load_and_prepare_data(self):
        logger.info("Loading data from %s", self.data_path)
        self.df = pd.read_csv(self.data_path)
        self.df["label"] = self.df["label"].apply(eval)
        self.df["text"] = self.df["text"].apply(lambda x: " ".join(str(x).split()[:500]))

        # Replace underscores with spaces in labels
        self.df["label"] = self.df["label"].apply(
            lambda labels: [l.replace("_", " ") for l in labels]
            if isinstance(labels, list)
            else labels
        )

        # Extract third-level categories
        self.df["categories"] = self.df["label"].apply(
            lambda lst: [
                "/".join(s.strip("/").split("/")[2:3])
                for s in lst
                if len(s.strip("/").split("/")) >= 3
            ]
        )

        self.df["categories"] = self.df["categories"].apply(
            lambda lst: list(dict.fromkeys(lst))
        )
        self.df["categories_count"] = self.df["categories"].apply(len)
        self.df = self.df[self.df["categories_count"] != 0]

        self.unique_categories = sorted(
            set(cat for row in self.df["categories"] for cat in row)
        )

    def _generate_embeddings(self):
        logger.info("Generating embeddings for %d categories", len(self.unique_categories))
        category_embeddings = self.embedding_generator.encode(self.unique_categories)
        content_embeddings = self.embedding_generator.encode(
            self.df["text"].astype(str).tolist()
        )
        self.df["text_embedding"] = list(content_embeddings)
        self.category_matcher = CategoryMatcher(
            categories=self.unique_categories,
            category_embeddings=list(category_embeddings),
        )

    def _create_frequency_buckets(self):
        all_labels = self.df["categories"].explode()
        label_counts = Counter(all_labels)
        self.bucket_map = self.category_matcher.create_frequency_buckets(label_counts)

    def _prepare_examples(self, n_samples: int = 10):
        sample = self.df.sample(n=n_samples, random_state=42)[["url", "text", "categories"]]
        rows = [
            f"url:{r['url']}, page content:{r['text']}, Categories:{r['categories']}"
            for _, r in sample.iterrows()
        ]
        self.examples_string = "\n".join(rows)

    # ------------------------------------------------------------------ #
    # Main analysis entry-point                                             #
    # ------------------------------------------------------------------ #

    def analyze_url(
        self,
        url: str,
        k: int = 55,
        categories_limit: int = 3,
        keywords_limit: int = 20,
        entities_limit: int = 10,
        concepts_limit: int = 10,
        return_analyzed_text: bool = False,
    ) -> Dict[str, Any]:
        """
        Scrape a URL and run the full analysis pipeline.

        Returns a dict with keys: url, status, categories, keywords,
        entities, concepts, metadata, analyzed_text (optional), error.
        """
        result: Dict[str, Any] = {
            "url": url,
            "status": "error",
            "categories": [],
            "keywords": {"theme": "", "keywords": [], "phrases": []},
            "entities": {t: [] for t in _ENTITY_TYPES},
            "concepts": [],
            "metadata": {},
            "analyzed_text": None,
            "error": None,
            "error_code": None,
        }

        # Step 1 — scrape
        # Any failure here returns a detailed user-facing message from the scraper.
        # We never proceed to an LLM call if we have no text.
        scrape = self.web_scraper.scrape(url)
        if scrape["status"] != "success":
            result["error"] = scrape.get("error", "Failed to scrape the URL.")
            result["error_code"] = scrape.get("error_code", "UNKNOWN")
            logger.warning(
                "Scrape failed for %s [%s]: %s",
                url,
                result["error_code"],
                result["error"],
            )
            return result

        raw_text = scrape.get("raw_text", "")
        cleaned_text = scrape.get("cleaned_text", "")
        source_text = raw_text if raw_text.strip() else cleaned_text

        # Hard gate — no LLM call if there is no usable text
        if not source_text.strip():
            result["error"] = (
                "The page was fetched but contained no readable text. "
                "The page may be blank, behind a login wall, or consist only of "
                "images and media."
            )
            result["error_code"] = "EMPTY_CONTENT"
            logger.warning("Empty content after scraping %s — skipping LLM call", url)
            return result

        analysis_text = " ".join(source_text.split()[:500])

        result["metadata"] = {
            "title": scrape["metadata"].get("title"),
            "description": scrape["metadata"].get("description"),
            "domain": scrape["metadata"].get("domain"),
            "word_count": scrape["metadata"].get("word_count"),
        }

        if return_analyzed_text:
            result["analyzed_text"] = raw_text

        # Step 2 — retrieve top-k candidate categories via embedding similarity
        text_embedding = self.embedding_generator.encode([analysis_text])[0]
        top_k_categories = self.category_matcher.get_top_k_categories(
            text_embedding=text_embedding,
            bucket_map=self.bucket_map,
            k=k,
        )

        # Step 3 — single LLM call
        try:
            prompt = build_unified_prompt(
                text=analysis_text,
                url=url,
                top_k_categories=top_k_categories,
                examples=self.examples_string,
                categories_limit=categories_limit,
                keywords_limit=keywords_limit,
                entities_limit=entities_limit,
                concepts_limit=concepts_limit,
            )
            call = self.watsonx_client.generate(prompt)
        except Exception as exc:
            traceback.print_exc()
            logger.exception("WatsonX call failed for %s: %s", url, exc)
            result["error"] = f"Model inference failed: {exc}"
            return result

        # Log a concise per-request summary (telemetry stays in logs only)
        t = call.telemetry
        logger.info(
            "Request telemetry | url=%s | input_tokens=%d | output_tokens=%d | "
            "total_tokens=%d | stop_reason=%s | latency_ms=%.1f | attempts=%d",
            url,
            t.input_tokens,
            t.output_tokens,
            t.total_tokens,
            t.stop_reason,
            t.latency_ms,
            t.attempts,
        )

        # Step 4 — parse JSON response
        try:
            parsed = self._parse_json_response(call.text)
        except Exception as exc:
            logger.error(
                "JSON parse failed | url=%s error=%s | raw=%s",
                url, exc, call.text[:300],
            )
            result["error"] = f"Failed to parse model response: {exc}"
            return result

        # Step 5 — post-process and assemble result
        result["categories"] = self._process_categories(
            parsed.get("categories", []), categories_limit
        )
        result["keywords"] = self._process_keywords(parsed.get("keywords", {}))
        result["entities"] = self._process_entities(
            parsed.get("entities", {}), entities_limit
        )
        result["concepts"] = parsed.get("concepts", [])[:concepts_limit]
        result["status"] = "success"

        return result

    # ------------------------------------------------------------------ #
    # Parsing helpers                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_json_response(raw: str) -> Dict[str, Any]:
        """Extract and parse the JSON object from the model's raw text output."""
        text = raw.strip()

        # Strip markdown code fences if present
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        # Find the outermost JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in model response")

        return json.loads(text[start : end + 1])

    @staticmethod
    def _process_categories(
        raw_categories: List[Any], limit: int
    ) -> List[Dict[str, Any]]:
        """Validate and sanitize category objects [{label, score}]."""
        valid_category_set = None  # checked per-pipeline in pipeline; skipped here
        result = []
        seen = set()

        for item in raw_categories:
            if not isinstance(item, dict):
                continue
            label = item.get("label", "")
            score = item.get("score", 0.0)

            if not label:
                continue

            # Sanitize label — lowercase, spaces → underscores, keep /&_-
            label = label.lower().strip()
            label = re.sub(r"[^\w/&_\-]", "_", label)
            label = re.sub(r"_+", "_", label)
            if not label.startswith("/"):
                label = "/" + label

            if label in seen:
                continue
            seen.add(label)

            try:
                score = float(score)
                score = max(0.0, min(1.0, score))
            except (TypeError, ValueError):
                score = 0.5

            result.append({"label": label, "score": round(score, 2)})

        # Sort by score descending and enforce limit
        result.sort(key=lambda x: x["score"], reverse=True)
        return result[:limit]

    @staticmethod
    def _process_keywords(raw_kw: Any) -> Dict[str, Any]:
        """Ensure keywords dict has the required shape."""
        if not isinstance(raw_kw, dict):
            return {"theme": "", "keywords": [], "phrases": []}
        return {
            "theme": str(raw_kw.get("theme", "")),
            "keywords": [str(k) for k in raw_kw.get("keywords", []) if k],
            "phrases": [str(p) for p in raw_kw.get("phrases", []) if p],
        }

    @staticmethod
    def _process_entities(raw_ent: Any, limit: int) -> Dict[str, List[str]]:
        """Ensure entities dict has all required type keys, each capped at limit."""
        if not isinstance(raw_ent, dict):
            return {t: [] for t in _ENTITY_TYPES}
        return {
            t: [str(e) for e in raw_ent.get(t, []) if e][:limit]
            for t in _ENTITY_TYPES
        }
