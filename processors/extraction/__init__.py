# from .content_orchestrator import ContentExtractor
# from .text_extractor import TextExtractor, SimpleChunker
# from .table_extractor import TableExtractor
# from .image_extractor import ImageExtractor
# from .section_mapper import SectionMapper

# __all__ = [
#     'ContentExtractor', 
#     'TextExtractor', 
#     'SimpleChunker',
#     'TableExtractor', 
#     'ImageExtractor', 
#     'SectionMapper'
# ]

from .text_extractor import TextExtractor, SimpleChunker
from .table_extractor import TableExtractor
from .image_extractor import ImageExtractor
from .section_mapper import SectionMapper
from .RFI_extractor import SimpleChunkerRFI,TextExtractorRFI
from .content_orchestrator import ContentExtractor as OriginalContentExtractor
from .enhanced_content_orchestrator import ContentExtractor as EnhancedContentExtractor

# Default to enhanced version for new features
ContentExtractor = EnhancedContentExtractor

__all__ = [
    'ContentExtractor',              # Enhanced version (default) - RFI/RFP detection
    'TextExtractor', 
    'SimpleChunker',
    'TableExtractor', 
    'ImageExtractor', 
    'SectionMapper',
    # Explicit versions for choice
    'OriginalContentExtractor',      # RFP-only with PowerExtractor
    'EnhancedContentExtractor'       # RFI/RFP detection with appropriate extractors
]