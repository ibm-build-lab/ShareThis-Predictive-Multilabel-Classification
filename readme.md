# Classification Notebook - README

## Overview
This notebook implements a multi-label classification system for categorizing web page content scraped from URLs. The system assigns third-level categories to web pages based on their text content using a hybrid approach combining semantic embeddings and large language model (LLM) generation.

## Purpose
The notebook processes the `with_label.csv` dataset from ShareThis Predictive, which contains:
- URLs of web pages
- Scraped text content from those pages
- Ground truth category labels (hierarchical, 3-level structure)

The goal is to automatically predict third-level categories for each webpage, where each page can have 1-7 categories (average: 2.5, mode: 2).

## Methodology

### 4-Step Process

#### 1. Data Preparation
- **Input**: `with_label.csv` from IBM Cloud Object Storage
- **Processing**:
  - Parse hierarchical labels (format: `/level1/level2/level3`)
  - Extract only third-level categories
  - Limit text to first 500 words per page
  - Replace underscores with spaces in category names
  - Remove duplicate categories per row
  - Filter out rows with no categories

#### 2. Embedding Generation
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Embeddings Created**:
  - All unique third-level categories
  - All scraped text content
- **Purpose**: Enable semantic similarity comparison between text and categories

#### 3. Category Narrowing (Top-K Selection)
- **Method**: Cosine similarity with frequency bucketing
- **Process**:
  1. Calculate cosine similarity between text embeddings and category embeddings
  2. Apply frequency-based bonus weights to adjust similarity scores
  3. Select top 55 most similar categories per text
  
- **Frequency Buckets**:
  - Very High (≥30 occurrences): +0.25 bonus
  - High (20-29 occurrences): +0.20 bonus
  - Medium (9-19 occurrences): +0.15 bonus
  - Low (4-8 occurrences): +0.05 bonus
  - None (<4 occurrences): +0.00 bonus

- **Performance Metrics** (Top-K Selection):
  - Micro Recall: **93.95%** (high recall ensures correct categories are in top 55)
  - Micro Precision: **3.46%** (intentionally low - casting wide net)
  - Macro Recall: **91.24%**
  - Macro Precision: **5.56%**

#### 4. Final Category Prediction
- **Model**: IBM watsonx.ai - `mistralai/mistral-small-3-1-24b-instruct-2503`
- **Parameters**:
  - Temperature: 0.1 (low for consistency)
  - Max tokens: 200
  - Decoding: Sample
  - Stop sequence: `]`

- **Prompt Engineering**:
  - Provides top 55 candidate categories
  - Includes 10 random training examples (few-shot learning)
  - Supplies URL and text content
  - Constrains output to 1-7 categories from candidate list

- **Post-Processing**:
  - Parse LLM output to extract category list
  - Validate categories against known category set
  - Clean and normalize category names

## Results

### Final Classification Performance
- **Subset Accuracy** (exact match): **28.00%**
- **Micro F1**: **62.22%**
- **Micro Precision**: **69.65%**
- **Micro Recall**: **56.23%**
- **Macro F1**: **60.87%**
- **Macro Precision**: **65.96%**
- **Macro Recall**: **62.95%**

### Key Insights
1. The two-stage approach (narrowing + generation) balances computational efficiency with accuracy
2. Frequency bucketing improves category selection by accounting for real-world distribution
3. Few-shot learning with 10 examples helps the LLM understand the task
4. The system achieves good precision (69.65%), indicating reliable predictions
5. Recall (56.23%) shows room for improvement in capturing all correct categories

## Dataset Information
- **Format**: CSV with columns: url, text, label
- **Training Examples**: 10 randomly selected samples (seed=42)
- **Test Set**: Remaining samples after removing training examples
- **Category Distribution**: Aligned with ShareThis's general data distribution

## Environment Setup

### Prerequisites
- Python 3.10 or higher
- pip package manager
- IBM Cloud account with Object Storage and watsonx.ai access

### Step 1: Create Virtual Environment

**Using venv (recommended):**
```bash
# Create virtual environment
python -m venv classification-env

# Activate virtual environment
# On macOS/Linux:
source classification-env/bin/activate
# On Windows:
classification-env\Scripts\activate
```

**Using conda:**
```bash
# Create conda environment
conda create -n classification-env python=3.10

# Activate environment
conda activate classification-env
```

### Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### Step 3: Set Up Jupyter Kernel

```bash
# Install the kernel for Jupyter
python -m ipykernel install --user --name=classification-env --display-name="Python (Classification)"
```

### Step 4: Configure Environment Variables (Optional)

Create a `.env` file in the project directory:
```bash
# IBM Cloud Object Storage
IBM_COS_API_KEY_ID=your_api_key_id
IBM_COS_BUCKET=your_bucket_name
IBM_COS_ENDPOINT=https://s3.direct.us-south.cloud-object-storage.appdomain.cloud

# IBM watsonx.ai
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### Step 5: Launch Jupyter Notebook

```bash
# Start Jupyter Notebook
jupyter notebook

# Or use Jupyter Lab
jupyter lab
```

Then open `classification.ipynb` and select the "Python (Classification)" kernel.

## Dependencies

See `requirements.txt` for complete list:

## Running the Notebook

### Before Running
1. **Update credentials** in the notebook cells:
   - Cell with IBM Cloud Object Storage setup: Replace `ADD YOUR API KEY ID` and `ADD YOUR BUCKET`
   - Cell with watsonx.ai setup: Replace `ADD YOUR API KEY` and `ADD YOUR PROJECT ID`

2. **Verify data file**: Ensure `with_label.csv` is uploaded to your IBM Cloud Object Storage bucket

3. **Check model access**: Confirm you have access to `mistralai/mistral-small-3-1-24b-instruct-2503` in watsonx.ai

### Execution Steps
1. Run cells sequentially from top to bottom
2. Wait for each cell to complete before proceeding
3. Monitor progress bars for embedding generation
4. LLM generation step may take several minutes depending on dataset size
