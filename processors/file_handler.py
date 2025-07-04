import os
from config import SUPPORTED_EXTENSIONS

class FileHandler:
    @staticmethod
    def validate_file(filename: str) -> bool:
        """Check if file extension is supported"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in SUPPORTED_EXTENSIONS
    
    @staticmethod
    def process_file(uploaded_file) -> bytes:
        """Convert uploaded file to bytes for Azure processing"""
        return uploaded_file.read()
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        return os.path.splitext(filename)[1].lower()