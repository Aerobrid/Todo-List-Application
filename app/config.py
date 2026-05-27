from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load local environment variables from .env file into python os.environ
load_dotenv()

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables or local files.
    Allows easy customization of CORS rules, database URLs, and API behaviors.
    """
    PROJECT_NAME: str = "Amplify Federal Todo API"
    DATABASE_URL: str = "sqlite:///./tasks.db"
    
    # CORS origins parameterization prevents unauthorized cross-site data harvesting.
    # Accepts string-based list configurations or JSON lists.
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # parse comma-separated lists if supplied in env variables
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
