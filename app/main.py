"""FastAPI application for text classification"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import pandas as pd
import io
from dotenv import load_dotenv
from src.pipeline import ClassificationPipeline

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Text Classification API",
    description="Multi-label text classification using embeddings and LLM",
    version="1.0.0"
)

# Global pipeline instance
pipeline = None


class ClassificationRequest(BaseModel):
    url: str
    text: str
    k: Optional[int] = 55


class ClassificationResponse(BaseModel):
    url: str
    categories: List[str]


class BatchClassificationResponse(BaseModel):
    total_processed: int
    results: List[ClassificationResponse]


@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup"""
    global pipeline
    
    # Get credentials from environment variables
    watsonx_api_key = os.getenv("WATSONX_API_KEY")
    watsonx_project_id = os.getenv("WATSONX_PROJECT_ID")
    data_path = os.getenv("DATA_PATH", "with_label.csv")
    
    # Get COS credentials (optional)
    use_cos = os.getenv("USE_COS", "false").lower() == "true"
    cos_api_key = os.getenv("COS_API_KEY")
    cos_endpoint = os.getenv("COS_ENDPOINT")
    cos_bucket = os.getenv("COS_BUCKET")
    cos_object_key = os.getenv("COS_OBJECT_KEY", "with_label.csv")
    
    if not watsonx_api_key or not watsonx_project_id:
        raise ValueError("WATSONX_API_KEY and WATSONX_PROJECT_ID must be set")
    
    # Validate COS credentials if COS is enabled
    if use_cos and not all([cos_api_key, cos_endpoint, cos_bucket]):
        raise ValueError(
            "When USE_COS=true, COS_API_KEY, COS_ENDPOINT, and COS_BUCKET must be set"
        )
    
    # Initialize and prepare pipeline
    pipeline = ClassificationPipeline(
        watsonx_api_key=watsonx_api_key,
        watsonx_project_id=watsonx_project_id,
        data_path=data_path,
        use_cos=use_cos,
        cos_api_key=cos_api_key,
        cos_endpoint=cos_endpoint,
        cos_bucket=cos_bucket,
        cos_object_key=cos_object_key
    )
    
    pipeline.load_and_prepare_data()
    pipeline.generate_embeddings()
    pipeline.create_frequency_buckets()
    pipeline.prepare_examples()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Text Classification API is running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/classify", response_model=ClassificationResponse)
async def classify_text(request: ClassificationRequest):
    """Classify text into categories"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        categories = pipeline.classify_text(
            url=request.url,
            text=request.text,
            k=request.k
        )
        
        return ClassificationResponse(
            url=request.url,
            categories=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@app.get("/categories")
async def get_categories():
    """Get all available categories"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    return {
        "categories": pipeline.unique_categories,
        "total": len(pipeline.unique_categories) if pipeline.unique_categories else 0
    }


@app.post("/classify/batch")
async def classify_batch(
    file: UploadFile = File(...),
    k: Optional[int] = 55
):
    """
    Batch classify texts from uploaded CSV file.
    
    Expected CSV format:
    - Must have 'url' and 'text' columns
    - Optional: any other columns will be preserved in output
    
    Returns a CSV file with original columns plus 'categories' column
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        # Read uploaded CSV file
        contents = await file.read()
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise HTTPException(
                status_code=400,
                detail="Unable to decode CSV file. Please ensure it's properly encoded."
            )
        
        # Validate required columns
        if 'url' not in df.columns or 'text' not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="CSV must contain 'url' and 'text' columns"
            )
        
        # Process each row
        results = []
        for idx, row in df.iterrows():
            try:
                categories = pipeline.classify_text(
                    url=str(row['url']),
                    text=str(row['text']),
                    k=k
                )
                results.append(categories)
            except Exception as e:
                # If classification fails for a row, append empty list
                results.append([])
                print(f"Error processing row {idx}: {str(e)}")
        
        # Add categories column to dataframe
        df['categories'] = results
        
        # Convert to CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        # Return as downloadable CSV file
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=classified_{file.filename}"
            }
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")
    except pd.errors.ParserError:
        raise HTTPException(status_code=400, detail="Invalid CSV file format")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch classification failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
