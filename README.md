# ShareThis Predictive Multilabel Classification

A comprehensive multi-label text classification system using embeddings and IBM Watsonx AI, deployed on IBM Code Engine. This project provides tools for web scraping, data extraction, keyword analysis, and intelligent content categorization.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [API Endpoints](#api-endpoints)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Support](#support)

## 🎯 Overview

This project provides a complete pipeline for:
- **Web Content Extraction**: Scrape and extract content from URLs
- **Keyword & Entity Extraction**: Extract meaningful keywords and entities using IBM Watsonx AI
- **Multi-label Classification**: Classify content into multiple categories using advanced ML techniques
- **API Deployment**: Production-ready FastAPI service on IBM Code Engine

### Classification Approach

The system uses a hybrid approach combining:
1. **Sentence embeddings** (all-MiniLM-L6-v2) for semantic similarity
2. **Frequency bucketing** to prioritize common categories
3. **IBM Watsonx AI LLM** for final classification and validation

## ✨ Features

- 🚀 **Fast API**: High-performance FastAPI with async support
- 🤖 **IBM Watsonx AI Integration**: Leverage IBM's powerful LLM capabilities
- 📊 **Multi-label Classification**: Assign multiple relevant categories to content
- 🔍 **Web Scraping**: Extract content from URLs with intelligent parsing
- 🎯 **Keyword Extraction**: Automated keyword and entity extraction
- 📦 **Cloud Storage**: Support for IBM Cloud Object Storage (COS)
- 🐳 **Docker Ready**: Containerized deployment with Docker
- ☁️ **IBM Code Engine**: Seamless deployment to IBM's serverless platform
- 📈 **Scalable**: Auto-scaling based on demand
- 🔐 **Secure**: Environment-based credential management

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](./docs) folder:

### Core Documentation
- **[API Documentation](./docs/API_DOCUMENTATION.md)** - Complete API reference, endpoints, request/response formats, and usage examples
- **[IBM Credentials Setup](./docs/IBM_CREDENTIALS_SETUP.md)** - Step-by-step guide for setting up IBM Cloud credentials and services
- **[BYOM IBM Documentation](./docs/BYOM_IBM_DOCUMENTATION.md)** - Bring Your Own Model (BYOM) guide for IBM Watson
  - **Main IBM BYOM Link**: [IBM Watson BYOM Overview](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/ml-byom-overview.html)

### Additional Resources
- **[Web Scraper Guide](./docs/WEB_SCRAPER_README.md)** - Web scraping implementation and usage
- **[Crawler Documentation](./docs/CRAWLER_README.md)** - Web crawler setup and configuration

## 🏗️ Architecture

```
ShareThis-Predictive-Multilabel-Classification/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── Dockerfile              # Container configuration
│   ├── requirements.txt        # Python dependencies
│   └── src/
│       ├── embeddings.py       # Sentence embedding generation
│       ├── category_matcher.py # Cosine similarity with frequency bucketing
│       ├── classifier.py       # IBM Watsonx AI LLM classification
│       ├── pipeline.py         # End-to-end classification pipeline
│       ├── web_scraper.py      # Web content extraction
│       ├── extractors.py       # Keyword/entity extraction
│       └── cos_reader.py       # IBM COS integration
├── data/                       # Training data and results
├── Notebook/                   # Jupyter notebooks for analysis
└── docs/                       # Documentation files
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- IBM Cloud account with Watsonx AI access
- IBM Watsonx AI API key and Project ID

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/ShareThis-Predictive-Multilabel-Classification.git
cd ShareThis-Predictive-Multilabel-Classification

# Create virtual environment
python3.12 -m venv venv312
source venv312/bin/activate  # On Windows: venv312\Scripts\activate

# Install dependencies
cd app
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your credentials
```

### Run the API

```bash
python main.py
```

The API will be available at `http://localhost:8080`

## 🔌 API Endpoints

### Classification
- **`POST /classify`** - Classify text into multiple categories
- **`POST /classify/batch`** - Batch classify from an uploaded CSV file (`url` + `text` columns required; returns CSV with added `categories` column)

### URL Analysis
- **`POST /analyze`** - Comprehensive URL analysis: scrapes URL, classifies content, extracts keywords/phrases/concepts and named entities in a single call

### Categories
- **`GET /categories`** - Get all available categories

### Health & Status
- **`GET /health`** - Health check endpoint
- **`GET /`** - API information

**Classify Example:**
```bash
curl -X POST http://localhost:8080/classify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "text": "Your text content here...",
    "k": 55
  }'
```

**Classify Response:**
```json
{
  "url": "https://example.com",
  "categories": [
    "artificial-intelligence",
    "startups"
  ]
}
```

**Analyze Example:**
```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "k": 55,
    "max_keywords": 10
  }'
```

