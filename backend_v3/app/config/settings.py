"""
Application Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "smart_parking"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_TITLE: str = "Smart Parking API V3"
    API_VERSION: str = "3.0.0"
    API_DESCRIPTION: str = "Professional Smart Parking Management System"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5500",
        "*"
    ]
    
    # Parking Configuration
    PARKING_CAPACITY: int = 100
    PARKING_ROWS: int = 10
    PARKING_COLS: int = 10
    
    # Fee Configuration (VND)
    FEE_PER_HOUR: int = 5000
    FEE_DAILY_PACKAGE: int = 50000
    FEE_MONTHLY_PACKAGE: int = 500000
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
