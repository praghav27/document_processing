import os
import pandas as pd
from typing import List, Dict
from storage.local_storage import LocalStorage
from .content_verbalizer import ContentVerbalizer
from llm_metadata.power_extractor import DocumentMetadataExtractor
from llm_metadata.rfi_extractor import RFIMetadataExtractor
from llm_metadata.document_type_detector import DocumentTypeDetector
import re
import uuid
from datetime import datetime

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class SimpleChunker:
    """Advanced text chunker with better section detection and debugging"""
    
    def __init__(self):
        self.section_patterns = {
            'section_heading': r'\[ParagraphRole\.SECTION_HEADING\]',
            'numbered_section': r'^\s*(\d+\.\d+)\s+([A-Z\s]+)',
            'cleanup_tags': r'\[None\]\s*|\[ParagraphRole\.[^\]]+\]'
        }
    
    @tracer.start_as_current_span("chunk_text_fn")
    def chunk_text(self, text: str, document_metadata: Dict = None) -> List[Dict]:
        """Create chunks from text with enhanced section detection and document metadata integration"""
        try:
            if not text or not isinstance(text, str):
                #print("⚠️ No valid text provided for chunking")
                log_custom_event(
                                logger,
                                "No valid text provided for chunking",
                                level="warning",
                                )
                return []
            
            chunks = []
            
            # Split by sections but keep the delimiter
            sections = self._split_by_sections_improved(text)
            
            for idx, section in enumerate(sections):
                if section and isinstance(section, str) and section.strip():
                    # Clean the section after splitting
                    cleaned_section = self._clean_text(section)
                    if cleaned_section and cleaned_section.strip():  # Check again after cleaning
                        chunk = self._create_chunk(cleaned_section, idx, document_metadata)
                        if chunk:  # Only add if chunk creation succeeded
                            chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            #print(f"❌ Error in chunk_text: {e}")
            return []
    
    @tracer.start_as_current_span("_split_by_sections_improved_fn")
    def _split_by_sections_improved(self, text: str) -> List[str]:
        """Improved section splitting that preserves content with error handling"""
        try:
            if not text or not isinstance(text, str):
                return []
            
            # Method 1: Try splitting with the section heading pattern
            sections = re.split(f'({self.section_patterns["section_heading"]})', text)
            
            # Remove empty sections and combine heading markers with following content
            combined_sections = []
            i = 0
            while i < len(sections):
                try:
                    section = sections[i].strip() if sections[i] else ""
                    if not section:
                        i += 1
                        continue
                        
                    # If this is a section heading marker, combine with next section
                    if re.match(self.section_patterns['section_heading'], section):
                        if i + 1 < len(sections):
                            next_section = sections[i + 1].strip() if sections[i + 1] else ""
                            combined_sections.append(section + '\n' + next_section)
                            i += 2
                        else:
                            combined_sections.append(section)
                            i += 1
                    else:
                        combined_sections.append(section)
                        i += 1
                except Exception as e:
                    #print(f"⚠️ Error processing section {i}: {e}")
                    i += 1
                    continue
            
            # If we didn't get good results, try alternative splitting
            if len(combined_sections) <= 1:
                # Fallback: split by double newlines or paragraph markers
                try:
                    fallback_sections = re.split(r'\n\s*\n|\[ParagraphRole\.[^\]]+\]', text)
                    combined_sections = [s.strip() for s in fallback_sections if s and s.strip()]
                except Exception as e:
                    #print(f"⚠️ Error in fallback splitting: {e}")
                    # Ultimate fallback: return original text as single section
                    combined_sections = [text.strip()] if text.strip() else []
            
            return combined_sections
            
        except Exception as e:
            #print(f"❌ Error in _split_by_sections_improved: {e}")
            return [text] if text else []
    
    @tracer.start_as_current_span("_clean_text_fn")
    def _clean_text(self, text: str) -> str:
        """Clean text but preserve important content with error handling"""
        try:
            if not text or not isinstance(text, str):
                return ""
            
            # Remove cleanup tags but be more careful
            cleaned = re.sub(self.section_patterns['cleanup_tags'], '', text)
            
            # Normalize whitespace but don't be too aggressive
            cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 newlines
            cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Normalize spaces
            
            return cleaned.strip()
            
        except Exception as e:
            #print(f"⚠️ Error cleaning text: {e}")
            return text if text else ""
    
    @tracer.start_as_current_span("_extract_section_info_fn")
    def _extract_section_info(self, content: str) -> Dict:
        """Extract section information with better fallbacks and error handling"""
        try:
            if not content or not isinstance(content, str):
                return {'section_no': 'unknown', 'section_name': 'EMPTY_SECTION'}
            
            # Try numbered section pattern first
            match = re.search(self.section_patterns['numbered_section'], content)
            if match:
                return {
                    'section_no': match.group(1),
                    'section_name': match.group(2).strip()
                }
            
            # Try to find other patterns
            lines = content.split('\n')
            first_meaningful_line = None
            
            for line in lines:
                if line and isinstance(line, str):
                    line = line.strip()
                    if line and not re.match(r'^\[.*\]$', line):  # Skip tag-only lines
                        first_meaningful_line = line
                        break
            
            if first_meaningful_line:
                # Check if it looks like a section header
                if (first_meaningful_line.isupper() or 
                    re.match(r'^\d+\.?\d*\s+[A-Z]', first_meaningful_line) or
                    len(first_meaningful_line) < 100):
                    return {
                        'section_no': 'auto',
                        'section_name': first_meaningful_line[:50]
                    }
            
            return {
                'section_no': 'unknown',
                'section_name': first_meaningful_line[:50] if first_meaningful_line else 'UNKNOWN_SECTION'
            }
            
        except Exception as e:
            #print(f"⚠️ Error extracting section info: {e}")
            return {'section_no': 'error', 'section_name': 'ERROR_SECTION'}
    
    @tracer.start_as_current_span("_create_chunk_fn")
    def _create_chunk(self, content: str, idx: int, document_metadata: Dict = None) -> Dict:
        """Create chunk with comprehensive metadata including LLM-extracted document metadata with error handling"""
        try:
            if not content or not isinstance(content, str):
                #print(f"⚠️ Invalid content for chunk {idx}")
                log_custom_event(
                                logger,
                                f"Invalid content for chunk {idx}",
                                level="warning",
                                )
                return None
            
            section_info = self._extract_section_info(content)
            
            # Use LLM-extracted metadata if available, otherwise use defaults
            if document_metadata and isinstance(document_metadata, dict):
                # Extract key fields from LLM metadata
                project_title = document_metadata.get('project_title', 'none')
                if project_title and project_title != 'Not Specified' and len(str(project_title)) > 50:
                    file_name = str(project_title)[:50]  # Truncate if too long
                else:
                    file_name = str(project_title) if project_title and project_title != 'Not Specified' else 'none'
                    
                domain = document_metadata.get('domain_category', 'none')
                if domain == 'Not Specified' or domain == 'Other':
                    domain = 'none'
                    
                # For RFI, use client_name as author; for RFP, use vendor_name
                if 'vendor_name' in document_metadata:
                    # RFP document
                    vendor_name = document_metadata.get('vendor_name', 'tetratech')
                    if vendor_name == 'Not Specified':
                        vendor_name = 'tetratech'
                    author = str(vendor_name)
                else:
                    # RFI document
                    author = document_metadata.get('client_name', 'tetratech')
                    if author == 'Not Specified':
                        author = 'tetratech'
                    author = str(author)
            else:
                file_name = 'none'
                domain = 'none'
                author = 'tetratech'
            
            chunk = {
                'chunk_id': str(uuid.uuid4())[:8],
                'file_name': file_name,
                'section_name': str(section_info.get('section_name', 'unknown')),
                'section_no': str(section_info.get('section_no', 'unknown')),
                'domain': str(domain),
                'content_type': 'text',
                'author': author,
                'content': content,
                'verbalized_content': content,  # Same as content for text chunks
                'metadata': {
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'chunk_index': idx,
                    'word_count': len(content.split()) if content else 0,
                    'char_count': len(content) if content else 0,
                    # Store all LLM-extracted metadata for reference
                    'llm_extracted_metadata': document_metadata if document_metadata else {}
                }
            }
            return chunk
            
        except Exception as e:
            #print(f"❌ Error creating chunk {idx}: {e}")
            return None


