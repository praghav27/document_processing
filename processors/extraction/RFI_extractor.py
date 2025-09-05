import re
import uuid
from datetime import datetime
from typing import List, Dict


class SimpleChunkerRFI:
    """Advanced text chunker with better section detection and debugging"""
    
    def __init__(self):
        self.section_patterns = {
            'section_heading': r'\[ParagraphRole\.SECTION_HEADING\]',
            'numbered_section': r'^\s*(\d+\.\d+)\s+([A-Z\s]+)',
            'cleanup_tags': r'\[None\]\s*|\[ParagraphRole\.[^\]]+\]',
            'page_footer': r'\[ParagraphRole\.PAGE_FOOTER\]\s*([^\[]+)'
        }
    
    def chunk_text_for_RFI(self, text: str, document_metadata: Dict = None, project_id: str = None) -> List[Dict]:
        """Create chunks from text with enhanced section detection and document metadata integration"""
        print(f"DEBUG: Input text length: {len(text)}")
        print(f"DEBUG: First 200 chars: {repr(text[:200])}")
        
        chunks = []
        chunk = self._create_chunk_for_RFI(document_metadata, project_id)
        chunks.append(chunk)
        print(f"DEBUG: Total chunks created: {len(chunks)}")
        return chunks
    

    def _create_chunk_for_RFI(self, document_metadata: Dict = None, project_id: str = None) -> Dict:
        """Create chunk with comprehensive metadata including LLM-extracted document metadata"""
        # section_info = self._extract_section_info(content)
        
        # Use LLM-extracted metadata if available, otherwise use defaults
        if document_metadata:
            # Extract key fields from LLM metadata
            project_name = document_metadata.get('project_name', 'none')
                
            client = document_metadata.get('client', 'hydro_one')
            if client == 'Not Specified' or client == 'Other':
                client = 'hydro_one'
                
            region = document_metadata.get('region', 'canada')
            if region == 'Not Specified':
                region = 'canada'
            industry = document_metadata.get('industry', 'none')
            if industry == 'Not Specified' or industry == 'Other':
                industry = 'none'
            prepared_date = document_metadata.get('prepared_date', 'none')
            if prepared_date == 'Not Specified' or prepared_date == 'Other':    
                prepared_date = 'none'
            station_discipline = document_metadata.get('station_discipline', 'none')
            if station_discipline == 'Not Specified' or station_discipline == 'Other':    
                station_discipline = 'none'
            scope_of_work = document_metadata.get('scope_of_work', 'none')
            if scope_of_work == 'Not Specified' or scope_of_work == 'Other':    
                scope_of_work = 'none'
            required_activities = document_metadata.get('required_activities', 'none')
            if required_activities == 'Not Specified' or required_activities == 'Other':    
                required_activities = 'none'
            
        else:
            file_name = 'none'
            domain = 'none'
            vendor_name = 'tetratech'
        
        chunk = {
            'chunk_id': str(uuid.uuid4())[:8],
            'project_id': project_id,
            "project_name":project_name ,
            'content_type': 'text',
            "client": client,
            "region": region,
            "industry": industry,
            "prepared_date": prepared_date,
            "station_discipline": station_discipline,
            "scope_of_work": scope_of_work,
            "required_activities":required_activities
            
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


class TextExtractorRFI:
    """Handle text extraction and chunking logic"""
    
    def __init__(self):
        pass
    
    
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
        
    def create_text_chunks_with_simple_chunker_for_RFI(self, text_elements: List[Dict], document_metadata: Dict, project_id: str = None) -> List[Dict]:
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
        # rfp_id = self.extract_rfp_id_from_text(all_text)
        chunker = SimpleChunkerRFI()
        chunks = chunker.chunk_text_for_RFI(all_text, document_metadata, project_id=project_id)
        chunker.debug_text_analysis(all_text)
        # chunker.print_chunks(chunks)
        print(chunks)
        return chunks
        # return chunks
    