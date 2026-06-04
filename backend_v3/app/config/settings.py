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

    # MQTT
    MQTT_BROKER: str = "127.0.0.1"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_QOS: int = 1
    MQTT_TOPIC_RFID: str = "pbl5/smartparking/rfid_scanned"
    MQTT_TOPIC_GATE: str = "pbl5/smartparking/gate"
    MQTT_TOPIC_PARKING_STATUS: str = "pbl5/smartparking/parking_status"
    BACKEND_MQTT_CLIENT_ID: str = "SmartParkingBackendGate"
    
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

    # Camera/OCR gate decision policy
    OCR_ENTRY_POLICY: str = "required"
    OCR_EXIT_POLICY: str = "required"
    STRICT_OCR_BEFORE_GATE: bool = True
    ALLOW_ENTRY_ON_OCR_MISMATCH: bool = False
    ALLOW_EXIT_ON_OCR_FAILED: bool = False
    ALLOW_EXIT_ON_OCR_MISMATCH: bool = False
    ALLOW_EXIT_ON_OCR_FUZZY_MATCH: bool = True
    OCR_FUZZY_MAX_DISTANCE: int = 2
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
