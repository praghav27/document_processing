
import os
from typing import Dict, List
from storage.storage_factory import get_storage_instance
from llm_metadata import RFIExtractor, RFPExtractor
from llm_metadata.document_type_detector import DocumentTypeDetector
from .text_extractor import TextExtractor  # Use existing file
from .table_extractor import TableExtractor  # Use existing file
from .image_extractor import ImageExtractor  # Use existing file
from .section_mapper import SectionMapper  # Use existing file
from .RFI_extractor import SimpleChunkerRFI,TextExtractorRFI
from data_indexing.data_to_rfp_indexer import AzureSearchRFPResponseUploader
from data_indexing.data_to_rfi_indexer import AzureSearchRFPRequestUploader
from config import (AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_KEY, AZURE_AI_SEARCH_RFI_INDEX_NAME,
    AZURE_AI_SEARCH_RFP_INDEX_NAME, ENABLE_DOCUMENT_TYPE_DETECTION, DEFAULT_DOCUMENT_TYPE)

from application_logging.custom_logging_to_app_insights import configure_logger, log_step, log_exception
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class ContentExtractor:
    """Extract and process content from Azure Document Intelligence results with verbalization and LLM metadata extraction"""
    
    def __init__(self):
        with tracer.start_as_current_span("ContentExtractor_init_fn") as span:
            self.storage = get_storage_instance()
            self.text_elements = []  # Store for section association
            self.text_chunks = []  # Store text chunks for section mapping
            self.document_metadata = {}  # Store LLM-extracted document metadata
            self.document_type = "RFP"  # Default document type
            self.document_type_info = {}  # Store document type detection results
            
            # Initialize document type detector
            self.type_detector = DocumentTypeDetector()
            self.data_indexing_RFP_request= AzureSearchRFPRequestUploader()
            self.data_indexing_RFP_response = AzureSearchRFPResponseUploader()
            # Initialize modular extractors (using existing files)
            self.text_extractor_RFI =TextExtractorRFI()
            self.text_extractor = TextExtractor()
            self.table_extractor = TableExtractor()
            self.image_extractor = ImageExtractor()
            self.section_mapper = SectionMapper()  # ✅ Keep section mapping separate

    def _extract_project_id_from_filename(self, filename: str) -> str:
        """Extract project ID (first 15 characters) from filename"""
        if not filename:
            return "unknown_project"
        
        # Remove file extension and get first 15 characters
        base_name = os.path.splitext(filename)[0]
        project_id = base_name[:15] if len(base_name) >= 15 else base_name
        print(f"🔑 Extracted Project ID: {project_id}")
        return project_id
    
    async def extract_all_content(self, result, filename: str, client=None, operation_id=None) -> Dict:
        with tracer.start_as_current_span("extract_all_content_fn") as span:
            """Extract text, tables, and images from Azure Document Intelligence result with verbalization and LLM metadata extraction"""
            base_filename = os.path.splitext(filename)[0]
            
            print(f"🔍 Extracting content from {filename}...")
            print(f"📋 Debug: client={client is not None}, operation_id={operation_id}")
            
            # Extract content using Azure DI
            print(f"📋 Step 1: Extracting text elements...")
            self.text_elements = self.text_extractor.extract_text(result)
            print(f"📋 Text elements extracted: {len(self.text_elements)}")

            all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in self.text_elements])
            rfp_id = self.text_extractor.extract_rfp_id_from_text(all_text)
            print(f"🔑 Extracted RFP ID for all chunks: {rfp_id}")
            
            # Extract project ID from filename
            project_id = self._extract_project_id_from_filename(filename)
            
            # Step 1.2 - Document type selection (Auto-detect or Hardcoded)
            if ENABLE_DOCUMENT_TYPE_DETECTION:
                print(f"📄 Step 1.2: Auto-detecting document type (RFI vs RFP)...")
                self.document_type_info = self.type_detector.detect_document_type(self.text_elements)
                self.document_type = self.document_type_info.get('document_type', 'RFP')
                document_type_folder = "rfp_request" if self.document_type == "RFI" else "rfp_response"
                self.storage.set_project_context(filename, document_type_folder)
                self.type_detector.print_detection_summary(self.document_type_info)
            else:
                self.document_type = DEFAULT_DOCUMENT_TYPE
                print(f"🔒 HARDCODED: Using {self.document_type} extractor (detection disabled)")
                self.document_type_info = {
                    'document_type': self.document_type,
                    'confidence': 1.0,
                    'reasoning': 'Hardcoded configuration setting'
                }
                
            document_type_folder = "rfp_request" if self.document_type == "RFI" else "rfp_response"
            self.storage.set_project_context(filename, document_type_folder)    

            # Step 1.5 - Extract document metadata using selected extractor
            if self.document_type == "RFI":
                print(f"🤖 Step 1.5: Enhanced RFI metadata extraction (DI text + First page content)...")
                rfi_extractor = RFIExtractor()
                # 🚀 ENHANCED: Pass the Azure DI result to extract first page content
                self.document_metadata = await rfi_extractor.extract_metadata_only(self.text_elements, azure_di_result=result)
                print(f"📋 Enhanced RFI metadata extracted: {len(self.document_metadata)} fields")
                print(f"   📄 Enhancement: Document Intelligence text + First page comprehensive content")
            else:
                print(f"🤖 Step 1.5: Extracting RFP metadata using LLM from complete document...")
                rfp_extractor = RFPExtractor()
                self.document_metadata = await rfp_extractor.extract_metadata(self.text_elements)
                print(f"📋 RFP metadata extracted: {len(self.document_metadata)} fields")
                    
            print(f"📋 Step 2: Creating text chunks with LLM metadata...")
            
            # Create text chunks based on document type
            if self.document_type == "RFI":
                print(f"🔍 Creating RFI text chunks (metadata-only approach)...")
                self.text_chunks = self.text_extractor_RFI.create_text_chunks_with_simple_chunker_for_RFI(
                    self.text_elements, 
                    self.document_metadata, 
                    project_id
                )
                print(f"📋 RFI Text chunks created: {len(self.text_chunks)}")
            else:
                print(f"🔍 Creating RFP text chunks (full processing approach)...")
                self.text_chunks = self.text_extractor.create_text_chunks_with_simple_chunker_for_RFP(
                    self.text_elements, 
                    self.document_metadata, 
                    project_id
                )
                print(f"📋 RFP Text chunks created: {len(self.text_chunks)}")
            
            # Initialize chunk lists
            table_chunks = []
            image_chunks = []
            
            if self.document_type == "RFP":
                # Full RFP processing with tables and images
                print(f"📋 Step 3: Extracting tables with section association...")
                tables = self.table_extractor.extract_tables(result, base_filename, self.section_mapper, self.storage)
                print(f"📊 Tables extracted: {len(tables)}")

                print(f"📋 Step 4: Extracting figures with section association...")
                figures = self.image_extractor.extract_figures(result, base_filename, client, operation_id, self.section_mapper, self.text_elements, self.storage)
                print(f"🖼️ Figures extracted: {len(figures)}")
                
                # Create table chunks with verbalization, section mapping, and LLM metadata
                print(f"🤖 Creating table chunks with verbalization, section mapping, and LLM metadata...")
                table_chunks = await self.table_extractor.create_table_chunks(
                    tables, 
                    base_filename, 
                    self.document_metadata, 
                    self.section_mapper, 
                    self.text_elements, 
                    rfp_id=rfp_id, 
                    project_id=project_id
                )
                print(f"📊 Table chunks created: {len(table_chunks)}")

                # Create image chunks with verbalization, section mapping, and LLM metadata
                print(f"🤖 Creating image chunks with verbalization, section mapping, and LLM metadata...")
                image_chunks = await self.image_extractor.create_image_chunks(
                    figures, 
                    base_filename, 
                    self.document_metadata, 
                    self.section_mapper, 
                    self.text_elements, 
                    rfp_id=rfp_id, 
                    project_id=project_id
                )
                print(f"🖼️ Image chunks created: {len(image_chunks)}")
            else:
                # RFI processing - skip table and image chunk creation
                print(f"📋 Step 3-4: Skipping table/image extraction for RFI (metadata-only approach)")
                tables = []
                figures = []
                print(f"📊 RFI: Table chunks skipped")
                print(f"🖼️ RFI: Image chunks skipped")

            # Combine all chunks based on document type
            if self.document_type == "RFI":
                all_chunks = self.text_chunks
                print(f"📋 RFI: Using only text chunks, total: {len(all_chunks)}")
            else:
                all_chunks = self.text_chunks + table_chunks + image_chunks
                print(f"📋 RFP: Combined all chunk types, total: {len(all_chunks)}")
            
            # Create all text content for raw text storage
            all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in self.text_elements])
            
            #Save to storage and upload to Azure AI Search
            if all_chunks:
                if self.document_type == "RFI":
                    print(f"💾 Saving enhanced RFI text chunks to storage...")
                    chunk_data, json_path = self.storage.save_text_chunks_RFI(all_chunks, base_filename)
                    if chunk_data:
                        print(f"📊 RFI chunk data prepared for indexing:")
                        print(f"   📝 Total chunks: {chunk_data.get('total_chunks', 0)}")
                        print(f"   🎯 Processing method: {chunk_data.get('processing_method', 'N/A')}")
                        
                        # Upload to Azure AI Search RFI index
                        print(f"📤 Uploading RFI data to Azure AI Search RFI index...")
                        self.data_indexing_RFP_request.upload_chunks_from_dict(chunk_data)
                        print(f"✅ RFI data successfully uploaded to Azure AI Search RFI index")
                    else:
                        print("❌ Failed to prepare RFI chunk data for indexing")
                else:
                    print(f"💾 Saving RFP text chunks to storage...")
                    chunk_data, json_path = self.storage.save_text_chunks(all_chunks, base_filename)
                    if chunk_data:
                        print(f"📊 RFP chunk data prepared for indexing:")
                        print(f"   📝 Total chunks: {chunk_data.get('total_chunks', 0)}")
                        print(f"   🎯 Processing method: {chunk_data.get('processing_method', 'N/A')}")
                        
                        # Upload to Azure AI Search RFP index
                        print(f"📤 Uploading RFP data to Azure AI Search RFP index...")
                        self.data_indexing_RFP_response.upload_chunks_from_dict(chunk_data)
                        print(f"✅ RFP data successfully uploaded to Azure AI Search RFP index")
                    else:
                        print("❌ Failed to prepare RFP chunk data for indexing")

            # Save raw text content to storage
            if all_text.strip():
                print(f"💾 Saving raw text content...")
                self.storage.save_raw_text(all_text, base_filename)
            
            print(f"✅ Enhanced content extraction and indexing complete!")
            
            # Print comprehensive debug information
            self._print_extraction_debug(all_text, self.text_chunks, tables, figures, table_chunks, image_chunks)

            return {
                "text": all_text,
                "text_chunks": all_chunks,
                "tables": tables if self.document_type == "RFP" else [],
                "images": figures if self.document_type == "RFP" else [],
                "raw_text": all_text,
                "document_metadata": self.document_metadata,  # Include LLM-extracted metadata in response
                "document_type": self.document_type,  # Include detected document type
                "document_type_info": self.document_type_info,  # Include detection details
                "project_id": project_id,  # Include project_id in response
                "enhancement_info": {
                    "rfi_first_page_extraction": self.document_type == "RFI",
                    "extraction_method": "DI_text + first_page_content" if self.document_type == "RFI" else "DI_text_only",
                    "processing_approach": "metadata_only" if self.document_type == "RFI" else "full_processing"
                },
                "stats": {
                    "text_count": len(self.text_chunks),
                    "table_count": len(table_chunks),
                    "image_count": len(image_chunks),
                    "total_chunks": len(all_chunks)
                }
            }
    
    def _print_extraction_debug(self, all_text, text_chunks, tables, figures, table_chunks, image_chunks):
        """Print comprehensive debug information with LLM metadata - FULL CONTENT DISPLAY INCLUDING RFI/RFP DETECTION"""
        
        # Print Document Type Detection Results FIRST
        print(f"\n{'='*80}")
        print(f"📄 DOCUMENT TYPE DETECTION RESULTS")
        print(f"{'='*80}")
        print(f"🎯 Detected Type: {self.document_type}")
        print(f"📊 Confidence: {self.document_type_info.get('confidence', 0):.1%}")
        print(f"🔍 RFP Score: {self.document_type_info.get('rfp_score', 0)}")
        print(f"🔍 RFI Score: {self.document_type_info.get('rfi_score', 0)}")
        print(f"💭 Reasoning: {self.document_type_info.get('reasoning', 'No reasoning available')}")
        
        # Print LLM-extracted metadata - WITH APPROPRIATE FIELD COUNT BASED ON DOCUMENT TYPE
        print(f"\n{'='*80}")
        if self.document_type == "RFI":
            print(f"🤖 ENHANCED RFI DOCUMENT METADATA EXTRACTION (8 FIELDS)")
            print(f"{'='*80}")
            print(f"🚀 ENHANCEMENT: Document Intelligence text + First page comprehensive content")
            print(f"📄 First Page Content: Tables + Images + Text from page 1")
            print(f"🔍 Extraction Source: Combined content for maximum accuracy")
            print(f"")
            print(f"📝 Project Name: {self.document_metadata.get('project_name', 'N/A')}")
            print(f"🏢 Client: {self.document_metadata.get('client', 'N/A')}")
            print(f"🌍 Region: {self.document_metadata.get('region', 'N/A')}")
            print(f"🏭 Industry: {self.document_metadata.get('industry', 'N/A')}")
            print(f"📅 Prepared Date: {self.document_metadata.get('prepared_date', 'N/A')}")
            print(f"⚙️ Station Discipline: {self.document_metadata.get('station_discipline', 'N/A')}")
            print(f"🎯 Scope of Work: {len(str(self.document_metadata.get('scope_of_work', '')))} characters")
            print(f"📋 Required Activities: {len(str(self.document_metadata.get('required_activities', '')))} characters")
        else:
            print(f"🤖 LLM-EXTRACTED RFP DOCUMENT METADATA (11 FIELDS)")
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
            print(f"📜 Compliance Standard: {self.document_metadata.get('compliance_standard', 'N/A')}")
            print(f"🔧 Equipments Used: {self.document_metadata.get('equipments_used', 'N/A')}")

        print(f"\n{'='*80}")
        field_count = 8 if self.document_type == "RFI" else 11
        print(f"🎯 ENHANCED SUMMARY WITH LLM INTEGRATION - {field_count} FIELDS ({self.document_type})")
        print(f"📄 Document Type: {self.document_type} (Confidence: {self.document_type_info.get('confidence', 0):.1%})")
        
        if self.document_type == "RFI":
            print(f"🚀 RFI ENHANCEMENT: DI text + First page (tables + images + text)")
            print(f"📝 Text chunks: {len(text_chunks)} (RFI metadata only)")
            print(f"📊 Table chunks: SKIPPED for RFI")
            print(f"🖼️ Image chunks: SKIPPED for RFI") 
            print(f"🎯 Index Target: Azure AI Search RFI Index")
        else:
            print(f"📝 Text chunks: {len(text_chunks)} (with LLM metadata)")
            print(f"📊 Table chunks: {len(table_chunks)} (with LLM metadata + verbalization)")
            print(f"🖼️ Image chunks: {len(image_chunks)} (with LLM metadata + verbalization)")
            print(f"🎯 Index Target: Azure AI Search RFP Index")
            
        print(f"🤖 LLM Metadata: ✅ Extracted {field_count} fields from {'enhanced' if self.document_type == 'RFI' else 'standard'} content")
        print(f"🗂️ Section Mapping: ✅ Using separate SectionMapper for clean architecture")
        
        if self.document_type == "RFI":
            print(f"✅ RFI Fields: project_name, client, region, industry, prepared_date, station_discipline, scope_of_work, required_activities")
            print(f"🚀 Enhancement Active: First page comprehensive content extraction")
        else:
            print(f"✅ RFP Fields: project_title→file_name, vendor_name→author, domain_category→domain")
            print(f"✅ Financial Fields: revenue_range→💰, region→🌍, project_value→💵")
            print(f"✅ Technical Fields: compliance_standard→📜, equipments_used→🔧")
            
        print(f"✅ FULL CONTENT PROCESSING: Enhanced extraction for RFI, standard for RFP")
        print(f"{'='*80}")

        # Show storage and indexing paths
        if hasattr(self.storage, 'project_id') and hasattr(self.storage, 'document_type'):
            print(f"💾 Storage Path: {self.storage.project_id}/{self.storage.document_type}")
            print(f"🎯 Search Index: {'Azure AI Search RFI Index' if self.document_type == 'RFI' else 'Azure AI Search RFP Index'}")
            print(f"📊 Processing Method: {'Enhanced (DI + First Page)' if self.document_type == 'RFI' else 'Standard (DI Only)'}")