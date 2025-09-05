import os
from typing import Dict, List
from storage.local_storage import LocalStorage
# from llm_metadata.power_extractor import DocumentMetadataExtractor
# from llm_metadata.rfi_extractor import RFIMetadataExtractor
# from llm_metadata.document_type_detector import DocumentTypeDetector
from llm_metadata import RFIExtractor, RFPExtractor
from llm_metadata.document_type_detector import DocumentTypeDetector
from .text_extractor import TextExtractor
from .table_extractor import TableExtractor
from .image_extractor import ImageExtractor
from .section_mapper import SectionMapper


class ContentExtractor:
    """Extract and process content from Azure Document Intelligence results with verbalization and LLM metadata extraction"""
    
    def __init__(self):
        self.storage = LocalStorage()
        self.text_elements = []  # Store for section association
        self.text_chunks = []  # Store text chunks for section mapping
        self.document_metadata = {}  # Store LLM-extracted document metadata
        # self.metadata_extractor = DocumentMetadataExtractor()  # LLM metadata extractor
        self.document_type_detector = DocumentTypeDetector()
        
        # Initialize modular extractors
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.section_mapper = SectionMapper()
    
    def extract_all_content(self, result, filename: str, client=None, operation_id=None) -> Dict:
        """Extract text, tables, and images from Azure Document Intelligence result with verbalization and LLM metadata extraction"""
        base_filename = os.path.splitext(filename)[0]
        
        print(f"🔍 Extracting content from {filename}...")
        print(f"📋 Debug: client={client is not None}, operation_id={operation_id}")
        
        # Extract content using Azure DI
        print(f"📋 Step 1: Extracting text elements...")
        self.text_elements = self.text_extractor.extract_text(result)
        print(f"📋 Text elements extracted: {len(self.text_elements)}")
        
        # NEW: Extract document metadata from first 2 pages using LLM
        # print(f"🤖 Step 1.5: Extracting document metadata using LLM from first 2 pages...")
        # self.document_metadata = self.metadata_extractor.extract_document_metadata(self.text_elements)
        # print(f"📋 Document metadata extracted: {len(self.document_metadata)} fields")
        print(f"📄 Step 1.2: Detecting document type (RFI vs RFP)...")
        detection_result = self.document_type_detector.detect_document_type(self.text_elements)
        self.document_type_detector.print_detection_summary(detection_result)
        doc_type = detection_result['document_type']

        print(f"🤖 Step 1.5: Extracting {doc_type} metadata using LLM from complete document...")
        
        if doc_type == "RFI":
            extractor = RFIExtractor()
            self.document_metadata = extractor.extract_metadata(self.text_elements)  # 8 fields
            print(f"📋 RFI metadata extracted: {len(self.document_metadata)} fields")
        else:  # RFP or any other document type defaults to RFP
            extractor = RFPExtractor()
            self.document_metadata = extractor.extract_metadata(self.text_elements)  # 11 fields  
            print(f"📋 RFP metadata extracted: {len(self.document_metadata)} fields")

        
        print(f"📋 Step 2: Creating text chunks with LLM metadata using SimpleChunker...")
        self.text_chunks = self.text_extractor.create_text_chunks_with_simple_chunker(self.text_elements, self.document_metadata)
        print(f"📋 Text chunks created: {len(self.text_chunks)}")
        
        print(f"📋 Step 3: Extracting tables with section association...")
        tables = self.table_extractor.extract_tables(result, base_filename, self.section_mapper)
        print(f"📋 Tables extracted: {len(tables)}")
        
        print(f"📋 Step 4: Extracting figures with section association...")
        figures = self.image_extractor.extract_figures(result, base_filename, client, operation_id, self.section_mapper, self.text_elements)
        print(f"📋 Figures extracted: {len(figures)}")
        
        # Create table chunks with verbalization, section mapping, and LLM metadata
        print(f"🤖 Creating table chunks with verbalization, section mapping, and LLM metadata...")
        table_chunks = self.table_extractor.create_table_chunks(tables, base_filename, self.document_metadata, self.section_mapper, self.text_elements)
        
        # Create image chunks with verbalization, section mapping, and LLM metadata
        print(f"🤖 Creating image chunks with verbalization, section mapping, and LLM metadata...")
        image_chunks = self.image_extractor.create_image_chunks(figures, base_filename, self.document_metadata, self.section_mapper, self.text_elements)
        
        # Combine all chunks
        all_chunks = self.text_chunks + table_chunks + image_chunks
        
        # Create all text content for raw text storage
        all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in self.text_elements])
        
        # Save text content to local storage
        if all_text.strip():
            self.storage.save_raw_text(all_text, base_filename)
        
        # Save enhanced text chunks to local storage (now includes LLM metadata)
        if all_chunks:
            self.storage.save_text_chunks(all_chunks, base_filename)
        
        print(f"✅ Content extraction complete!")
        
        # Print debug information
        self._print_extraction_debug(all_text, self.text_chunks, tables, figures, table_chunks, image_chunks)
        
        return {
            "text": all_text,
            "text_chunks": all_chunks,
            "tables": tables,
            "images": figures,
            "raw_text": all_text,
            "document_metadata": self.document_metadata,  # Include LLM-extracted metadata in response
            "stats": {
                "text_count": len(self.text_chunks),
                "table_count": len(table_chunks),
                "image_count": len(image_chunks),
                "total_chunks": len(all_chunks)
            }
        }
    
    def _print_extraction_debug(self, all_text, text_chunks, tables, figures, table_chunks, image_chunks):
        """Print comprehensive debug information with LLM metadata - FULL CONTENT DISPLAY INCLUDING 11 FIELDS"""
        # Print LLM-extracted metadata first - NOW WITH 11 FIELDS INCLUDING COMPLIANCE_STANDARD AND EQUIPMENTS_USED
        print(f"\n{'='*80}")
        print(f"🤖 LLM-EXTRACTED DOCUMENT METADATA")
        print(f"{'='*80}")
        print(f"📝 Project Title: {self.document_metadata.get('project_title', 'N/A')}")
        print(f"🏢 Client Name: {self.document_metadata.get('client_name', 'N/A')}")
        print(f"🏭 Vendor Name: {self.document_metadata.get('vendor_name', 'N/A')}")
        print(f"📅 Submission Date: {self.document_metadata.get('submission_date', 'N/A')}")
        print(f"🏷️ Domain Category: {self.document_metadata.get('domain_category', 'N/A')}")
        print(f"⚙️ Service Category: {self.document_metadata.get('service_category', 'N/A')}")
        print(f"💰 Revenue Range: {self.document_metadata.get('revenue_range', 'N/A')}")
        print(f"🌍 Region: {self.document_metadata.get('region', 'N/A')}")
        print(f"💵 Project Value: {self.document_metadata.get('project_value', 'N/A')}")
        print(f"📜 Compliance Standard: {self.document_metadata.get('compliance_standard', 'N/A')}")  # NEW
        print(f"🔧 Equipments Used: {self.document_metadata.get('equipments_used', 'N/A')}")           # NEW

        print(f"\n{'='*80}")
        print(f"🎯 ENHANCED SUMMARY WITH LLM INTEGRATION - 11 FIELDS")
        print(f"📝 Text chunks: {len(text_chunks)} (with LLM metadata)")
        print(f"📊 Table chunks: {len(table_chunks)} (with LLM metadata + verbalization)")
        print(f"🖼️ Image chunks: {len(image_chunks)} (with LLM metadata + verbalization)")
        print(f"🤖 LLM Metadata: ✅ Extracted 11 fields from first 2 pages")
        print(f"✅ All chunks now include: project_title→file_name, vendor_name→author, domain_category→domain")
        print(f"✅ EXISTING FIELDS: revenue_range→💰, region→🌍, project_value→💵")
        print(f"✅ NEW FIELDS: compliance_standard→📜, equipments_used→🔧")
        print(f"✅ FULL CONTENT DISPLAY: No truncation - see complete text, tables, and verbalizations")
        print(f"{'='*80}")