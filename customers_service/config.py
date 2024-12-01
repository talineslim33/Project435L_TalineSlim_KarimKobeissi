import os

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Talineslim0303$@postgres:5432/customers_service")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "d0eebc9d6b3f4d6b9817b5f6c0c4e7a4b6f8c3e1f6b4a8e5c1d2e3c0d4f1b5a9"
    JWT_ALGORITHM = "HS256"

