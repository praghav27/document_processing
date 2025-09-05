import re
import uuid
from datetime import datetime
from typing import List, Dict


class SimpleChunker:
    """Advanced text chunker with better section detection and debugging"""
    
    def __init__(self):
        self.section_patterns = {
            'section_heading': r'\[ParagraphRole\.SECTION_HEADING\]',
            'numbered_section': r'^\s*(\d+\.\d+)\s+([A-Z\s]+)',
            'cleanup_tags': r'\[None\]\s*|\[ParagraphRole\.[^\]]+\]',
            'page_footer': r'\[ParagraphRole\.PAGE_FOOTER\]\s*([^\[]+)'
        }
    
    # def chunk_text(self, text: str, document_metadata: Dict = None, rfp_id: str = None) -> List[Dict]:
    def chunk_text(self, text: str, document_metadata: Dict = None, rfp_id: str = None, project_id: str = None) -> List[Dict]:
        """Create chunks from text with enhanced section detection and document metadata integration"""
        print(f"DEBUG: Input text length: {len(text)}")
        print(f"DEBUG: First 200 chars: {repr(text[:200])}")
        
        chunks = []
        
        # First, let's see what we're working with
        section_heading_matches = re.findall(self.section_patterns['section_heading'], text)
        print(f"DEBUG: Found {len(section_heading_matches)} section headings")
        
        # Split by sections but keep the delimiter
        sections = self._split_by_sections_improved(text)
        print(f"DEBUG: Split into {len(sections)} sections")
        
        for idx, section in enumerate(sections):
            print(f"DEBUG: Section {idx + 1} length: {len(section)}")
            print(f"DEBUG: Section {idx + 1} preview: {repr(section[:100])}")
            
            if section.strip():
                # Clean the section after splitting
                cleaned_section = self._clean_text(section)
                if cleaned_section.strip():  # Check again after cleaning
                    # chunk = self._create_chunk(cleaned_section, idx, document_metadata,rfp_id)
                    chunk = self._create_chunk(cleaned_section, idx, document_metadata, rfp_id, project_id)
                    chunks.append(chunk)
                    print(f"DEBUG: Created chunk {idx + 1} with {len(cleaned_section)} chars")
                else:
                    print(f"DEBUG: Section {idx + 1} became empty after cleaning")
            else:
                print(f"DEBUG: Section {idx + 1} was empty")
        
        print(f"DEBUG: Total chunks created: {len(chunks)}")
        return chunks
    
    def _split_by_sections_improved(self, text: str) -> List[str]:
        """Improved section splitting that preserves content"""
        # Method 1: Try splitting with the section heading pattern
        sections = re.split(f'({self.section_patterns["section_heading"]})', text)
        
        # Remove empty sections and combine heading markers with following content
        combined_sections = []
        i = 0
        while i < len(sections):
            section = sections[i].strip()
            if not section:
                i += 1
                continue
                
            # If this is a section heading marker, combine with next section
            if re.match(self.section_patterns['section_heading'], section):
                if i + 1 < len(sections):
                    next_section = sections[i + 1].strip()
                    combined_sections.append(section + '\n' + next_section)
                    i += 2
                else:
                    combined_sections.append(section)
                    i += 1
            else:
                combined_sections.append(section)
                i += 1
        
        # If we didn't get good results, try alternative splitting
        if len(combined_sections) <= 1:
            # Fallback: split by double newlines or paragraph markers
            fallback_sections = re.split(r'\n\s*\n|\[ParagraphRole\.[^\]]+\]', text)
            combined_sections = [s.strip() for s in fallback_sections if s.strip()]
        
        return combined_sections
    
    def _clean_text(self, text: str) -> str:
        """Clean text but preserve important content"""
        # Remove cleanup tags but be more careful
        cleaned = re.sub(self.section_patterns['cleanup_tags'], '', text)
        
        # Normalize whitespace but don't be too aggressive
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 newlines
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Normalize spaces
        
        return cleaned.strip()
    
    def _extract_section_info(self, content: str) -> Dict:
        """Extract section information with better fallbacks"""
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
    
    # def _create_chunk(self, content: str, idx: int, document_metadata: Dict = None,rfp_id:str=None) -> Dict:
    def _create_chunk(self, content: str, idx: int, document_metadata: Dict = None, rfp_id: str = None, project_id: str = None) -> Dict:
        """Create chunk with comprehensive metadata including LLM-extracted document metadata"""
        section_info = self._extract_section_info(content)
        
        # Use LLM-extracted metadata if available, otherwise use defaults
        if document_metadata:
            # Extract key fields from LLM metadata
            project_title = document_metadata.get('project_title', 'none')
            if project_title != 'Not Specified' and len(project_title) > 50:
                file_name = project_title[:50]  # Truncate if too long
            else:
                file_name = project_title if project_title != 'Not Specified' else 'none'
                
            domain = document_metadata.get('domain_category', 'none')
            if domain == 'Not Specified' or domain == 'Other':
                domain = 'none'
                
            vendor_name = document_metadata.get('vendor_name', 'tetratech')
            if vendor_name == 'Not Specified':
                vendor_name = 'tetratech'
        else:
            file_name = 'none'
            domain = 'none'
            vendor_name = 'tetratech'
        
        chunk = {
            'chunk_id': str(uuid.uuid4())[:8],
            'file_name': file_name,
            'project_id': project_id,
            'section_name': section_info['section_name'],
            'section_no': section_info['section_no'],
            'domain': domain,
            'content_type': 'text',
            'author': vendor_name,  # Now uses LLM-extracted vendor_name instead of 'tetratech'
            'content': content,
            'verbalized_content': '',
            'rfp_id':rfp_id,  #kept empty for now or we can keep it as same as content
            'metadata': {
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'chunk_index': idx,
                'word_count': len(content.split()),
                'char_count': len(content),
                # Store all LLM-extracted metadata for reference
                'llm_extracted_metadata': document_metadata if document_metadata else {}
            }
        }
        return chunk

    def print_chunks(self, chunks: List[Dict]):
        """Print chunks with detailed formatting including LLM-extracted metadata - FULL CONTENT"""
        print(f"\n{'='*80}")
        print(f"TEXT CHUNKING RESULTS WITH LLM METADATA - Total chunks: {len(chunks)}")
        print(f"{'='*80}")
        
        if not chunks:
            print("⚠️  NO CHUNKS WERE CREATED!")
            print("This might indicate issues with:")
            print("- Section splitting regex patterns")
            print("- Text cleaning removing too much content")
            print("- Input text format not matching expected patterns")
            return
        
        # Print LLM metadata summary first - NOW WITH 11 FIELDS
        if chunks and chunks[0].get('metadata', {}).get('llm_extracted_metadata'):
            llm_metadata = chunks[0]['metadata']['llm_extracted_metadata']
            print(f"\n🤖 LLM-EXTRACTED DOCUMENT METADATA:")
            print(f"   📝 Project Title: {llm_metadata.get('project_title', 'N/A')}")
            print(f"   🏢 Client Name: {llm_metadata.get('client_name', 'N/A')}")
            print(f"   🏭 Vendor Name: {llm_metadata.get('vendor_name', 'N/A')}")
            print(f"   📅 Submission Date: {llm_metadata.get('submission_date', 'N/A')}")
            print(f"   🏷️ Domain Category: {llm_metadata.get('domain_category', 'N/A')}")
            print(f"   ⚙️ Service Category: {llm_metadata.get('service_category', 'N/A')}")
            print(f"   💰 Revenue Range: {llm_metadata.get('revenue_range', 'N/A')}")
            print(f"   🌍 Region: {llm_metadata.get('region', 'N/A')}")
            print(f"   💵 Project Value: {llm_metadata.get('project_value', 'N/A')}")
            print(f"   📜 Compliance Standard: {llm_metadata.get('compliance_standard', 'N/A')}")  # NEW
            print(f"   🔧 Equipments Used: {llm_metadata.get('equipments_used', 'N/A')}")           # NEW
            print(f"{'='*80}")
    
    def debug_text_analysis(self, text: str):
        """Debug method to analyze the input text"""
        print(f"\n{'='*60}")
        print("TEXT ANALYSIS DEBUG")
        print(f"{'='*60}")
        print(f"Total text length: {len(text)} characters")
        print(f"Total lines: {len(text.split(chr(10)))}")
        
        # Check for section headings
        section_headings = re.findall(self.section_patterns['section_heading'], text)
        print(f"Section headings found: {len(section_headings)}")
        
        # Check for numbered sections
        numbered_sections = re.findall(self.section_patterns['numbered_section'], text, re.MULTILINE)
        print(f"Numbered sections found: {len(numbered_sections)}")
        
        # Show some examples
        print("\nFirst 500 characters:")
        print(repr(text[:500]))
        
        print("\nLast 500 characters:")
        print(repr(text[-500:]))
        
        if section_headings:
            print(f"\nSection heading examples: {section_headings[:3]}")
        
        if numbered_sections:
            print(f"\nNumbered section examples: {numbered_sections[:3]}")


