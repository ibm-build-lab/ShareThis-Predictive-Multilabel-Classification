"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # WatsonX AI credentials
    watsonx_api_key: str = Field(..., env="WATSONX_API_KEY")
    watsonx_project_id: str = Field(..., env="WATSONX_PROJECT_ID")
    watsonx_url: str = Field(
        default="https://us-south.ml.cloud.ibm.com",
        env="WATSONX_URL"
    )

    # Model configuration
    watsonx_model_id: str = Field(
        default="mistralai/mistral-small-3-2-24b-instruct-2506",
        env="WATSONX_MODEL_ID"
    )
    watsonx_max_retries: int = Field(default=3, env="WATSONX_MAX_RETRIES")

    # Data source
    data_path: str = Field(default="with_label.csv", env="DATA_PATH")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Server
    port: int = Field(default=8080, env="PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
