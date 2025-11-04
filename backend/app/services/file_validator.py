"""File validation service with comprehensive error handling"""
import os
from fastapi import UploadFile
from typing import Tuple
from app.core.exceptions import FileValidationException

class FileValidator:
    """Validates uploaded files for type, size, and content"""
    
    @staticmethod
    def validate_pdf_file(file: UploadFile, max_size: int) -> Tuple[bool, str]:
        """
        Validate PDF file for type, size, and basic integrity
        
        Args:
            file: Uploaded file object
            max_size: Maximum allowed file size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Raises:
            FileValidationException: If validation fails
        """
        try:
            # Validate file extension
            if not file.filename.lower().endswith('.pdf'):
                raise FileValidationException("Only PDF files are allowed")
            
            # Validate file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset position
            
            if file_size > max_size:
                raise FileValidationException(
                    f"File size ({file_size} bytes) exceeds maximum allowed size of {max_size} bytes"
                )
            
            if file_size < 100:  # Minimum reasonable PDF size
                raise FileValidationException("Uploaded file is too small or invalid")
                
            return True, "File validation successful"
            
        except Exception as e:
            raise FileValidationException(f"File validation failed: {str(e)}")