class TextExtractor:
    """Handle text extraction and chunking logic"""
    
    def __init__(self):
        pass
    
    def extract_text(self, result) -> List[Dict]:
        """Extract clean text content excluding tables and figures"""
        text_elements = []
        excluded_spans = self._get_excluded_spans(result)
        #print("255: ", excluded_spans)

        if hasattr(result, 'paragraphs') and result.paragraphs:
            for para_idx, paragraph in enumerate(result.paragraphs):
                if self._is_excluded_content(paragraph, excluded_spans):
                    continue
                
                content = getattr(paragraph, 'content', '')
                #print("263: ", content)
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
                    #print("276: ", page_number)

                    text_elements.append({
                        "content": content,
                        "role": getattr(paragraph, "role", "unknown"),
                        "page_number": page_number,
                        "paragraph_index": para_idx + 1,
                        "position": position_info
                    })
        print(f"📋 Extracted {len(text_elements)} text elements from paragraphs")
        # print(text_elements)
        return text_elements
    
    def extract_rfp_id_from_text(self, text: str) -> str:
        """
        Extract RFP ID from page footer using regex.
        Returns the first matching footer content, or 'unknown_rfp' if not found.
        """
        # Use the same pattern as in SimpleChunker
        page_footer_pattern = r'\[ParagraphRole\.PAGE_FOOTER\]\s*([^\[]+)'
        matches = re.findall(page_footer_pattern, text)
        if matches:
            rfp_id = matches[0].strip()
            print(f"✅ Found RFP ID in footer using regex: '{rfp_id}'")
            return rfp_id
        print(f"⚠️ No RFP ID found in footer using regex - using default RFP ID")
        return 'unknown_rfp'

    # def create_text_chunks_with_simple_chunker(self, text_elements: List[Dict], document_metadata: Dict) -> List[Dict]:
    def create_text_chunks_with_simple_chunker_for_RFP(self, text_elements: List[Dict], document_metadata: Dict, project_id: str = None) -> List[Dict]:
        """Create text chunks using the sophisticated SimpleChunker with LLM metadata"""
        # Create all text content with role tags (like previous code)
        all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in text_elements])
        
        # Print original processed sections (like previous code)
        print("\n" + "="*60)
        print("ORIGINAL PROCESSED SECTIONS")
        print("="*60)
        section_text = all_text.split("[ParagraphRole.SECTION_HEADING]")
        processed_sections = []
        for section in section_text:
            section = section.replace("[None] ", "")
            section = section.replace("\n\n", "")
            processed_sections.append(section.strip())
        
        print("Printing processed sections:\n")
        for i, section in enumerate(processed_sections, 1):
            if section.strip():
                print(f"Section {i}: {section[:200]}...")
                print("-" * 40)
        
        # Advanced chunking with debugging and LLM metadata
        rfp_id = self.extract_rfp_id_from_text(all_text)
        chunker = SimpleChunker()
        # chunks = chunker.chunk_text(all_text, document_metadata, rfp_id=rfp_id)
        chunks = chunker.chunk_text(all_text, document_metadata, rfp_id=rfp_id, project_id=project_id)
        chunker.debug_text_analysis(all_text)
        chunker.print_chunks(chunks)
        return chunks
        
    def _get_position_info(self, paragraph):
        """Extract position information from bounding regions"""
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
        return {"x": 0, "y": 0, "page": 1}
    
    def _get_excluded_spans(self, result) -> set:
        """Get character spans that belong to tables and figures"""
        excluded_spans = set()
        
        # Exclude table spans
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                if hasattr(table, 'spans'):
                    for span in table.spans:
                        for i in range(span.offset, span.offset + span.length):
                            excluded_spans.add(i)
        
        # Exclude figure spans
        if hasattr(result, 'figures') and result.figures:
            for figure in result.figures:
                if hasattr(figure, 'spans'):
                    for span in figure.spans:
                        for i in range(span.offset, span.offset + span.length):
                            excluded_spans.add(i)
        
        return excluded_spans
    
    def _is_excluded_content(self, paragraph, excluded_spans: set) -> bool:
        """Check if paragraph content overlaps with excluded spans"""
        if hasattr(paragraph, 'spans') and paragraph.spans:
            for span in paragraph.spans:
                span_range = set(range(span.offset, span.offset + span.length))
                if span_range.intersection(excluded_spans):
                    return True
        return False