"""Custom exceptions for better error handling"""
from fastapi import HTTPException
from typing import Any, Dict

class DocumentProcessingException(HTTPException):
    """Custom exception for document processing errors"""
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)

class FileValidationException(HTTPException):
    """Custom exception for file validation errors"""
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)

class FinancialDataException(HTTPException):
    """Custom exception for financial data errors"""
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)