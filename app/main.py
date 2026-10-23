"""
FastAPI application — Analyze Text API.

Single endpoint: POST /analyze
Scrapes a URL, runs embedding-based candidate retrieval, calls WatsonX
with a single unified prompt, and returns categories, keywords, entities,
concepts, and metadata in one response.
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl, field_validator
from dotenv import load_dotenv

load_dotenv()

from src.config import settings
from src.pipeline import ClassificationPipeline
from src.watsonx_client import WatsonxRetryExhausted

# ── Logging ────────────────────────────────────────────────────────────── #
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Global pipeline instance ───────────────────────────────────────────── #
pipeline: Optional[ClassificationPipeline] = None


# ── Lifespan ───────────────────────────────────────────────────────────── #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the pipeline on startup; clean up on shutdown."""
    global pipeline
    logger.info("Starting up — initialising pipeline …")
    try:
        pipeline = ClassificationPipeline(
            watsonx_api_key=settings.watsonx_api_key,
            watsonx_project_id=settings.watsonx_project_id,
            watsonx_url=settings.watsonx_url,
            model_id=settings.watsonx_model_id,
            data_path=settings.data_path,
            max_retries=settings.watsonx_max_retries,
        )
        pipeline.prepare()
        logger.info("Pipeline ready.")
    except Exception:
        logger.exception("Pipeline initialisation failed — exiting.")
        raise

    yield

    logger.info("Shutting down.")
    pipeline = None


# ── App ────────────────────────────────────────────────────────────────── #
app = FastAPI(
    title="Analyze Text API",
    description=(
        "Content analysis API: scrapes a URL and returns categories, "
        "keywords, entities, concepts, and metadata in a single call."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ── Request models ─────────────────────────────────────────────────────── #
class FeatureConfig(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)


class FeaturesRequest(BaseModel):
    categories: FeatureConfig = Field(default_factory=lambda: FeatureConfig(limit=3))
    keywords: FeatureConfig = Field(default_factory=lambda: FeatureConfig(limit=20))
    entities: FeatureConfig = Field(default_factory=lambda: FeatureConfig(limit=10))
    concepts: FeatureConfig = Field(default_factory=lambda: FeatureConfig(limit=10))


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="URL of the page to analyze")
    version: Optional[str] = Field(default=None, description="API version string (informational)")
    return_analyzed_text: bool = Field(
        default=False,
        description="When true, includes cleaned page text in the response",
    )
    features: FeaturesRequest = Field(default_factory=FeaturesRequest)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v


# ── Response models ────────────────────────────────────────────────────── #
class CategoryItem(BaseModel):
    label: str
    score: float


class KeywordsResponse(BaseModel):
    theme: str
    keywords: List[str]
    phrases: List[str]


class EntitiesResponse(BaseModel):
    PERSON: List[str] = []
    ORGANIZATION: List[str] = []
    LOCATION: List[str] = []
    DATE: List[str] = []
    EVENT: List[str] = []
    PRODUCT: List[str] = []
    OTHER: List[str] = []


class MetadataResponse(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    word_count: Optional[int] = None


class AnalyzeResponse(BaseModel):
    url: str
    status: str
    categories: List[CategoryItem]
    keywords: KeywordsResponse
    entities: EntitiesResponse
    concepts: List[str]
    metadata: MetadataResponse
    analyzed_text: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────── #
@app.get("/", tags=["Health"])
async def root():
    return {"status": "healthy", "message": "Analyze Text API is running"}


@app.get("/health", tags=["Health"])
async def health():
    """Returns pipeline readiness alongside basic health status."""
    return {
        "status": "healthy",
        "ready": pipeline is not None and pipeline.is_ready,
        "model": settings.watsonx_model_id,
    }


@app.get("/categories", tags=["Info"])
async def get_categories():
    """Return the full list of unique categories known to the pipeline."""
    _require_pipeline()
    return {
        "categories": pipeline.unique_categories,
        "total": len(pipeline.unique_categories),
    }


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_url(request: AnalyzeRequest):
    """
    Comprehensive URL analysis.

    Scrapes the provided URL and returns:
    - **categories** — scored hierarchical labels
    - **keywords** — theme, single-word terms, and key phrases
    - **entities** — named entities by type
    - **concepts** — high-level themes and ideas
    - **metadata** — page title, description, domain, word count
    - **analyzed_text** — cleaned page text (only when `return_analyzed_text: true`)
    """
    _require_pipeline()

    features = request.features
    try:
        result = pipeline.analyze_url(
            url=request.url,
            categories_limit=features.categories.limit,
            keywords_limit=features.keywords.limit,
            entities_limit=features.entities.limit,
            concepts_limit=features.concepts.limit,
            return_analyzed_text=request.return_analyzed_text,
        )
    except WatsonxRetryExhausted as exc:
        logger.error("WatsonX retries exhausted for %s: %s", request.url, exc)
        raise HTTPException(
            status_code=503,
            detail="Model inference service unavailable. Please retry later.",
        )
    except Exception as exc:
        logger.exception("Unhandled error in /analyze for %s", request.url)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    if result["status"] != "success":
        # Map scrape error codes to appropriate HTTP status codes
        error_code = result.get("error_code", "UNKNOWN")
        http_status = _scrape_error_http_status(error_code)
        raise HTTPException(
            status_code=http_status,
            detail={
                "error": result.get("error", "Analysis failed."),
                "error_code": error_code,
            },
        )

    return AnalyzeResponse(
        url=result["url"],
        status=result["status"],
        categories=[CategoryItem(**c) for c in result["categories"]],
        keywords=KeywordsResponse(**result["keywords"]),
        entities=EntitiesResponse(**result["entities"]),
        concepts=result["concepts"],
        metadata=MetadataResponse(**result["metadata"]),
        analyzed_text=result.get("analyzed_text"),
        error=result.get("error"),
        error_code=result.get("error_code"),
    )


# ── Helpers ────────────────────────────────────────────────────────────── #

def _scrape_error_http_status(error_code: str) -> int:
    """Map a ScrapeErrorCode value to the most appropriate HTTP status code."""
    mapping = {
        "INVALID_URL":        422,  # Unprocessable Entity — bad input
        "DNS_FAILURE":        502,  # Bad Gateway — upstream unreachable
        "CONNECTION_REFUSED": 502,
        "TIMEOUT":            504,  # Gateway Timeout
        "HTTP_403":           403,  # Forbidden — pass through
        "HTTP_404":           404,  # Not Found — pass through
        "HTTP_429":           429,  # Too Many Requests — pass through
        "HTTP_5XX":           502,
        "HTTP_OTHER":         502,
        "NON_HTML_CONTENT":   422,
        "JAVASCRIPT_ONLY":    422,
        "EMPTY_CONTENT":      422,
        "ENCODING_ERROR":          502,
        "PARSE_ERROR":             502,
        "PLAYWRIGHT_UNAVAILABLE":  422,
    }
    return mapping.get(error_code, 500)


def _require_pipeline():
    if pipeline is None or not pipeline.is_ready:
        raise HTTPException(status_code=503, detail="Pipeline not ready")


# ── Entry point ────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
