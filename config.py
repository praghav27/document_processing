# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Azure Document Intelligence
# AZURE_DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT", "https://tetratech-doc-intelligence.cognitiveservices.azure.com/")
# AZURE_DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOC_INTELLIGENCE_KEY", "CKHhGcDGXL1j0iyML5IEhnshRM6RTTHuKFa4bC5cTS86FBBSeySPJQQJ99BFACHYHv6XJ3w3AAALACOGW54W")

# # Storage paths
# TABLES_DIR = "extracted_content/tables"
# IMAGES_DIR = "extracted_content/images"
# TEXT_DIR = "extracted_content/text"

# # Text processing
# MAX_CHUNK_SIZE = 1000
# CHUNK_OVERLAP = 200

# # Supported file types
# SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.xlsx']
import os
from dotenv import load_dotenv

load_dotenv()

# Azure Document Intelligence (existing)
AZURE_DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT", "https://tetratech-doc-intelligence.cognitiveservices.azure.com/")
AZURE_DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOC_INTELLIGENCE_KEY", "CKHhGcDGXL1j0iyML5IEhnshRM6RTTHuKFa4bC5cTS86FBBSeySPJQQJ99BFACHYHv6XJ3w3AAALACOGW54W")



# Storage paths (existing)
TABLES_DIR = "extracted_content/tables"
IMAGES_DIR = "extracted_content/images"
TEXT_DIR = "extracted_content/text"
CHUNKS_DIR = "extracted_content/chunks"  # NEW: Structure-aware chunks

# LLM Processing Configuration
LLM_CONFIG = {
    "temperature": 0.1,  # Low temperature for consistent structure analysis
    "max_tokens": 4000,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "timeout": 60git add .
}

# Chunking Configuration
CHUNKING_CONFIG = {
    # Target chunk sizes (in tokens)
    "min_chunk_size": 200,
    "target_chunk_size": 1000,
    "max_chunk_size": 1500,
    
    # Section-specific chunking
    "section_strategies": {
        "introduction": {"target_size": 800, "allow_split": False},
        "scope_of_work": {"target_size": 1200, "allow_split": True},
        "technical_requirements": {"target_size": 1000, "allow_split": True},
        "pricing": {"target_size": 800, "allow_split": True},
        "assumptions": {"target_size": 600, "allow_split": False},
        "exclusions": {"target_size": 600, "allow_split": False},
        "general": {"target_size": 1000, "allow_split": True}
    },
    
    # Overlap settings
    "semantic_overlap": 100,  # tokens
    "context_preservation": True
}

# Section Classification Configuration
SECTION_CLASSIFICATION = {
    "domain_categories": [
        "engineering", "environmental", "financial", "legal", 
        "technical", "administrative", "general"
    ],
    
    "service_categories": [
        "design", "construction_support", "consulting", 
        "maintenance", "analysis", "general"
    ],
    
    "content_types": [
        "text", "text_with_table", "text_with_image", 
        "text_with_multimodal", "table", "image"
    ]
}

# Text processing (existing + enhanced)
MAX_CHUNK_SIZE = CHUNKING_CONFIG["max_chunk_size"]
CHUNK_OVERLAP = CHUNKING_CONFIG["semantic_overlap"]
MIN_CHUNK_SIZE = CHUNKING_CONFIG["min_chunk_size"]

# Supported file types (existing)
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.xlsx']

# Document Structure Analysis
STRUCTURE_ANALYSIS_CONFIG = {
    "max_hierarchy_depth": 3,  # 1.0 -> 1.1 -> 1.1.1
    "section_title_patterns": [
        r'^\d+\.?\d*\.?\d*\.?\s+[A-Z][^:\n]*',  # 1., 1.1, 1.1.1
        r'^[A-Z][A-Z\s]{5,}$',  # ALL CAPS headings
        r'^[A-Z][^:\n]{10,80}$',  # Title case headings
        r'^\s*([A-Z][^:\n]*?):\s*$',  # Headings with colons
        r'^([IVX]+\.\s*[A-Z][^:\n]*?)$'  # Roman numerals
    ],
    "min_section_length": 100,  # Minimum characters for a valid section
    "content_analysis_window": 500  # Characters to analyze for section classification
}