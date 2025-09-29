import json
import os
from typing import Dict, List
from storage.storage_factory import get_storage_instance
from storage.azure_table_storage import AzureTableMetadataHandler
from llm_metadata import RFIExtractor, RFPExtractor
from llm_metadata.document_type_detector import DocumentTypeDetector
from .text_extractor import TextExtractor  # Use existing file
from .table_extractor import TableExtractor  # Use existing file
from .image_extractor import ImageExtractor  # Use existing file
from .section_mapper import SectionMapper  # Use existing file
from .RFI_extractor import SimpleChunkerRFI,TextExtractorRFI

from data_indexing.rfp_request_indexer import RFPRequestIndexManager
from data_indexing.rfp_response_indexer import RFPResponseIndexManager

from data_indexing.data_to_rfp_indexer import AzureSearchRFPResponseUploader
from data_indexing.data_to_rfi_indexer import AzureSearchRFPRequestUploader
from config import (AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_KEY, AZURE_AI_SEARCH_RFI_INDEX_NAME,
    AZURE_AI_SEARCH_RFP_INDEX_NAME, ENABLE_DOCUMENT_TYPE_DETECTION, DEFAULT_DOCUMENT_TYPE)

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
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
            self.table_handler = AzureTableMetadataHandler()  # ✅ Azure Table Storage handler
            self.text_elements = []  # Store for section association
            self.text_chunks = []  # Store text chunks for section mapping
            self.document_metadata = {}  # Store LLM-extracted document metadata
            self.document_type = "RFI"  # Default document type
            self.document_type_info = {}  # Store document type detection results
            
            # Initialize document type detector
            self.type_detector = DocumentTypeDetector()
            
            self.rfp_request_index_manager = RFPRequestIndexManager()
            self.rfp_response_index_manager = RFPResponseIndexManager()
            
            self.data_indexing_RFP_request= AzureSearchRFPRequestUploader()
            self.data_indexing_RFP_response = AzureSearchRFPResponseUploader()
            # Initialize modular extractors (using existing files)
            self.text_extractor_RFI =TextExtractorRFI()
            self.text_extractor = TextExtractor()
            self.table_extractor = TableExtractor()
            self.image_extractor = ImageExtractor()
            self.section_mapper = SectionMapper()  # ✅ Keep section mapping separate

    # async def _extract_project_id_from_filename(self, filename: str) -> str:
        # """Extract project ID (first 15 characters) from filename"""
        # if not filename:
        #     return "unknown_project"
        
        # # Remove file extension and get first 15 characters
        # base_name = os.path.splitext(filename)[0]
        # project_id = base_name[:15] if len(base_name) >= 15 else base_name
        # #print(f"🔑 Extracted Project ID: {project_id}")

        # return project_id
    async def _extract_project_id_from_filename(self, filename: str) -> str:
        """Extract project ID from standardized filename"""
        if not filename:
            return "unknown_project"
        
        base_name = os.path.splitext(filename)[0]
        
        # Since we standardize filenames, project ID is always first 15 chars
        return base_name[:15] if len(base_name) >= 15 else base_name
    
    async def extract_all_content(self, result, filename: str, client=None, operation_id=None, document_type_override=None) -> Dict:
        with tracer.start_as_current_span("extract_all_content_fn") as span:
            """Extract text, tables, and images from Azure Document Intelligence result with verbalization and LLM metadata extraction"""
            base_filename = os.path.splitext(filename)[0]
            
            # print(f"🔍 Extracting content from {filename}...")
            # print(f"📋 Debug: client={client is not None}, operation_id={operation_id}")
            
            # Extract content using Azure DI
            #print(f"📋 Step 1: Extracting text elements...")
            self.text_elements = self.text_extractor.extract_text(result)
            #print(f"📋 Text elements extracted: {len(self.text_elements)}")

            all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in self.text_elements])
            rfp_id = self.text_extractor.extract_rfp_id_from_text(all_text)
            #(f"🔑 Extracted RFP ID for all chunks: {rfp_id}")
            
            # Extract project ID from filename
            project_id = await self._extract_project_id_from_filename(filename)
            
            

            # Step 1.2 - Document type selection with OVERRIDE SUPPORT
            if document_type_override:
                self.document_type = document_type_override
                print(f"🔒 EXPLICIT OVERRIDE: Using {self.document_type} from folder hint")
                self.document_type_info = {
                    'document_type': self.document_type,
                    'confidence': 1.0,
                    'reasoning': f'Explicit override to {document_type_override} based on folder structure'
                }
            elif ENABLE_DOCUMENT_TYPE_DETECTION:
                #print(f"📄 Step 1.2: Auto-detecting document type (RFI vs RFP)...")
                self.document_type_info = self.type_detector.detect_document_type(self.text_elements)
                self.document_type = self.document_type_info.get('document_type', 'RFI')
                self.type_detector.print_detection_summary(self.document_type_info)
            else:
                self.document_type = DEFAULT_DOCUMENT_TYPE
                #print(f"🔒 HARDCODED: Using {self.document_type} extractor (detection disabled)")
                self.document_type_info = {
                    'document_type': self.document_type,
                    'confidence': 1.0,
                    'reasoning': 'Hardcoded configuration setting'
                }
                
            document_type_folder = "rfp_request" if self.document_type == "RFI" else "rfp_response"
            self.storage.set_project_context(filename, document_type_folder)
            # if ENABLE_DOCUMENT_TYPE_DETECTION:
            #     #print(f"📄 Step 1.2: Auto-detecting document type (RFI vs RFP)...")
            #     self.document_type_info = self.type_detector.detect_document_type(self.text_elements)
            #     self.document_type = self.document_type_info.get('document_type', 'RFI')
            #     document_type_folder = "rfp_request" if self.document_type == "RFI" else "rfp_response"
            #     self.storage.set_project_context(filename, document_type_folder)
            #     self.type_detector.print_detection_summary(self.document_type_info)
            # else:
            #     self.document_type = DEFAULT_DOCUMENT_TYPE
            #     #print(f"🔒 HARDCODED: Using {self.document_type} extractor (detection disabled)")
            #     self.document_type_info = {
            #         'document_type': self.document_type,
            #         'confidence': 1.0,
            #         'reasoning': 'Hardcoded configuration setting'
            #     }
                
            # document_type_folder = "rfp_request" if self.document_type == "RFI" else "rfp_response"
            # self.storage.set_project_context(filename, document_type_folder)    

            # Step 1.5 - Extract document metadata using selected extractor
            if self.document_type == "RFI":
                print(f"🤖 Step 1.5: Enhanced RFI metadata extraction (DI text + First 10 page content)...")
                rfi_extractor = RFIExtractor()
                # 🚀 ENHANCED: Pass the Azure DI result to extract first 10 page content
                self.document_metadata = await rfi_extractor.extract_metadata_only(self.text_elements, azure_di_result=result)
                # print(f"📋 Enhanced RFI metadata extracted: {len(self.document_metadata)} fields")
                # print(f"   📄 Enhancement: Document Intelligence text + First 10 page comprehensive content")
            else:
                #print(f"🤖 Step 1.5: Extracting RFP metadata using LLM from complete document...")
                rfp_extractor = RFPExtractor()
                self.document_metadata = await rfp_extractor.extract_metadata(self.text_elements)
                #print(f"📋 RFP metadata extracted: {len(self.document_metadata)} fields")

            # 🆕 Step 1.6 - Store metadata in Azure Table Storage (ENHANCED INTEGRATION)
            #print(f"💾 Step 1.6: Storing metadata in Azure Table Storage...")
            table_storage_success = await self._store_metadata_in_table_storage(filename, project_id)
                    
            #print(f"📋 Step 2: Creating text chunks with LLM metadata...")
            
            # Create text chunks based on document type
            if self.document_type == "RFI":
                #print(f"🔍 Creating RFI text chunks (metadata-only approach)...")
                self.text_chunks = self.text_extractor_RFI.create_text_chunks_with_simple_chunker_for_RFI(
                    self.text_elements, 
                    self.document_metadata, 
                    project_id
                )
                #print(f"📋 RFI Text chunks created: {len(self.text_chunks)}")
            else:
                #print(f"🔍 Creating RFP text chunks (full processing approach)...")
                self.text_chunks = self.text_extractor.create_text_chunks_with_simple_chunker_for_RFP(
                    self.text_elements, 
                    self.document_metadata, 
                    project_id
                )
                #print(f"📋 RFP Text chunks created: {len(self.text_chunks)}")
            
            # Initialize chunk lists
            table_chunks = []
            image_chunks = []
            
            if self.document_type == "RFP":
                # Full RFP processing with tables and images
                #print(f"📋 Step 3: Extracting tables with section association...")
                tables = self.table_extractor.extract_tables(result, base_filename, self.section_mapper, self.storage)
                #print(f"📊 Tables extracted: {len(tables)}")

                #print(f"📋 Step 4: Extracting figures with section association...")
                figures = self.image_extractor.extract_figures(result, base_filename, client, operation_id, self.section_mapper, self.text_elements, self.storage)
                #print(f"🖼️ Figures extracted: {len(figures)}")
                
                # Create table chunks with verbalization, section mapping, and LLM metadata
                #print(f"🤖 Creating table chunks with verbalization, section mapping, and LLM metadata...")
                table_chunks = await self.table_extractor.create_table_chunks(
                    tables, 
                    base_filename, 
                    self.document_metadata, 
                    self.section_mapper, 
                    self.text_elements, 
                    rfp_id=rfp_id, 
                    project_id=project_id
                )
                #print(f"📊 Table chunks created: {len(table_chunks)}")

                # Create image chunks with verbalization, section mapping, and LLM metadata
                #print(f"🤖 Creating image chunks with verbalization, section mapping, and LLM metadata...")
                image_chunks = await self.image_extractor.create_image_chunks(
                    figures, 
                    base_filename, 
                    self.document_metadata, 
                    self.section_mapper, 
                    self.text_elements, 
                    rfp_id=rfp_id, 
                    project_id=project_id
                )
                #print(f"🖼️ Image chunks created: {len(image_chunks)}")
            else:
                # RFI processing - skip table and image chunk creation
                #print(f"📋 Step 3-4: Skipping table/image extraction for RFI (metadata-only approach)")
                tables = []
                figures = []
                # print(f"📊 RFI: Table chunks skipped")
                # print(f"🖼️ RFI: Image chunks skipped")

            # Combine all chunks based on document type
            if self.document_type == "RFI":
                all_chunks = self.text_chunks
                #print(f"📋 RFI: Using only text chunks, total: {len(all_chunks)}")
            else:
                all_chunks = self.text_chunks + table_chunks + image_chunks
                #print(f"📋 RFP: Combined all chunk types, total: {len(all_chunks)}")
            
            # Create all text content for raw text storage
            all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in self.text_elements])
            
            #Save to storage and upload to Azure AI Search
            if all_chunks:
                if self.document_type == "RFI":
                    #print(f"💾 Saving enhanced RFI text chunks to storage...")
                    chunk_data, json_path = self.storage.save_text_chunks_RFI(all_chunks, base_filename)
                    with open("expand_chunk_by_component", "a") as outfile:
                        json.dump(chunk_data, outfile)
                        outfile.write("\n")
                    if chunk_data:
                        # print(f"📊 RFI chunk data prepared for indexing:")
                        # print(f"   📝 Total chunks: {chunk_data.get('total_chunks', 0)}")
                        # print(f"   🎯 Processing method: {chunk_data.get('processing_method', 'N/A')}")
                        # Upload to Azure AI Search RFI index
                        #print(f"📤 Uploading RFI data to Azure AI Search RFI index...")
                        self.rfp_request_index_manager.recreate_index()
                        created_at=chunk_data.get("created_at")
                        print(created_at)
                        self.data_indexing_RFP_request.upload_chunks_from_dict(chunk_data)
                        #print(f"✅ RFI data successfully uploaded to Azure AI Search RFI index")
                    else:
                        #print("❌ Failed to prepare RFI chunk data for indexing")
                        print()
                else:
                    #print(f"💾 Saving RFP text chunks to storage...")
                    chunk_data, json_path = self.storage.save_text_chunks(all_chunks, base_filename)
                    if chunk_data:
                        # print(f"📊 RFP chunk data prepared for indexing:")
                        # print(f"   📝 Total chunks: {chunk_data.get('total_chunks', 0)}")
                        # print(f"   🎯 Processing method: {chunk_data.get('processing_method', 'N/A')}")
                        # Upload to Azure AI Search RFP index
                        #print(f"📤 Uploading RFP data to Azure AI Search RFP index...")
                        self.rfp_response_index_manager.recreate_index()
                        self.data_indexing_RFP_response.upload_chunks_from_dict(chunk_data)
                        #print(f"✅ RFP data successfully uploaded to Azure AI Search RFP index")
                    else:
                        #print("❌ Failed to prepare RFP chunk data for indexing")
                        print()

            # Save raw text content to storage
            if all_text.strip():
                #print(f"💾 Saving raw text content...")
                self.storage.save_raw_text(all_text, base_filename)
            
            #print(f"✅ Enhanced content extraction, table storage, and AI Search indexing complete!")
            log_custom_event(
                 logger,
                 f"Enhanced content extraction, table storage, and AI Search indexing complete!",
                 level="info",
                )
            
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
                    "extraction_method": "DI_text + first_10_page_content" if self.document_type == "RFI" else "DI_text_only",
                    "processing_approach": "metadata_only" if self.document_type == "RFI" else "full_processing",
                    "table_storage_enabled": True  # 🆕 Indicate table storage is enabled
                },
                "stats": {
                    "text_count": len(self.text_chunks),
                    "table_count": len(table_chunks),
                    "image_count": len(image_chunks),
                    "total_chunks": len(all_chunks)
                }
            }

    @tracer.start_as_current_span("_store_metadata_in_table_storage_fn")
    async def _store_metadata_in_table_storage(self, filename: str, project_id: str) -> bool:
        """Store metadata in Azure Table Storage using your exact logic"""
        try:
            print(f"💾 Starting Azure Table Storage operations for {filename}...")
            
            # Step 1: Prepare file metadata for table storage
            file_metadata = self.document_metadata.copy()
            file_metadata.update({
                'document_type': self.document_type,
                'project_id': project_id,
                'filename': filename,
                'detection_confidence': self.document_type_info.get('confidence', 0),
                'detection_reasoning': self.document_type_info.get('reasoning', ''),
                'processing_timestamp': self.document_metadata.get('created_at', ''),
                'extraction_method': 'enhanced_llm_with_first_10_pages' if self.document_type == "RFI" else 'standard_llm'
            })
            #print(f"🔍 DEBUG: File metadata keys = {list(file_metadata.keys())}")
            # Store file metadata in FileMetadata table
            file_entity_key = self.table_handler.store_file_metadata(file_metadata, "FileMetadata")
            file_metadata_success = False
            if file_entity_key:
                #print(f"✅ File metadata stored successfully: {file_entity_key}")
                file_metadata_success = True
            else:
                #print(f"❌ Failed to store file metadata")
                print()
            component_data_success = False

            if self.document_type == "RFI":
                print(f"💾 Storing RFI component data in ComponentData ...")
                component_data_success = True  # Initialize as True
                if self.text_chunks:
                    for chunk in self.text_chunks:
                        # Each chunk now represents one component
                        component_name = chunk.get('component_name', '')
                        discipline = chunk.get('discipline', 'unknown_discipline')
                        components = chunk.get('components', {})
                        if component_name and components.get(component_name):
                            component_data_dict = {
                                "chunk_id": chunk.get("chunk_id", ""),
                                "project_id": chunk.get("project_id", ""),
                                "project_name": chunk.get("project_name", ""),
                                "content_type": chunk.get("content_type", "text"),
                                "client": chunk.get("client", ""),
                                "region": chunk.get("region", ""),
                                "industry": chunk.get("industry", ""),
                                "prepared_date": chunk.get("prepared_date", ""),
                                "field_type": chunk.get("field_type", ""),
                                "voltage": chunk.get("voltage", ""),
                                "contract_types": chunk.get("contract_types", ""),
                                "pricing": chunk.get("pricing", ""),
                                "location": chunk.get("location", ""),
                                "state": chunk.get("state", ""),
                                "country": chunk.get("country", ""),
                                "component_name": component_name,  # NEW
                                "discipline": discipline,  # NEW
                                "components": components
                            }
                            component_entity_keys = self.table_handler.store_component_data(component_data_dict, "ComponentDataV4")
                            if not component_entity_keys:
                                component_data_success = False
                                print(f"❌ Failed to store component data for {component_name} in chunk {chunk.get('chunk_id', '')}")
                            else:
                                print(f"✅ Component data stored successfully: {component_name} ({discipline}) for chunk {chunk.get('chunk_id', '')}")
                        else:
                            print(f"⚠️ Skipping chunk - no valid component data: {chunk.get('chunk_id', '')}")
                    if not self.text_chunks:
                        print(f"❌ No text chunks available for component data storage")
                        component_data_success = False
                else:
                    print(f"❌ No text chunks available for component data storage")
                    component_data_success = False

            elif self.document_type == "RFP":
                print(f"ℹ️ RFP document - skipping component data storage")
                component_data_success = True
            overall_success = file_metadata_success and component_data_success
            if overall_success:
                #print(f"✅ Azure Table Storage operations completed successfully")
                print()
            else:
                # print(f"⚠️ Azure Table Storage operations completed with some failures")
                # print(f"   File metadata success: {file_metadata_success}")
                # print(f"   Component data success: {component_data_success}")
                print()
            return overall_success
        except Exception as e:
            #print(f"❌ Error storing metadata in Azure Table Storage: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _print_extraction_debug(self, all_text, text_chunks, tables, figures, table_chunks, image_chunks):
        """Print comprehensive debug information with LLM metadata - FULL CONTENT DISPLAY INCLUDING RFI/RFP DETECTION"""
        
        # Print Document Type Detection Results FIRST
        # print(f"\n{'='*80}")
        # print(f"📄 DOCUMENT TYPE DETECTION RESULTS")
        # print(f"{'='*80}")
        # print(f"🎯 Detected Type: {self.document_type}")
        # print(f"📊 Confidence: {self.document_type_info.get('confidence', 0):.1%}")
        # print(f"🔍 RFP Score: {self.document_type_info.get('rfp_score', 0)}")
        # print(f"🔍 RFI Score: {self.document_type_info.get('rfi_score', 0)}")
        # print(f"💭 Reasoning: {self.document_type_info.get('reasoning', 'No reasoning available')}")
        
        # Print LLM-extracted metadata - WITH APPROPRIATE FIELD COUNT BASED ON DOCUMENT TYPE
        #print(f"\n{'='*80}")
        if self.document_type == "RFI":
            # print(f"🤖 ENHANCED RFI DOCUMENT METADATA EXTRACTION (10 FIELDS) + AZURE TABLE STORAGE")
            # print(f"{'='*80}")
            # print(f"🚀 ENHANCEMENT: Document Intelligence text + First page comprehensive content")
            # print(f"📄 First Page Content: Tables + Images + Text from page 1")
            # print(f"🔍 Extraction Source: Combined content for maximum accuracy")
            # print(f"💾 Table Storage: File metadata + Component data stored in Azure Tables")
            # print(f"")
            # print(f"📝 Project Name: {self.document_metadata.get('project_name', 'N/A')}")
            # print(f"🏢 Client: {self.document_metadata.get('client', 'N/A')}")
            # print(f"🌍 Region: {self.document_metadata.get('region', 'N/A')}")
            # print(f"🏭 Industry: {self.document_metadata.get('industry', 'N/A')}")
            # print(f"📅 Prepared Date: {self.document_metadata.get('prepared_date', 'N/A')}")
            # print(f"🏞️ Field Type: {self.document_metadata.get('field_type', 'N/A')}")
            # print(f"🔌 Voltage Class: {self.document_metadata.get('voltage_class', 'N/A')}")
            # print(f"📃 Contract Types: {self.document_metadata.get('contract_types', 'N/A')}")
            # print(f"💰 Pricing: {self.document_metadata.get('pricing', 'N/A')}")
            # print(f"🧩 Components: {len(self.document_metadata.get('components', {}))} components identified")
            print()
        
        else:
            # print(f"🤖 LLM-EXTRACTED RFP DOCUMENT METADATA (11 FIELDS) + AZURE TABLE STORAGE")
            # print(f"{'='*80}")
            # print(f"💾 Table Storage: File metadata stored in Azure Tables")
            # print(f"📝 Project Title: {self.document_metadata.get('project_title', 'N/A')}")
            # print(f"🏢 Client Name: {self.document_metadata.get('client_name', 'N/A')}")
            # print(f"🏭 Vendor Name: {self.document_metadata.get('vendor_name', 'N/A')}")
            # print(f"📅 Submission Date: {self.document_metadata.get('submission_date', 'N/A')}")
            # print(f"🏷️ Domain Category: {self.document_metadata.get('domain_category', 'N/A')}")
            # print(f"⚙️ Service Category: {self.document_metadata.get('service_category', 'N/A')}")
            # print(f"💰 Revenue Range: {self.document_metadata.get('revenue_range', 'N/A')}")
            # print(f"🌍 Region: {self.document_metadata.get('region', 'N/A')}")
            # print(f"💵 Project Value: {self.document_metadata.get('project_value', 'N/A')}")
            # print(f"📜 Compliance Standard: {self.document_metadata.get('compliance_standard', 'N/A')}")
            # print(f"🔧 Equipments Used: {self.document_metadata.get('equipments_used', 'N/A')}")
            print()

        #print(f"\n{'='*80}")
        field_count = 10 if self.document_type == "RFI" else 11
        # print(f"🎯 ENHANCED SUMMARY WITH LLM INTEGRATION + AZURE TABLE STORAGE - {field_count} FIELDS ({self.document_type})")
        # print(f"📄 Document Type: {self.document_type} (Confidence: {self.document_type_info.get('confidence', 0):.1%})")
        # print(f"💾 Table Storage: ✅ Metadata stored in Azure Table Storage")
        
        if self.document_type == "RFI":
            # print(f"🚀 RFI ENHANCEMENT: DI text + First page (tables + images + text)")
            # print(f"📝 Text chunks: {len(text_chunks)} (RFI metadata only)")
            # print(f"📊 Table chunks: SKIPPED for RFI")
            # print(f"🖼️ Image chunks: SKIPPED for RFI") 
            # print(f"🎯 Index Target: Azure AI Search RFI Index")
            # print(f"💾 Table Storage: FileMetadataV2 + ComponentDataV2 tables")
            print()
        else:
            # print(f"📝 Text chunks: {len(text_chunks)} (with LLM metadata)")
            # print(f"📊 Table chunks: {len(table_chunks)} (with LLM metadata + verbalization)")
            # print(f"🖼️ Image chunks: {len(image_chunks)} (with LLM metadata + verbalization)")
            # print(f"🎯 Index Target: Azure AI Search RFP Index")
            # print(f"💾 Table Storage: FileMetadataV2 table")
            print()
            
        # print(f"🤖 LLM Metadata: ✅ Extracted {field_count} fields from {'enhanced' if self.document_type == 'RFI' else 'standard'} content")
        # print(f"🗂️ Section Mapping: ✅ Using separate SectionMapper for clean architecture")
        # print(f"💾 Azure Table Storage: ✅ Structured metadata storage enabled")
        
        if self.document_type == "RFI":
            # print(f"✅ RFI Fields: project_name, client, region, industry, prepared_date, field_type, voltage_class, contract_types, pricing, components")
            # print(f"🚀 Enhancement Active: First page comprehensive content extraction")
            # print(f"🗃️ Component Storage: Individual component records in ComponentDataV2 table")
            print()
        else:
            # print(f"✅ RFP Fields: project_title→file_name, vendor_name→author, domain_category→domain")
            # print(f"✅ Financial Fields: revenue_range→💰, region→🌍, project_value→💵")
            # print(f"✅ Technical Fields: compliance_standard→📜, equipments_used→🔧")
            print()
            
        # print(f"✅ FULL CONTENT PROCESSING: Enhanced extraction for RFI, standard for RFP")
        # print(f"✅ AZURE TABLE STORAGE: Metadata and components stored for structured querying")
        # print(f"{'='*80}")

        log_custom_event(
                 logger,
                 f"AZURE TABLE STORAGE: Metadata and components stored for structured querying",
                 level="info",
                )

        # Show storage and indexing paths
        if hasattr(self.storage, 'project_id') and hasattr(self.storage, 'document_type'):
            # print(f"💾 Blob Storage Path: {self.storage.project_id}/{self.storage.document_type}")
            # print(f"🗃️ Table Storage: FileMetadataV2 + {'ComponentDataV2 (for RFI)' if self.document_type == 'RFI' else 'N/A (RFP only uses file metadata)'}")
            # print(f"🎯 Search Index: {'Azure AI Search RFI Index' if self.document_type == 'RFI' else 'Azure AI Search RFP Index'}")
            # print(f"📊 Processing Method: {'Enhanced (DI + First Page)' if self.document_type == 'RFI' else 'Standard (DI Only)'}")
            print()