**Analyze Response:**
```json
{
  "url": "https://example.com",
  "status": "success",
  "categories": ["artificial-intelligence"],
  "keywords": {
    "theme": "AI and technology",
    "keywords": ["machine learning", "neural networks"],
    "phrases": ["deep learning models"],
    "concepts": ["artificial intelligence"]
  },
  "entities": {
    "PERSON": [], "ORGANIZATION": ["OpenAI"],
    "LOCATION": [], "DATE": [], "EVENT": [],
    "PRODUCT": ["ChatGPT"], "OTHER": []
  },
  "metadata": {
    "title": "Example Page",
    "description": "...",
    "domain": "example.com",
    "word_count": 450
  },
  "raw_text": "...",
  "cleaned_text": "..."
}
```

For detailed API documentation, see [API_DOCUMENTATION.md](./docs/API_DOCUMENTATION.md)

## 💻 Local Development

### System Requirements

**Important:** This project requires **Python 3.10 or higher** (Python 3.12 recommended)

- Python 3.9 only supports `ibm-watsonx-ai==0.0.5` (lacks `Credentials` class)
- Python 3.10+ supports `ibm-watsonx-ai>=1.1.11` (full feature support)

### Setup Options

#### Option 1: Using venv (Recommended)

```bash
# Verify Python version (must be 3.10+)
python3.12 --version

# Create virtual environment
python3.12 -m venv venv312

# Activate environment
source venv312/bin/activate  # Windows: venv312\Scripts\activate

# Navigate to app directory
cd app

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

# Navigate to app directory
cd app

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the `app/` directory (use `env.example` as template):

#### Required Variables
```bash
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_project_id
```

#### Data Source Configuration

**Option 1: Local File (Default)**
```bash
USE_COS=false
DATA_PATH=with_label.csv
```

**Option 2: IBM Cloud Object Storage**
```bash
USE_COS=true
COS_API_KEY=your_cos_api_key
COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud
COS_BUCKET=your_bucket_name
COS_OBJECT_KEY=with_label.csv
```

For detailed credential setup, see [IBM_CREDENTIALS_SETUP.md](./docs/IBM_CREDENTIALS_SETUP.md)

### Data Format

Training data (`with_label.csv`) structure:
- `url`: Web page URL
- `text`: Page content
- `label`: Category labels (e.g., `['/category/subcategory/item']`)

### Running the Application

```bash
# From the app directory
python main.py
```

API available at: `http://localhost:8080`

### Testing

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

# Comprehensive URL analysis (scrape + classify + keywords + entities)
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "k": 55,
    "max_keywords": 10
  }'

# Batch classify from CSV file
curl -X POST http://localhost:8080/classify/batch \
  -F "file=@your_data.csv" \
  -o classified_output.csv
```

## 🚢 Deployment

### Deploy to IBM Code Engine

This project is designed for seamless deployment to IBM Code Engine, IBM's serverless container platform.

#### Prerequisites

- IBM Cloud account
- GitHub repository with this code
- IBM Watsonx AI credentials (API Key and Project ID)
- (Optional) IBM Cloud Object Storage for data

#### Deployment Methods

1. **UI-Based Deployment** - Deploy using IBM Cloud Console (recommended for beginners)
2. **CLI-Based Deployment** - Deploy using IBM Cloud CLI (recommended for automation)
3. **Docker Deployment** - Deploy using Docker containers

#### Quick Deploy Steps

### Step 1: Access IBM Code Engine

1. Log in to [IBM Cloud Console](https://cloud.ibm.com)
2. Navigate to **Code Engine** from the hamburger menu (☰)
3. Click **"Start creating"** or select an existing project

### Step 2: Create a Code Engine Project

1. Click **"Create project"**
2. **Project name:** `text-classification-project` (or your preferred name)
3. **Resource group:** Select your resource group
4. **Location:** Choose a region (e.g., Dallas, London, Frankfurt)
5. Click **"Create"**
6. Wait for the project to be created (~30 seconds)

### Step 3: Create Application from GitHub

1. Inside your project, click **"Create"** → **"Application"**
2. **Application name:** `text-classification-api`

### Step 4: Configure Source Code

1. **Choose your source:**
   - Select **"Source code"**
   - Click **"Specify build details"**

2. **Code repository:**
   - **Code repo URL:** `https://github.com/YOUR-USERNAME/YOUR-REPO-NAME`
   - **Code repo access:** 
     - For **public repos:** Select "None"
     - For **private repos:** Click "Create" to add GitHub token
   - **Branch name:** `main` (or your default branch)
   - **Revision:** Leave empty (uses latest commit)

3. **Build configuration:**
   - **Strategy:** Select **"Dockerfile"** (IMPORTANT!)
   - **Dockerfile:** `Dockerfile` (default location at root)
   - **Build context directory:** `.` (root directory)
   - **Build timeout:** `1800` seconds (35 minutes)
   - **Build resources:** Select "Large" if available

