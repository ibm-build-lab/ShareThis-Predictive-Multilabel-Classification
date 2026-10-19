# API Documentation

## Text Classification API

A comprehensive FastAPI application for multi-label text classification, keyword extraction, and named entity recognition using IBM WatsonX.ai.

---

## Table of Contents

1. [Overview](#overview)
2. [Endpoints](#endpoints)
3. [Request/Response Models](#requestresponse-models)
4. [Usage Examples](#usage-examples)
5. [Error Handling](#error-handling)

---

## Overview

This API provides three main functionalities:

1. **Text Classification**: Classify text into multiple categories
2. **Keyword Extraction**: Extract keywords, phrases, and concepts from text
3. **Named Entity Recognition**: Extract entities (PERSON, ORGANIZATION, LOCATION, etc.)

The API supports both single-item and batch processing.

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Get Available Categories

**GET** `/categories`

Retrieve all available classification categories.

**Response:**
```json
{
  "categories": ["category1", "category2", ...],
  "total": 150
}
```

---

### 3. Classify Text

**POST** `/classify`

Classify provided text into categories.

**Request Body:**
```json
{
  "url": "https://example.com",
  "text": "Your text content here...",
  "k": 55
}
```

**Parameters:**
- `url` (string, required): URL associated with the text
- `text` (string, required): Text content to classify
- `k` (integer, optional): Number of top categories to consider (default: 55)

**Response:**
```json
{
  "url": "https://example.com",
  "categories": ["category1", "category2", "category3"]
}
```

---

### 4. Batch Classify

**POST** `/classify/batch`

Classify multiple texts from a CSV file.

**Request:**
- Content-Type: `multipart/form-data`
- File: CSV file with `url` and `text` columns
- Query Parameter: `k` (optional, default: 55)

**CSV Format:**
```csv
url,text
https://example1.com,"Text content 1..."
https://example2.com,"Text content 2..."
```

**Response:**
- Content-Type: `text/csv`
- Returns CSV file with original columns plus `categories` column

---

### 5. Comprehensive URL Analysis (NEW)

**POST** `/analyze`

🎯 **Main Feature**: Comprehensive analysis of a URL including web scraping, classification, keyword extraction, and entity recognition.

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "k": 55,
  "max_keywords": 10
}
```

**Parameters:**
- `url` (string, required): URL to analyze
- `k` (integer, optional): Number of top categories to consider (default: 55)
- `max_keywords` (integer, optional): Maximum keywords to extract (default: 10)

**Response:**
```json
{
  "url": "https://example.com/article",
  "status": "success",
  "categories": [
    "technology",
    "artificial intelligence",
    "machine learning"
  ],
  "keywords": {
    "theme": "Artificial Intelligence and Machine Learning",
    "keywords": [
      "AI",
      "algorithm",
      "neural",
      "data"
    ],
    "phrases": [
      "machine learning",
      "deep learning",
      "natural language processing"
    ],
    "concepts": [
      "artificial intelligence",
      "data science",
      "automation"
    ]
  },
  "entities": {
    "PERSON": ["John Doe", "Jane Smith"],
    "ORGANIZATION": ["OpenAI", "Google", "Microsoft"],
    "LOCATION": ["San Francisco", "United States"],
    "DATE": ["2024", "January 2024"],
    "EVENT": ["AI Summit 2024"],
    "PRODUCT": ["ChatGPT", "TensorFlow"],
    "OTHER": []
  },
  "metadata": {
    "title": "The Future of AI",
    "description": "An article about artificial intelligence...",
    "domain": "example.com",
    "word_count": 1250
  },
  "raw_text": "The Future of AI Artificial intelligence is transforming...",
  "cleaned_text": "The Future of AI Artificial intelligence is transforming...",
  "error": null
}
```

**Process Flow:**

1. **Web Scraping**: Fetches and extracts clean text from the URL
2. **Classification**: Classifies content into relevant categories
3. **Keyword Extraction**: Extracts theme, keywords, phrases, and concepts
4. **Entity Recognition**: Identifies named entities across 7 categories
5. **Metadata Extraction**: Captures title, description, and other metadata

---

## Request/Response Models

### AnalyzeRequest

```python
{
  "url": str,              # Required: URL to analyze
  "k": int,                # Optional: Top-k categories (default: 55)
  "max_keywords": int      # Optional: Max keywords (default: 10)
}
```

### AnalyzeResponse

```python
{
  "url": str,              # Original URL
  "status": str,           # "success" or "error"
  "categories": List[str], # Predicted categories
  "keywords": {
    "theme": str,          # Main topic/theme
    "keywords": List[str], # Single-word keywords
    "phrases": List[str],  # Multi-word phrases
    "concepts": List[str]  # High-level concepts
  },
  "entities": {
    "PERSON": List[str],        # People names
    "ORGANIZATION": List[str],  # Companies, institutions
    "LOCATION": List[str],      # Places, countries, cities
    "DATE": List[str],          # Dates and time references
    "EVENT": List[str],         # Events, conferences
    "PRODUCT": List[str],       # Products, software, tools
    "OTHER": List[str]          # Other named entities
  },
  "metadata": {
    "title": str,          # Page title
    "description": str,    # Meta description
    "domain": str,         # Domain name
    "word_count": int      # Word count
  },
  "raw_text": str | null,      # Raw extracted text before cleaning
  "cleaned_text": str | null,  # Cleaned text used for analysis
  "error": str | null          # Error message if failed
}
```

---

## Usage Examples

### Example 1: Analyze a News Article

**Request:**
```bash
curl -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://techcrunch.com/2024/01/15/ai-breakthrough",
    "k": 55,
    "max_keywords": 10
  }'
```

**Response:**
```json
{
  "url": "https://techcrunch.com/2024/01/15/ai-breakthrough",
  "status": "success",
  "categories": ["technology", "artificial intelligence", "innovation"],
  "keywords": {
    "theme": "AI Technology Breakthrough",
    "keywords": ["AI", "breakthrough", "technology", "innovation"],
    "phrases": ["artificial intelligence", "machine learning", "tech industry"],
    "concepts": ["technological advancement", "AI research", "innovation"]
  },
  "entities": {
    "PERSON": ["Sam Altman", "Elon Musk"],
    "ORGANIZATION": ["OpenAI", "TechCrunch"],
    "LOCATION": ["Silicon Valley"],
    "DATE": ["January 2024"],
    "EVENT": ["AI Conference 2024"],
    "PRODUCT": ["GPT-4"],
    "OTHER": []
  },
  "metadata": {
    "title": "Major AI Breakthrough Announced",
    "description": "A groundbreaking development in AI technology...",
    "domain": "techcrunch.com",
    "word_count": 850
  },
  "error": null
}
```

### Example 2: Analyze a Blog Post

**Python Example:**
```python
import requests

url = "http://localhost:8080/analyze"
payload = {
    "url": "https://medium.com/@author/article-title",
    "k": 55,
    "max_keywords": 15
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Categories: {result['categories']}")
print(f"Theme: {result['keywords']['theme']}")
print(f"Keywords: {result['keywords']['keywords']}")
print(f"Entities: {result['entities']}")
```

### Example 3: Simple Text Classification

**Request:**
```bash
curl -X POST "http://localhost:8080/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "text": "This is an article about machine learning and artificial intelligence.",
    "k": 55
  }'
```

**Response:**
```json
{
  "url": "https://example.com",
  "categories": ["technology", "artificial intelligence", "machine learning"]
}
```

---

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid URL format"
}
```

#### 503 Service Unavailable
```json
{
  "detail": "Pipeline not initialized"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Analysis failed: [error details]"
}
```

### Error Scenarios for `/analyze` Endpoint

1. **Invalid URL**: Returns 400 with "Invalid URL format"
2. **Scraping Failed**: Returns 400 with "Failed to fetch URL"
3. **No Content**: Returns 400 with "No text content extracted from URL"
4. **Processing Error**: Returns 500 with detailed error message

---

## Performance Considerations

- **Web Scraping**: Timeout set to 30 seconds with 3 retry attempts
- **Text Processing**: Text is truncated to 500 words for classification
- **Concurrent Requests**: API supports concurrent requests
- **Rate Limiting**: Consider implementing rate limiting for production use

---

## Environment Variables

Required environment variables (see `env.example`):

```bash
# IBM WatsonX.ai Credentials
WATSONX_API_KEY=your_api_key
WATSONX_PROJECT_ID=your_project_id

# Data Configuration
DATA_PATH=with_label.csv
USE_COS=false

# Optional: IBM Cloud Object Storage
COS_API_KEY=your_cos_api_key
COS_ENDPOINT=your_cos_endpoint
COS_BUCKET=your_bucket_name
COS_OBJECT_KEY=with_label.csv
```

---

## Running the API

### Local Development

```bash
cd app
pip install -r requirements.txt
python main.py
```

### Docker

```bash
cd app
docker build -t text-classification-api .
docker run -p 8080:8080 --env-file .env text-classification-api
```

### Access API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

---

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌───────────────────────────────┐  │
│  │    /analyze Endpoint          │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   ClassificationPipeline      │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │   WebScraper            │  │  │
│  │  │   - Fetch HTML          │  │  │
│  │  │   - Extract Text        │  │  │
│  │  │   - Clean Content       │  │  │
│  │  └─────────────────────────┘  │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │   Classifier            │  │  │
│  │  │   - Generate Embeddings │  │  │
│  │  │   - Match Categories    │  │  │
│  │  │   - Predict Labels      │  │  │
│  │  └─────────────────────────┘  │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │   KeywordExtractor      │  │  │
│  │  │   - Extract Keywords    │  │  │
│  │  │   - Extract Phrases     │  │  │
│  │  │   - Extract Concepts    │  │  │
│  │  └─────────────────────────┘  │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │   EntityExtractor       │  │  │
│  │  │   - Extract Entities    │  │  │
│  │  │   - Categorize Types    │  │  │
│  │  └─────────────────────────┘  │  │
│  └─────────────────────────────┘  │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────┐
│  IBM WatsonX.ai │
│  Foundation     │
│  Models         │
└─────────────────┘
```

---

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify environment variables are set correctly
3. Ensure IBM WatsonX.ai credentials are valid
4. Review the API documentation at `/docs`

---

**Version**: 1.0.0  
**Last Updated**: 2026-04-24  
**Author**: Bob