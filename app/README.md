# Text Classification API

Multi-label text classification API using embeddings and IBM Watsonx AI, deployed on IBM Code Engine.

## Overview

This API classifies web page text into multiple categories using:
1. **Sentence embeddings** (all-MiniLM-L6-v2) for semantic similarity
2. **Frequency bucketing** to prioritize common categories
3. **IBM Watsonx AI LLM** for final classification

## Architecture

```
app/src/
├── embeddings.py       # Embedding generation using SentenceTransformer
├── category_matcher.py # Cosine similarity with frequency bucketing
├── classifier.py       # IBM Watsonx AI LLM classification
└── pipeline.py         # End-to-end classification pipeline

main.py                 # FastAPI application
```

## API Endpoints

### `POST /classify`
Classify text into categories.

**Request:**
```json
{
  "url": "https://example.com",
  "text": "Your text content here...",
  "k": 55
}
```

**Response:**
```json
{
  "url": "https://example.com",
  "categories": ["category1", "category2"]
}
```

### `GET /categories`
Get all available categories.

### `GET /categories/batch`
Get all available categories.

### `GET /health`
Health check endpoint.

## Local Development

### Prerequisites

**Important:** This project requires **Python 3.10 or higher** (Python 3.12 recommended) due to `ibm-watsonx-ai` package requirements.

- Python 3.9 only supports `ibm-watsonx-ai==0.0.5` which lacks the `Credentials` class
- Python 3.10+ supports `ibm-watsonx-ai>=1.1.11` with full feature support

### Setup

#### Option 1: Using venv (Recommended)

```bash
# Verify Python version (must be 3.10+)
python3.12 --version

# Create virtual environment with Python 3.12
python3.12 -m venv venv312

# Activate the environment
source venv312/bin/activate  # On Windows: venv312\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

```

#### Option 2: Using conda

```bash
# Create conda environment with Python 3.12
conda create -n fastapi312 python=3.12

# Activate environment
conda activate fastapi312

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables
#### Required
- `WATSONX_API_KEY`: IBM Watsonx AI API key (required)
- `WATSONX_PROJECT_ID`: IBM Watsonx AI project ID (required)

#### Data Source Options

**Option 1: Local File (Default)**
- `USE_COS`: Set to `false` or leave empty (default)
- `DATA_PATH`: Path to training data CSV file (default: `with_label.csv`)

**Option 2: IBM Cloud Object Storage**
- `USE_COS`: Set to `true` to enable COS
- `COS_API_KEY`: IBM Cloud Object Storage API key
- `COS_ENDPOINT`: COS endpoint URL (e.g., `https://s3.direct.us-south.cloud-object-storage.appdomain.cloud`)
- `COS_BUCKET`: COS bucket name
- `COS_OBJECT_KEY`: Object key/path in bucket (default: `with_label.csv`)

See `env.example` for a complete configuration template.

## Data Format

The training data (`with_label.csv`) should have:
- `url`: Web page URL
- `text`: Page content
- `label`: List of category labels (e.g., `['/category/subcategory/item']`)

### Run Locally

```bash
python main.py
```

The API will be available at `http://localhost:8080`

### Test the API

```bash
# Health check
curl http://localhost:8080/health

# Get categories
curl http://localhost:8080/categories

# Classify text
curl -X POST http://localhost:8080/classify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "text": "Your text content here..."
  }'
```