### Step 5: Configure Runtime Settings

1. **Container settings:**
   - **Listening port:** `8080`
   - **Image pull policy:** Always

2. **Resources & scaling:**
   - **CPU:** `1` vCPU
   - **Memory:** `2` GB
   - **Ephemeral storage:** `0.4` GB (default)
   - **Min instances:** `1`
   - **Max instances:** `3`
   - **Concurrency:** `100` (default)

3. **Auto-scaling:**
   - **Requests per instance:** `10`
   - **Scale down delay:** `300` seconds

### Step 6: Add Environment Variables

Click **"Add environment variable"** and add the following:

#### Required Variables (Always needed):

| Name | Type | Value |
|------|------|-------|
| `WATSONX_API_KEY` | Literal | Your IBM Watsonx AI API key |
| `WATSONX_PROJECT_ID` | Literal | Your IBM Watsonx AI Project ID |

#### Option 1: Using Local File (Default)

| Name | Type | Value |
|------|------|-------|
| `USE_COS` | Literal | `false` |
| `DATA_PATH` | Literal | `with_label.csv` |

**Note:** When using local file, you need to ensure `with_label.csv` is in your GitHub repository.

#### Option 2: Using IBM Cloud Object Storage (Recommended for Production)

| Name | Type | Value |
|------|------|-------|
| `USE_COS` | Literal | `true` |
| `COS_API_KEY` | Literal | Your IBM COS API key |
| `COS_ENDPOINT` | Literal | Your COS endpoint URL (e.g., `https://s3.us-south.cloud-object-storage.appdomain.cloud`) |
| `COS_BUCKET` | Literal | Your COS bucket name |
| `COS_OBJECT_KEY` | Literal | `with_label.csv` (or your file name in COS) |


**For sensitive values (recommended):**
1. Click **"Reference to full secret"**
2. Create a new secret with your credentials
3. Reference the secret instead of literal values

### Step 7: Optional - Configure Domain & Security

1. **Domain mappings:** (Optional)
   - Add custom domain if needed
   - Configure TLS certificates

2. **Service bindings:** (Optional)
   - Bind to IBM Cloud Object Storage if using COS

### Step 8: Create Application

1. Review all settings
2. Click **"Create"** at the bottom
3. Wait for the build to complete (15-20 minutes)

### Step 9: Monitor Build Progress

1. You'll see the application status as **"Deploying"**
2. Click on the application name to see details
3. Go to **"Configuration"** → **"Code"** tab
4. Click on the build run to see logs
5. Monitor the build progress:
   - ✅ Cloning repository
   - ✅ Building Docker image
   - ✅ Pushing to registry
   - ✅ Deploying application

### Step 10: Access Your Application

1. Once status shows **"Ready"** (green checkmark)
2. Find the **Application URL** at the top (e.g., `https://text-classification-api.xxx.us-south.codeengine.appdomain.cloud`)
3. Click the URL or copy it

### Step 11: Test Your Deployment

```bash
# Health check
curl https://YOUR-APP-URL/health

# Get categories
curl https://YOUR-APP-URL/categories

# Classify text
curl -X POST https://YOUR-APP-URL/classify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "text": "Your text content here"
  }'

# Comprehensive URL analysis
curl -X POST https://YOUR-APP-URL/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "k": 55,
    "max_keywords": 10
  }'

# Batch classify from CSV
curl -X POST https://YOUR-APP-URL/classify/batch \
  -F "file=@your_data.csv" \
  -o classified_output.csv
```

## 📖 Additional Resources

### IBM Services
- [IBM Code Engine Documentation](https://cloud.ibm.com/docs/codeengine)
- [IBM Watsonx AI Documentation](https://cloud.ibm.com/docs/watsonx-ai)
- [IBM Cloud Object Storage](https://cloud.ibm.com/docs/cloud-object-storage)
- [IBM Watson BYOM](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/ml-byom-overview.html)

### Project Documentation
- [API Documentation](./docs/API_DOCUMENTATION.md)
- [IBM Credentials Setup](./docs/IBM_CREDENTIALS_SETUP.md)
- [BYOM IBM Guide](./docs/BYOM_IBM_DOCUMENTATION.md)
- [Web Scraper Guide](./docs/WEB_SCRAPER_README.md)
- [Crawler Documentation](./docs/CRAWLER_README.md)

### Notebooks
- `Notebook/EDA.ipynb` - Exploratory Data Analysis
- `Notebook/watsonx_keyword_entity_extraction.ipynb` - Keyword extraction examples
- `Notebook/url_analysis_demo.ipynb` - URL analysis demonstrations

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is part of the ShareThis Predictive Multilabel Classification system.

## 💬 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation in the `docs/` folder
- Review the troubleshooting guides

---

**Last Updated:** May 2026
**Version:** 1.0.0