class ContentExtractor:
    """Extract and process content from Azure Document Intelligence results with document type detection"""
    
    def __init__(self):
        self.storage = LocalStorage()
        self.text_elements = []  # Store for section association
        self.verbalizer = ContentVerbalizer()
        self.text_chunks = []  # Store text chunks for section mapping
        self.document_metadata = {}  # Store LLM-extracted document metadata
        self.document_type_detector = DocumentTypeDetector()  # Document type detector
        self.metadata_extractor = None  # Will be set based on document type
        self.document_type = 'RFP'  # Default
    
    @tracer.start_as_current_span("extract_all_content_fn")
    def extract_all_content(self, result, filename: str, client=None, operation_id=None) -> Dict:
        """Extract text, tables, and images with automatic document type detection - Complete Fixed version"""
        try:
            base_filename = os.path.splitext(filename)[0] if filename else 'unknown'
            
            #print(f"🔍 Extracting content from {filename}...")
            log_custom_event(
                 logger,
                 f"Extracting content from {filename}...",
                 level="info",
                )
            
            # Step 1: Extract text elements
            #print(f"📋 Step 1: Extracting text elements...")
            self.text_elements = self._extract_text(result)
            #print(f"📋 Text elements extracted: {len(self.text_elements)}")
            
            # Step 2: Detect document type (RFP vs RFI) with error handling
            #print(f"🤖 Step 2: Detecting document type (RFP vs RFI)...")
            try:
                detection_result = self.document_type_detector.detect_document_type(self.text_elements)
                self.document_type = detection_result.get('document_type', 'RFP')
                self.document_type_detector.print_detection_summary(detection_result)
            except Exception as e:
                # print(f"⚠️ Error in document type detection: {e}")
                # print("🔄 Defaulting to RFP processing")
                self.document_type = 'RFP'
                detection_result = {'document_type': 'RFP', 'confidence': 0.5, 'reasoning': f'Error in detection: {e}'}
            
            # Step 3: Initialize appropriate metadata extractor based on document type
            #print(f"🎯 Step 3: Initializing {self.document_type} metadata extractor...")
            try:
                if self.document_type == 'RFI':
                    self.metadata_extractor = RFIMetadataExtractor()
                    #print("✅ RFI metadata extractor initialized")
                else:
                    self.metadata_extractor = DocumentMetadataExtractor()
                    #print("✅ RFP metadata extractor initialized")
            except Exception as e:
                # print(f"⚠️ Error initializing metadata extractor: {e}")
                # print("🔄 Falling back to RFP extractor")
                self.metadata_extractor = DocumentMetadataExtractor()
                self.document_type = 'RFP'
            
            # Step 4: Extract document metadata using appropriate extractor
            #print(f"🤖 Step 4: Extracting {self.document_type} metadata using LLM...")
            try:
                self.document_metadata = self.metadata_extractor.extract_metadata(self.text_elements)
                #print(f"📋 {self.document_type} metadata extracted: {len(self.document_metadata)} fields")
            except Exception as e:
                #print(f"⚠️ Error extracting metadata: {e}")
                self.document_metadata = self._get_default_metadata()
            
            # Step 5: Create text chunks with LLM metadata
            #print(f"📋 Step 5: Creating text chunks with {self.document_type} metadata...")
            try:
                self.text_chunks = self._create_text_chunks_with_simple_chunker()
                #print(f"📋 Text chunks created: {len(self.text_chunks)}")
            except Exception as e:
                #print(f"⚠️ Error creating text chunks: {e}")
                self.text_chunks = []
            
            # Step 6: Extract tables with section association
            #print(f"📋 Step 6: Extracting tables with section association...")
            try:
                tables = self._extract_tables(result, base_filename)
                #print(f"📋 Tables extracted: {len(tables)}")
            except Exception as e:
                #print(f"⚠️ Error extracting tables: {e}")
                tables = []
            
            # Step 7: Extract figures with section association
            #print(f"📋 Step 7: Extracting figures with section association...")
            try:
                figures = self._extract_figures(result, base_filename, client, operation_id)
                #print(f"📋 Figures extracted: {len(figures)}")
            except Exception as e:
                #print(f"⚠️ Error extracting figures: {e}")
                figures = []
            
            # Create table chunks with verbalization, section mapping, and LLM metadata
            #print(f"🤖 Creating table chunks with verbalization and {self.document_type} metadata...")
            try:
                table_chunks = self._create_table_chunks(tables, base_filename)
            except Exception as e:
                #print(f"⚠️ Error creating table chunks: {e}")
                table_chunks = []
            
            # Create image chunks with verbalization, section mapping, and LLM metadata
            #print(f"🤖 Creating image chunks with verbalization and {self.document_type} metadata...")
            try:
                image_chunks = self._create_image_chunks(figures, base_filename)
            except Exception as e:
                #print(f"⚠️ Error creating image chunks: {e}")
                image_chunks = []
            
            # Combine all chunks
            all_chunks = self.text_chunks + table_chunks + image_chunks
            
            # Create all text content for raw text storage
            try:
                all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem.get('content', '')}" for elem in self.text_elements if elem and elem.get('content')])
            except Exception as e:
                #print(f"⚠️ Error creating combined text: {e}")
                all_text = ""
            
            # Save text content to local storage
            try:
                if all_text.strip():
                    self.storage.save_raw_text(all_text, base_filename)
            except Exception as e:
                #print(f"⚠️ Error saving raw text: {e}")
                print()
            
            # Save enhanced text chunks to local storage (now includes document type-specific metadata)
            try:
                if all_chunks:
                    self.storage.save_text_chunks(all_chunks, base_filename)
            except Exception as e:
                #print(f"⚠️ Error saving text chunks: {e}")
                print()
            
            # Save document metadata separately
            try:
                if self.document_metadata:
                    self.storage.save_document_metadata(self.document_metadata, base_filename)
            except Exception as e:
                #print(f"⚠️ Error saving document metadata: {e}")
                print()
            
            #print(f"✅ Content extraction complete!")
            log_custom_event(
                            logger,
                            f"Content extraction complete!",
                            level="info",
                            )
            
            return {
                "text": all_text,
                "text_chunks": all_chunks,
                "tables": tables,
                "images": figures,
                "raw_text": all_text,
                "document_metadata": self.document_metadata,
                "document_type": self.document_type,  # Include detected document type
                "document_type_detection": detection_result,  # Include detection details
                "stats": {
                    "text_count": len(self.text_chunks),
                    "table_count": len(table_chunks),
                    "image_count": len(image_chunks),
                    "total_chunks": len(all_chunks)
                }
            }
            
        except Exception as e:
            #print(f"❌ Error in extract_all_content: {e}")
            import traceback
            traceback.print_exc()
            
            # Return minimal response on error
            return {
                "text": "",
                "text_chunks": [],
                "tables": [],
                "images": [],
                "raw_text": "",
                "document_metadata": self._get_default_metadata(),
                "document_type": "RFP",
                "document_type_detection": {"document_type": "RFP", "confidence": 0.5, "reasoning": f"Error: {e}"},
                "stats": {
                    "text_count": 0,
                    "table_count": 0,
                    "image_count": 0,
                    "total_chunks": 0
                }
            }
    
    @tracer.start_as_current_span("_get_default_metadata_fn")
    def _get_default_metadata(self) -> Dict:
        """Get default metadata based on document type"""
        try:
            if self.document_type == 'RFI':
                return {
                    'document_id': 'Not Specified',
                    'client_name': 'Not Specified',
                    'domain_category': 'Not mentioned in RFI',
                    'service_category': 'Not mentioned in RFI',
                    'project_title': 'Not Specified',
                    'rfi_description': 'Not mentioned in RFI',
                    'submission_date': 'Not Specified',
                    'duration': 'Not mentioned in RFI'
                }
            else:
                return {
                    'project_title': 'Not Specified',
                    'client_name': 'Not Specified',
                    'vendor_name': 'tetratech',
                    'submission_date': 'Not Specified',
                    'domain_category': 'Not mentioned in RFP',
                    'service_category': 'Not mentioned in RFP',
                    'revenue_range': 'Not mentioned in RFP',
                    'region': 'Not mentioned in RFP',
                    'project_value': 'Not mentioned in RFP',
                    'compliance_standard': 'Not mentioned in RFP',
                    'equipments_used': 'Not mentioned in RFP'
                }
        except:
            # Ultimate fallback
            return {'error': 'Could not generate default metadata'}
    
    def _extract_text(self, result) -> List[Dict]:
        """Extract clean text content excluding tables and figures with error handling"""
        text_elements = []
        
        try:
            if not result:
                #print("⚠️ No result provided for text extraction")
                log_custom_event(
                                logger,
                                "No result provided for text extraction",
                                level="warning",
                                )
                return text_elements
            
            excluded_spans = self._get_excluded_spans(result)
            
            if hasattr(result, 'paragraphs') and result.paragraphs:
                for para_idx, paragraph in enumerate(result.paragraphs):
                    try:
                        if self._is_excluded_content(paragraph, excluded_spans):
                            continue
                        
                        content = self._safe_get_content(paragraph)
                        if content and content.strip():
                            # Get position info safely
                            position_info = self._get_position_info(paragraph)
                            
                            # Get page number safely
                            page_number = 1
                            try:
                                if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                                    page_number = getattr(paragraph.bounding_regions[0], 'page_number', 1)
                            except:
                                pass
                            
                            # Use safe role extraction
                            role = self._safe_get_role(paragraph)
                            
                            text_elements.append({
                                "content": content,
                                "role": role,
                                "page_number": page_number,
                                "paragraph_index": para_idx + 1,
                                "position": position_info
                            })
                    except Exception as e:
                        #print(f"⚠️ Error processing paragraph {para_idx}: {e}")
                        continue
            
        except Exception as e:
            #print(f"❌ Error in _extract_text: {e}")
            print()
        
        return text_elements
    
    def _find_footer_position(self, page_number: int) -> dict:
            """Find footer X,Y position on given page using role attribute"""
            for element in self.text_elements:
                if (element.get('page_number') == page_number and 
                    element.get('role') == 'pageFooter'):
                    footer_pos = element.get('position', {})
                    footer_x = footer_pos.get('x', 0)
                    footer_y = footer_pos.get('y', 0)
                    #print(f"Footer found on page {page_number} at position: ({footer_x}, {footer_y})")
                    return {"x": footer_x, "y": footer_y}
            return None

    def _safe_get_content(self, element):
        """Safely get content from element with null checks"""
        try:
            if not element:
                return ""
            if isinstance(element, dict):
                content = element.get('content', '')
                return str(content) if content is not None else ""
            elif hasattr(element, 'content'):
                content = getattr(element, 'content', '')
                return str(content) if content is not None else ""
            return ""
        except Exception as e:
            #print(f"⚠️ Error getting content: {e}")
            return ""

    def _safe_get_role(self, element):
        """Safely get role from element with null checks"""
        try:
            if not element:
                return "unknown"
            if isinstance(element, dict):
                role = element.get('role', 'unknown')
                return str(role) if role is not None else "unknown"
            elif hasattr(element, 'role'):
                role = getattr(element, 'role', 'unknown')
                return str(role) if role is not None else "unknown"
            return "unknown"
        except Exception as e:
            #print(f"⚠️ Error getting role: {e}")
            return "unknown"
    
    def _get_position_info(self, paragraph):
        """Extract position information from bounding regions with error handling"""
        try:
            if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                bounding_region = paragraph.bounding_regions[0]
                if hasattr(bounding_region, 'polygon') and bounding_region.polygon:
                    # Get the top-left point (usually first point in polygon)
                    polygon = bounding_region.polygon
                    if len(polygon) >= 2:
                        return {
                            "x": polygon[0],
                            "y": polygon[1],
                            "page": getattr(bounding_region, 'page_number', 1)
                        }
        except Exception as e:
            #print(f"⚠️ Error getting position info: {e}")
            print()
        
        return {"x": 0, "y": 0, "page": 1}
    
    def _create_text_chunks_with_simple_chunker(self) -> List[Dict]:
        """Create text chunks using the sophisticated SimpleChunker with document type-specific metadata"""
        try:
            if not self.text_elements:
                #print("⚠️ No text elements available for chunking")
                return []
            
            # Create all text content with role tags
            text_parts = []
            for elem in self.text_elements:
                if elem and isinstance(elem, dict) and elem.get('content'):
                    role = elem.get('role', 'unknown')
                    content = elem.get('content', '')
                    if content and isinstance(content, str):
                        text_parts.append(f"[{role}] {content}")
            
            if not text_parts:
                #print("⚠️ No valid text parts found for chunking")
                return []
            
            all_text = "\n\n".join(text_parts)
            
            # Advanced chunking with document type-specific metadata
            chunker = SimpleChunker()
            chunks = chunker.chunk_text(all_text, self.document_metadata)  # Pass document type-specific metadata
            
            return chunks if chunks else []
            
        except Exception as e:
            #print(f"❌ Error in _create_text_chunks_with_simple_chunker: {e}")
            return []
    
    def _find_closest_section(self, target_page: int, target_position: Dict) -> Dict:
        """Find the closest preceding section header on the same page with error handling"""
        try:
            section_roles = ['sectionHeading', 'subsectionHeading', 'title']
            
            # Filter text elements to same page and section roles
            page_sections = []
            for elem in self.text_elements:
                if (elem and isinstance(elem, dict) and 
                    elem.get('page_number') == target_page and 
                    elem.get('role') in section_roles):
                    page_sections.append(elem)
            
            if not page_sections:
                # No sections on this page, try previous pages
                for page in range(target_page - 1, 0, -1):
                    page_sections = []
                    for elem in self.text_elements:
                        if (elem and isinstance(elem, dict) and 
                            elem.get('page_number') == page and 
                            elem.get('role') in section_roles):
                            page_sections.append(elem)
                    
                    if page_sections:
                        # Get the last section from the previous page
                        closest_section = max(page_sections, key=lambda x: x.get('position', {}).get('y', 0))
                        break
                else:
                    # No sections found anywhere
                    return {
                        "section_role": "unknown",
                        "section_content": "No section header found",
                        "section_page": target_page,
                        "section_paragraph_index": None,
                        "distance_from_section": None
                    }
            else:
                # Find sections that come before the target position
                target_y = target_position.get('y', 0) if target_position else 0
                preceding_sections = [
                    elem for elem in page_sections 
                    if elem.get('position', {}).get('y', 0) < target_y
                ]
                
                if preceding_sections:
                    # Get the closest preceding section (highest y value)
                    closest_section = max(preceding_sections, key=lambda x: x.get('position', {}).get('y', 0))
                    distance = abs(target_y - closest_section.get('position', {}).get('y', 0))
                else:
                    # No preceding sections, get the first section on the page
                    closest_section = min(page_sections, key=lambda x: x.get('position', {}).get('y', 0))
                    distance = abs(target_y - closest_section.get('position', {}).get('y', 0))
            
            return {
                "section_role": closest_section.get('role', 'unknown'),
                "section_content": str(closest_section.get('content', ''))[:100],  # Truncate for display
                "section_page": closest_section.get('page_number', target_page),
                "section_paragraph_index": closest_section.get('paragraph_index'),
                "distance_from_section": distance if 'distance' in locals() else None
            }
            
        except Exception as e:
            #print(f"⚠️ Error finding closest section: {e}")
            return {
                "section_role": "error",
                "section_content": "Error finding section",
                "section_page": target_page,
                "section_paragraph_index": None,
                "distance_from_section": None
            }
    
    def _get_section_info_from_closest_text_chunk(self, target_page: int, target_position: Dict) -> Dict:
        """Get section_name and section_no from closest text chunk for table/image mapping"""
        try:
            section_info = self._find_closest_section(target_page, target_position)
        
            # Extract section name and number from the section content
            section_content = section_info.get('section_content', '')
            if section_content:
                # Try to extract section number and name from content
                match = re.match(r'^\s*(\d+\.\d+)\s+(.+)', section_content)
                if match:
                    return {
                        'section_name': match.group(2).strip(),
                        'section_no': match.group(1)
                    }
            
            return {
                'section_name': section_content[:50] if section_content else 'Unknown Section',
                'section_no': 'auto'
            }
            
        except Exception as e:
            #print(f"⚠️ Error getting section info: {e}")
            return {'section_name': 'Error Section', 'section_no': 'error'}
    
    def _extract_tables(self, result, base_filename: str) -> List[Dict]:
        """Extract and save tables using Azure Document Intelligence with section association"""
        tables = []
        
        try:
            if not result or not hasattr(result, 'tables') or not result.tables:
                return tables
            
            for table_idx, table in enumerate(result.tables):
                try:
                    df = self._table_to_dataframe(table)
                    if not df.empty:
                        csv_path = self.storage.save_table(df, base_filename, table_idx + 1)
                        
                        # Get table position and find closest section
                        table_page = 1
                        try:
                            if hasattr(table, 'bounding_regions') and table.bounding_regions:
                                table_page = getattr(table.bounding_regions[0], 'page_number', 1)
                        except:
                            pass
                        
                        table_position = self._get_table_position(table)
                        section_info = self._find_closest_section(table_page, table_position)
                        
                        tables.append({
                            "content": df.to_string(index=False),
                            "html": df.to_html(index=False, classes="table table-striped"),
                            "csv_path": csv_path,
                            "page_number": table_page,
                            "row_count": len(df),
                            "column_count": len(df.columns),
                            "table_index": table_idx + 1,
                            "section_info": section_info,
                            "position": table_position
                        })
                except Exception as e:
                    #print(f"⚠️ Error processing table {table_idx + 1}: {e}")
                    continue
                    
        except Exception as e:
            #print(f"❌ Error in _extract_tables: {e}")
            print()
        
        return tables
    
    def _get_table_position(self, table):
        """Get table position from bounding regions with error handling"""
        try:
            if hasattr(table, 'bounding_regions') and table.bounding_regions:
                bounding_region = table.bounding_regions[0]
                if hasattr(bounding_region, 'polygon') and bounding_region.polygon:
                    polygon = bounding_region.polygon
                    if len(polygon) >= 2:
                        return {
                            "x": polygon[0],
                            "y": polygon[1],
                            "page": getattr(bounding_region, 'page_number', 1)
                        }
        except Exception as e:
            #print(f"⚠️ Error getting table position: {e}")
            print()
        
        return {"x": 0, "y": 0, "page": 1}
    
    def _should_exclude_figure(self, figure_data: Dict) -> bool:
            """
            Simple logo detection based on content length and image dimensions and dist from footer logic
            Step 1: Check if content is TE TETRA TECH or Tt TETRA TECH
            Step 2: Check if image dimensions are very small
            Step 3 : Check if figure is too close to the footer 
            """
            
            content = figure_data.get('content', '')
            
            # width = figure_data.get('width', 0)
            # height = figure_data.get('height', 0)
            
            # Step 1
            logo_patterns = [
                'TE\nTETRA TECH',
                'Tt\nTETRA TECH', 
                'TE TETRA TECH',
                'Tt TETRA TECH',
                'TE'
            ]

            if content in logo_patterns:
                #print(f"🚫 Logo detected: '{content}'")
                return True
            
            # Step 2
            # width_threshold = 150  # pixels
            # height_threshold = 100  
            
            # if width > 0 and height > 0:  
            #     if width <= width_threshold and height <= height_threshold:
            #         return True
            
            # Step 3
            position = figure_data.get('position', {})
            figure_x = position.get('x', 0)
            figure_y = position.get('y', 0)
            page_number = figure_data.get('page_number', 1)
            
            footer_position = self._find_footer_position(page_number)
            if footer_position:  # Footer found on this page
                x_diff = abs(figure_x - footer_position['x'])
                y_diff = abs(figure_y - footer_position['y'])
                distance_from_footer = x_diff + y_diff  # Manhattan distance
                
                footer_threshold = 6.75  # pixels - adjust as needed
                if distance_from_footer <= footer_threshold:
                    #print(f"🚫 Logo detected by footer proximity: distance={distance_from_footer}")
                    return True
            else:
                #print(f"ℹ️ No footer found on page {page_number} - skipping footer check")
                print()


            return False

    def _extract_figures(self, result, base_filename: str, client=None, operation_id=None) -> List[Dict]:
        """Extract figures/images using Azure Document Intelligence with section association"""
        figures = []
        
        if hasattr(result, 'figures') and result.figures:
            for fig_idx, figure in enumerate(result.figures):
                try:
                    # Extract text content from figure
                    text_content = self._extract_figure_content(figure, result)
                    page_number = getattr(figure.bounding_regions[0], 'page_number', 1) if figure.bounding_regions else 1
                    
                    # Get figure position and find closest section
                    figure_position = self._get_figure_position(figure)
                    section_info = self._find_closest_section(page_number, figure_position)
                    
                    figure_data = {
                        "content": text_content or f"Figure from page {page_number}",
                        "page_number": page_number,
                        "figure_index": fig_idx + 1,
                        "type": "figure",
                        "image_path": None,
                        "image_base64": None,
                        "width": None,
                        "height": None,
                        "section_info": section_info,
                        "position": figure_position
                    }
                    position = figure_data.get('position', {})
                    figure_x = position.get('x', 0)
                    figure_y = position.get('y', 0)
                    page_number = figure_data.get('page_number', 1)

                    footer_position = self._find_footer_position(page_number)
                    if footer_position:
                        x_diff = abs(figure_x - footer_position['x'])
                        y_diff = abs(figure_y - footer_position['y'])
                        distance_from_footer = x_diff + y_diff
                    else:
                        distance_from_footer = "Footer not found"

                    # Print distances
                    # print(f"Figure {fig_idx + 1} (Page {page_number}):")
                    # print(f"   Position: ({figure_x}, {figure_y})")
                    # print(f"   Distance from Footer: {distance_from_footer}")

                    # Try to extract actual image using get_analyze_result_figure
                    if figure.id and client and operation_id:
                        try:
                            #print(f"Extracting image for figure {fig_idx + 1} with ID: {figure.id}")
                            
                            # Get the raw image bytes
                            image_response = client.get_analyze_result_figure(
                                model_id=result.model_id,
                                result_id=operation_id,
                                figure_id=figure.id
                            )
                            
                            # Convert iterator to bytes
                            image_bytes = b''.join(image_response)
                            
                            if image_bytes:
                                # Save the image
                                image_path = self.storage.save_figure_image_bytes(
                                    image_bytes, 
                                    base_filename, 
                                    fig_idx + 1
                                )
                                
                                if image_path:
                                    # Convert to base64 for display
                                    import base64
                                    img_base64 = base64.b64encode(image_bytes).decode()
                                    
                                    figure_data.update({
                                        "image_path": image_path,
                                        "image_base64": img_base64,
                                        "type": "figure_with_image"
                                    })
                                    
                                    # Get image dimensions
                                    try:
                                        from PIL import Image
                                        from io import BytesIO
                                        img = Image.open(BytesIO(image_bytes))
                                        figure_data.update({
                                            "width": img.width,
                                            "height": img.height
                                        })
                                        
                                    except Exception as e:
                                        #print(f"Error getting image dimensions: {e}")
                                        print()


                                    if self._should_exclude_figure(figure_data):
                                        #print(f"ℹ️ Excluding figure {fig_idx + 1} based on simple logo detection")
                                        continue 
                                #print(f"✅ Successfully extracted image for figure {fig_idx + 1}")
                            else:
                                #print(f"⚠️ No image data received for figure {fig_idx + 1}")
                                print()
                                
                        except Exception as e:
                            #print(f"❌ Error extracting image for figure {fig_idx + 1}: {e}")
                            # Continue with text-only figure
                            if self._should_exclude_figure(figure_data):
                                #print(f"ℹ️ Excluding figure {fig_idx + 1} based on logo detection")
                                continue
                    
                    else:
                        if not figure.id:
                            #print(f"ℹ️ Figure {fig_idx + 1} has no ID - text content only")
                            print()
                        if not client or not operation_id:
                            #print(f"ℹ️ Client or operation_id not provided - text content only")
                            print()
                    
                    # Save text content if available
                    if text_content and text_content.strip():
                        text_path = self.storage.save_figure_text(text_content, base_filename, fig_idx + 1)
                    
                    figures.append(figure_data)
                    
                except Exception as e:
                    #print(f"Error processing figure {fig_idx + 1}: {e}")
                    continue
        
        return figures
    
    def _get_figure_position(self, figure):
        """Get figure position from bounding regions with error handling"""
        try:
            if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
                bounding_region = figure.bounding_regions[0]
                if hasattr(bounding_region, 'polygon') and bounding_region.polygon:
                    polygon = bounding_region.polygon
                    if len(polygon) >= 2:
                        return {
                            "x": polygon[0],
                            "y": polygon[1],
                            "page": getattr(bounding_region, 'page_number', 1)
                        }
        except Exception as e:
            #print(f"⚠️ Error getting figure position: {e}")
            print()
        
        return {"x": 0, "y": 0, "page": 1}
    
    def _create_table_chunks(self, tables: List[Dict], base_filename: str) -> List[Dict]:
        """Create chunks for tables with verbalization, section mapping, and document type-specific metadata"""
        table_chunks = []
        
        try:
            for idx, table in enumerate(tables):
                try:
                    # Get section info from closest text chunk
                    section_mapping = self._get_section_info_from_closest_text_chunk(
                        table.get('page_number', 1), 
                        table.get('position', {})
                    )
                    
                    # Verbalize the table
                    try:
                        verbalized_content = self.verbalizer.verbalize_table(table)
                    except Exception as e:
                        #print(f"⚠️ Error verbalizing table {idx}: {e}")
                        verbalized_content = f"Table from page {table.get('page_number', 'unknown')}"
                    
                    # Use document type-specific metadata for chunk creation
                    file_name = 'unknown'
                    domain = 'none'
                    author = 'tetratech'
                    
                    if self.document_metadata and isinstance(self.document_metadata, dict):
                        project_title = self.document_metadata.get('project_title', base_filename)
                        if project_title and project_title != 'Not Specified':
                            file_name = str(project_title)[:50] if len(str(project_title)) > 50 else str(project_title)
                        else:
                            file_name = base_filename
                        
                        domain_cat = self.document_metadata.get('domain_category', 'none')
                        if domain_cat and domain_cat not in ['Not Specified', 'Other']:
                            domain = str(domain_cat)
                        
                        # Use appropriate author field based on document type
                        if self.document_type == 'RFI':
                            author_field = self.document_metadata.get('client_name', 'tetratech')
                        else:
                            author_field = self.document_metadata.get('vendor_name', 'tetratech')
                        
                        if author_field and author_field != 'Not Specified':
                            author = str(author_field)
                    
                    # Create table chunk with document type-specific metadata integration
                    chunk = {
                        'chunk_id': str(uuid.uuid4())[:8],
                        'file_name': file_name,
                        'section_name': str(section_mapping.get('section_name', 'unknown')),
                        'section_no': str(section_mapping.get('section_no', 'unknown')),
                        'domain': domain,
                        'content_type': 'table',
                        'author': author,
                        'content': table.get('content', ''),
                        'verbalized_content': verbalized_content,
                        'metadata': {
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'chunk_index': idx,
                            'word_count': len(verbalized_content.split()) if verbalized_content else 0,
                            'char_count': len(verbalized_content) if verbalized_content else 0,
                            'document_type': self.document_type,
                            'table_info': {
                                'page_number': table.get('page_number', 1),
                                'row_count': table.get('row_count', 0),
                                'column_count': table.get('column_count', 0),
                                'csv_path': table.get('csv_path', ''),
                                'section_info': table.get('section_info', {})
                            },
                            'llm_extracted_metadata': self.document_metadata
                        }
                    }
                    
                    table_chunks.append(chunk)
                    
                except Exception as e:
                    #print(f"⚠️ Error creating table chunk {idx}: {e}")
                    continue
                    
        except Exception as e:
            #print(f"❌ Error in _create_table_chunks: {e}")
            print()
        
        return table_chunks
    
    def _create_image_chunks(self, figures: List[Dict], base_filename: str) -> List[Dict]:
        """Create chunks for images with verbalization, section mapping, and document type-specific metadata"""
        image_chunks = []
        
        try:
            for idx, figure in enumerate(figures):
                try:
                    # Get section info from closest text chunk
                    section_mapping = self._get_section_info_from_closest_text_chunk(
                        figure.get('page_number', 1), 
                        figure.get('position', {})
                    )
                    
                    # Verbalize the image
                    try:
                        verbalized_content = self.verbalizer.verbalize_image(figure)
                    except Exception as e:
                        #print(f"⚠️ Error verbalizing image {idx}: {e}")
                        verbalized_content = f"Image from page {figure.get('page_number', 'unknown')}"
                    
                    # Use document type-specific metadata for chunk creation
                    file_name = 'unknown'
                    domain = 'none'
                    author = 'tetratech'
                    
                    if self.document_metadata and isinstance(self.document_metadata, dict):
                        project_title = self.document_metadata.get('project_title', base_filename)
                        if project_title and project_title != 'Not Specified':
                            file_name = str(project_title)[:50] if len(str(project_title)) > 50 else str(project_title)
                        else:
                            file_name = base_filename
                        
                        domain_cat = self.document_metadata.get('domain_category', 'none')
                        if domain_cat and domain_cat not in ['Not Specified', 'Other']:
                            domain = str(domain_cat)
                        
                        # Use appropriate author field based on document type
                        if self.document_type == 'RFI':
                            author_field = self.document_metadata.get('client_name', 'tetratech')
                        else:
                            author_field = self.document_metadata.get('vendor_name', 'tetratech')
                        
                        if author_field and author_field != 'Not Specified':
                            author = str(author_field)
                    
                    # Create image chunk with document type-specific metadata integration
                    chunk = {
                        'chunk_id': str(uuid.uuid4())[:8],
                        'file_name': file_name,
                        'section_name': str(section_mapping.get('section_name', 'unknown')),
                        'section_no': str(section_mapping.get('section_no', 'unknown')),
                        'domain': domain,
                        'content_type': 'image',
                        'author': author,
                        'content': figure.get('content', ''),
                        'verbalized_content': verbalized_content,
                        'metadata': {
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'chunk_index': idx,
                            'word_count': len(verbalized_content.split()) if verbalized_content else 0,
                            'char_count': len(verbalized_content) if verbalized_content else 0,
                            'document_type': self.document_type,
                            'image_info': {
                                'page_number': figure.get('page_number', 1),
                                'image_type': figure.get('type', 'figure'),
                                'image_path': figure.get('image_path', ''),
                                'width': figure.get('width'),
                                'height': figure.get('height'),
                                'section_info': figure.get('section_info', {})
                            },
                            'llm_extracted_metadata': self.document_metadata
                        }
                    }
                    
                    image_chunks.append(chunk)
                    
                except Exception as e:
                    #print(f"⚠️ Error creating image chunk {idx}: {e}")
                    continue
                    
        except Exception as e:
            #print(f"❌ Error in _create_image_chunks: {e}")
            print()
        
        return image_chunks
    
    def _table_to_dataframe(self, table) -> pd.DataFrame:
        """Convert Azure table to pandas DataFrame with error handling"""
        try:
            if not table:
                return pd.DataFrame()
            
            row_count = getattr(table, 'row_count', 0)
            column_count = getattr(table, 'column_count', 0)
            
            if row_count == 0 or column_count == 0:
                return pd.DataFrame()
            
            # Create empty grid
            grid = [["" for _ in range(column_count)] for _ in range(row_count)]
            
            # Fill grid with cell data
            if hasattr(table, 'cells') and table.cells:
                for cell in table.cells:
                    try:
                        row_idx = getattr(cell, 'row_index', 0)
                        col_idx = getattr(cell, 'column_index', 0)
                        content = getattr(cell, 'content', '') or ""
                        
                        if 0 <= row_idx < row_count and 0 <= col_idx < column_count:
                            grid[row_idx][col_idx] = str(content)
                    except Exception as e:
                        #print(f"⚠️ Error processing table cell: {e}")
                        continue
            
            # Create DataFrame
            if row_count > 1 and any(grid[0]):
                # First row as headers
                df = pd.DataFrame(grid[1:], columns=grid[0])
            else:
                # No headers
                df = pd.DataFrame(grid)
            
            # Clean up empty rows/columns
            df = df.dropna(how='all').loc[:, (df != '').any(axis=0)]
            return df
            
        except Exception as e:
            #print(f"❌ Error converting table to dataframe: {e}")
            return pd.DataFrame()
    
    def _extract_figure_content(self, figure, result) -> str:
        """Extract text content from figure using spans with error handling"""
        try:
            if not figure or not result:
                return ""
            
            if hasattr(figure, 'spans') and figure.spans and hasattr(result, 'content'):
                content_parts = []
                for span in figure.spans:
                    try:
                        if hasattr(span, 'offset') and hasattr(span, 'length'):
                            span_content = result.content[span.offset:span.offset + span.length]
                            if span_content and isinstance(span_content, str) and span_content.strip():
                                content_parts.append(span_content.strip())
                    except Exception as e:
                        #print(f"⚠️ Error extracting span content: {e}")
                        continue
                return " ".join(content_parts)
                
        except Exception as e:
            #print(f"⚠️ Error extracting figure content: {e}")
            print()
        
        return ""
    
    def _get_excluded_spans(self, result) -> set:
        """Get character spans that belong to tables and figures with error handling"""
        excluded_spans = set()
        
        try:
            if not result:
                return excluded_spans
            
            # Exclude table spans
            if hasattr(result, 'tables') and result.tables:
                for table in result.tables:
                    try:
                        if hasattr(table, 'spans') and table.spans:
                            for span in table.spans:
                                try:
                                    if hasattr(span, 'offset') and hasattr(span, 'length'):
                                        for i in range(span.offset, span.offset + span.length):
                                            excluded_spans.add(i)
                                except Exception as e:
                                    #print(f"⚠️ Error processing table span: {e}")
                                    continue
                    except Exception as e:
                        #print(f"⚠️ Error processing table spans: {e}")
                        continue
            
            # Exclude figure spans
            if hasattr(result, 'figures') and result.figures:
                for figure in result.figures:
                    try:
                        if hasattr(figure, 'spans') and figure.spans:
                            for span in figure.spans:
                                try:
                                    if hasattr(span, 'offset') and hasattr(span, 'length'):
                                        for i in range(span.offset, span.offset + span.length):
                                            excluded_spans.add(i)
                                except Exception as e:
                                    #print(f"⚠️ Error processing figure span: {e}")
                                    continue
                    except Exception as e:
                        #print(f"⚠️ Error processing figure spans: {e}")
                        continue
                        
        except Exception as e:
            #print(f"❌ Error getting excluded spans: {e}")
            print()
        
        return excluded_spans
    
    def _is_excluded_content(self, paragraph, excluded_spans: set) -> bool:
        """Check if paragraph content overlaps with excluded spans with error handling"""
        try:
            if not paragraph or not excluded_spans:
                return False
            
            if hasattr(paragraph, 'spans') and paragraph.spans:
                for span in paragraph.spans:
                    try:
                        if hasattr(span, 'offset') and hasattr(span, 'length'):
                            span_range = set(range(span.offset, span.offset + span.length))
                            if span_range.intersection(excluded_spans):
                                return True
                    except Exception as e:
                        #print(f"⚠️ Error checking span exclusion: {e}")
                        continue
                        
        except Exception as e:
            #print(f"⚠️ Error checking excluded content: {e}")
            print()
        
        return False
    
    def get_processing_summary(self) -> Dict:
        """Get summary of processing results"""
        try:
            return {
                'document_type': self.document_type,
                'text_elements_count': len(self.text_elements),
                'text_chunks_count': len(self.text_chunks),
                'metadata_fields_count': len(self.document_metadata) if self.document_metadata else 0,
                'processing_status': 'completed' if self.document_metadata else 'partial'
            }
        except Exception as e:
            #print(f"⚠️ Error getting processing summary: {e}")
            return {
                'document_type': 'unknown',
                'text_elements_count': 0,
                'text_chunks_count': 0,
                'metadata_fields_count': 0,
                'processing_status': 'error'
            }
        