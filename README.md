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

# Deploy to IBM Code Engine from GitHub Repository (UI Guide)

This guide walks you through deploying the Text Classification API to IBM Code Engine using the web console and connecting it to your GitHub repository.

## Prerequisites

- IBM Cloud account
- GitHub repository with this code
- IBM Watsonx AI credentials (API Key and Project ID)

## Step-by-Step Deployment Guide

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
```

## Support

- [IBM Code Engine Documentation](https://cloud.ibm.com/docs/codeengine)
- [IBM Watsonx AI Documentation](https://cloud.ibm.com/docs/watsonx-ai)

