import os
from dotenv import load_dotenv

load_dotenv()

# Azure Document Intelligence
AZURE_DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT", "https://tetratech-doc-intelligence.cognitiveservices.azure.com/")
AZURE_DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOC_INTELLIGENCE_KEY", "CKHhGcDGXL1j0iyML5IEhnshRM6RTTHuKFa4bC5cTS86FBBSeySPJQQJ99BFACHYHv6XJ3w3AAALACOGW54W")

# Storage paths
TABLES_DIR = "extracted_content/tables"
IMAGES_DIR = "extracted_content/images"
TEXT_DIR = "extracted_content/text"

# Text processing
MAX_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Supported file types
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.xlsx']