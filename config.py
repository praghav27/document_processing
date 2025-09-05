import os
from dotenv import load_dotenv

load_dotenv()

# Azure Document Intelligence (existing)
AZURE_DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
AZURE_DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")

# Azure OpenAI for verbalization
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Azure OpenAI Embedding for semantic search (for future use)
AZURE_EMBEDDING_ENDPOINT = os.getenv("AZURE_EMBEDDING_ENDPOINT")
AZURE_EMBEDDING_API_KEY = os.getenv("AZURE_EMBEDDING_API_KEY")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_MODEL")

# Azure Blob Storage 
USE_BLOB_STORAGE = os.getenv("USE_BLOB_STORAGE", "False").lower() == "true"
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
INPUT_CONTAINER_NAME = "four-splitted-rfp-documents"
OUTPUT_CONTAINER_NAME = "extracted-rfp-data"

AZURE_AI_SEARCH_ENDPOINT=os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
AZURE_AI_SEARCH_RFI_INDEX_NAME= os.getenv("AZURE_AI_SEARCH_RFI_INDEX_NAME")
AZURE_AI_SEARCH_RFP_INDEX_NAME=os.getenv("AZURE_AI_SEARCH_RFP_INDEX_NAME")

# Storage paths
TABLES_DIR = "extracted_content/tables"
IMAGES_DIR = "extracted_content/images"
TEXT_DIR = "extracted_content/text"

#Hardcode logic
ENABLE_DOCUMENT_TYPE_DETECTION = os.getenv("ENABLE_DOCUMENT_TYPE_DETECTION", "True").lower() == "true"
DEFAULT_DOCUMENT_TYPE = os.getenv("DEFAULT_DOCUMENT_TYPE", "RFI")  # RFP or RFI

# Supported file types
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.xlsx']

# Text chunking configuration (DEPRECATED - now using role-based chunking)
MAX_CHUNK_SIZE = 2000  # Maximum characters per chunk
CHUNK_OVERLAP = 200    # Overlap between chunks

# Role-based chunking configuration
ROLE_HIERARCHY = {
    'section_roles': ['sectionHeading', 'title', 'subtitle'],
    'content_roles': ['paragraph', 'listItem', 'text', 'unknown'],
    'max_chunk_elements': 50,  # Maximum elements per chunk
    'min_chunk_length': 100    # Minimum characters for a valid chunk
}

# Application insights
APPLICATION_INSIGHTS_CONNECTION_STRING = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")