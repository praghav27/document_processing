import os
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from processors import AzureDocumentProcessor, ContentExtractor, FileHandler
from storage.storage_factory import get_storage_instance
from typing import Dict, Any, List
from datetime import datetime

from application_logging.custom_logging_to_app_insights import configure_logger, log_step, log_exception
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class DocumentProcessorMain:
    def __init__(self):
        with tracer.start_as_current_span("main_init_fn") as span:
            self.azure_processor = AzureDocumentProcessor()
            self.content_extractor = ContentExtractor()
            self.file_handler = FileHandler()
            self.storage = get_storage_instance() 
            
            # REDUCED Configuration for parallel processing to prevent rate limiting
            self.max_concurrent_documents = 3  # REDUCED from 8 to 3
            self.max_concurrent_processing = 2  # REDUCED from 4 to 2
            self.max_concurrent_storage_ops = 3  # REDUCED from 8 to 3
            
            # ADD: Rate limiting delays
            self.document_processing_delay = 2.0  # 2 seconds between document starts
            self.retry_attempts = 3
            self.retry_delay = 5.0  # 5 seconds between retries
    
    def process_document(self, uploaded_file, progress_callback=None) -> Dict[str, Any]:
        with tracer.start_as_current_span("process_document_fn") as span:
            """Main processing pipeline with Azure Document Intelligence (Single file - existing)"""
            filename = uploaded_file.name
            base_filename = os.path.splitext(filename)[0]
            
            try:
                # Validate file
                if not self.file_handler.validate_file(filename):
                    raise ValueError(f"Unsupported file format: {self.file_handler.get_file_extension(filename)}")
                
                if progress_callback:
                    progress_callback("🔍 Converting file to bytes...")
                
                # Convert to bytes
                file_bytes = self.file_handler.process_file(uploaded_file)
                
                if progress_callback:
                    progress_callback("📄 Analyzing document with Azure Document Intelligence Layout Model...")
                
                # Analyze with Azure DI
                result, client, operation_id = self.azure_processor.analyze_document(file_bytes, filename)
                
                if progress_callback:
                    progress_callback("📝 Extracting text, tables, and images...")
                    progress_callback("🤖 Extracting metadata with enhanced LLM processing...")
                    progress_callback("💾 Storing metadata in Azure Table Storage...")
                
                # Extract all content - NOW WITH ASYNC SUPPORT + AZURE TABLE STORAGE
                extracted_content = asyncio.run(self.content_extractor.extract_all_content(
                    result,
                    filename,
                    client=client,
                    operation_id=operation_id
                ))

                if progress_callback:
                    progress_callback("💾 Saving extracted content...")
                    progress_callback("✅ Azure Table Storage operations completed...")
                
                # Finalize and return response
                return self._finalize_response(extracted_content, filename)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"❌ Error processing document: {str(e)}")
                raise e

    async def process_multiple_documents_rfi(self, uploaded_files: List) -> List[Dict[str, Any]]:
        """
        ENHANCED: Process multiple RFI documents with BETTER rate limiting and error handling
        """
        start_time = time.time()
        print(f"\n{'='*80}")
        print(f"🚀 ENHANCED PARALLEL RFI PROCESSING FOR {len(uploaded_files)} DOCUMENTS")
        print(f"🗃️ Azure Table Storage: ENABLED - Metadata and components will be stored")
        print(f"🔧 Rate Limiting: ENABLED - {self.max_concurrent_documents} concurrent docs")
        print(f"{'='*80}")
        
        # Phase 1: Parallel Azure Document Intelligence Processing with BETTER rate limiting
        print(f"📄 Phase 1: Parallel Azure Document Intelligence processing with rate limiting...")
        phase1_start = time.time()
        
        # ENHANCED: Create semaphore with REDUCED concurrency
        di_semaphore = asyncio.Semaphore(self.max_concurrent_documents)
        
        async def process_single_document_di_with_retry(uploaded_file, file_index):
            """Process single document through Azure DI with retry logic and delays"""
            
            # ADD: Staggered start delay to prevent overwhelming Azure services
            await asyncio.sleep(file_index * self.document_processing_delay)
            
            async with di_semaphore:
                for attempt in range(self.retry_attempts):
                    try:
                        filename = uploaded_file.name
                        print(f"📄 Processing ({attempt + 1}/{self.retry_attempts}): {filename}")
                        
                        # Validate file
                        if not self.file_handler.validate_file(filename):
                            return {
                                'filename': filename,
                                'success': False,
                                'error': f"Unsupported file format: {self.file_handler.get_file_extension(filename)}",
                                'uploaded_file': uploaded_file
                            }
                        
                        # Convert to bytes in thread pool to avoid blocking
                        loop = asyncio.get_event_loop()
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            file_bytes = await loop.run_in_executor(
                                executor, 
                                self.file_handler.process_file, 
                                uploaded_file
                            )
                        
                        print(f"📄 Analyzing {filename} with Azure Document Intelligence...")
                        
                        # ENHANCED: Add timeout and retry for Azure DI
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            result, client, operation_id = await asyncio.wait_for(
                                loop.run_in_executor(
                                    executor,
                                    self.azure_processor.analyze_document,
                                    file_bytes,
                                    filename
                                ),
                                timeout=120.0  # 2 minute timeout per document
                            )
                        
                        return {
                            'filename': filename,
                            'uploaded_file': uploaded_file,
                            'azure_result': result,
                            'client': client,
                            'operation_id': operation_id,
                            'success': True
                        }
                        
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout on attempt {attempt + 1} for {uploaded_file.name}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            return {
                                'filename': uploaded_file.name,
                                'uploaded_file': uploaded_file,
                                'error': 'Timeout after multiple attempts',
                                'success': False
                            }
                    except Exception as e:
                        print(f"❌ Error on attempt {attempt + 1} for {uploaded_file.name}: {str(e)}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            return {
                                'filename': uploaded_file.name,
                                'uploaded_file': uploaded_file,
                                'error': str(e),
                                'success': False
                            }
        
        # Execute all Azure DI processing in parallel with staggered starts
        di_tasks = [
            process_single_document_di_with_retry(file, index) 
            for index, file in enumerate(uploaded_files)
        ]
        di_results = await asyncio.gather(*di_tasks, return_exceptions=True)
        
        phase1_time = time.time() - phase1_start
        print(f"✅ Phase 1 completed in {phase1_time:.2f}s")
        
        # Phase 2: Parallel Content Extraction with BETTER rate limiting
        print(f"📝 Phase 2: Parallel content extraction with enhanced rate limiting...")
        phase2_start = time.time()
        
        # ENHANCED: Create semaphore with REDUCED concurrency for content extraction
        extraction_semaphore = asyncio.Semaphore(self.max_concurrent_processing)
        
        async def extract_content_parallel_with_retry(di_result, extract_index):
            """Extract content with retry logic and delays"""
            if not di_result.get('success'):
                return di_result
                
            # ADD: Staggered start delay for content extraction
            await asyncio.sleep(extract_index * 1.0)  # 1 second delay between extractions
                
            async with extraction_semaphore:
                for attempt in range(self.retry_attempts):
                    try:
                        filename = di_result['filename']
                        result = di_result['azure_result']
                        client = di_result['client']
                        operation_id = di_result['operation_id']
                        
                        print(f"📝 Extracting content from {filename} (attempt {attempt + 1})...")
                        print(f"💾 Storing metadata in Azure Table Storage for {filename}...")
                        
                        # ENHANCED: Add timeout for content extraction
                        extracted_content = await asyncio.wait_for(
                            self.content_extractor.extract_all_content(
                                result,
                                filename,
                                client=client,
                                operation_id=operation_id
                            ),
                            timeout=600.0  # 3 minute timeout per extraction
                        )
                        
                        print(f"✅ Successfully processed {filename}")
                        
                        # Check if table storage was successful
                        table_storage_enabled = extracted_content.get('enhancement_info', {}).get('table_storage_enabled', False)
                        
                        # Return structured result following your exact format
                        di_result.update({
                            'extracted_content': extracted_content,
                            'chunks': extracted_content.get('text_chunks', []),
                            'metadata': extracted_content.get('document_metadata', {}),
                            'document_type': extracted_content.get('document_type', 'RFI'),
                            'project_id': extracted_content.get('project_id', 'unknown'),
                            'stats': extracted_content.get('stats', {}),
                            'enhancement_info': extracted_content.get('enhancement_info', {}),
                            'table_storage': {
                                'stored': table_storage_enabled,
                                'file_metadata': table_storage_enabled,
                                'component_data': table_storage_enabled and extracted_content.get('document_type') == 'RFI'
                            }
                        })
                        
                        return di_result
                        
                    except asyncio.TimeoutError:
                        print(f"⏰ Content extraction timeout on attempt {attempt + 1} for {di_result['filename']}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            di_result.update({
                                'error': 'Content extraction timeout after multiple attempts',
                                'success': False,
                                'table_storage': {'stored': False, 'error': 'Timeout'}
                            })
                            return di_result
                    except Exception as e:
                        print(f"❌ Error extracting content from {di_result['filename']} on attempt {attempt + 1}: {str(e)}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            di_result.update({
                                'error': str(e),
                                'success': False,
                                'table_storage': {'stored': False, 'error': str(e)}
                            })
                            return di_result
        
        # Execute all content extraction in parallel with staggered starts
        successful_di_results = [r for r in di_results if isinstance(r, dict) and r.get('success')]
        extraction_tasks = [
            extract_content_parallel_with_retry(result, index) 
            for index, result in enumerate(successful_di_results)
        ]
        processed_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        phase2_time = time.time() - phase2_start
        print(f"✅ Phase 2 completed in {phase2_time:.2f}s")
        
        # Combine results and handle failures
        final_results = []
        successful_results = [r for r in processed_results if isinstance(r, dict) and r.get('success')]
        failed_di_results = [r for r in di_results if isinstance(r, dict) and not r.get('success')]
        failed_extraction_results = [r for r in processed_results if isinstance(r, dict) and not r.get('success')]
        
        # Add successful results in your exact format
        # for result in successful_results:
        #     final_results.append({
        #         'filename': result['filename'],
        #         'success': True,
        #         'error': None,
        #         'chunks': result.get('chunks', []),
        #         'metadata': result.get('metadata', {}),
        #         'document_type': result.get('document_type', 'RFI'),
        #         'project_id': result.get('project_id', 'unknown'),
        #         'stats': result.get('stats', {}),
        #         'enhancement_info': result.get('enhancement_info', {}),
        #         'table_storage': result.get('table_storage', {}),
        #         'processing_time': datetime.now().isoformat()
        #     })

        for result in successful_results:
            chunks = result.get('chunks', [])
            # Now chunks is a list where each chunk represents one component
            final_results.append({
                'filename': result['filename'],
                'success': True,
                'error': None,
                'chunks': chunks,  # This now contains separate component chunks
                'component_count': len(chunks),  # NEW: Number of components found
                'disciplines': list(set(chunk.get('discipline', 'unknown') for chunk in chunks)),  # NEW: List of disciplines
                'metadata': result.get('metadata', {}),
                'document_type': result.get('document_type', 'RFI'),
                'project_id': result.get('project_id', 'unknown'),
                'stats': result.get('stats', {}),
                'enhancement_info': result.get('enhancement_info', {}),
                'table_storage': result.get('table_storage', {}),
                'processing_time': datetime.now().isoformat()
            })
        
        # Add failed results
        for failed in failed_di_results + failed_extraction_results:
            final_results.append({
                'filename': failed['filename'],
                'success': False,
                'error': failed.get('error', 'Unknown error'),
                'chunks': [],
                'metadata': {},
                'table_storage': {'stored': False, 'error': failed.get('error', 'Processing failed')},
                'processing_time': datetime.now().isoformat()
            })
        
        # Calculate statistics (your exact logic)
        successful_chunks = []
        for result in final_results:
            if result.get('success', False) and result.get('chunks'):
                successful_chunks.extend(result['chunks'])
        
        table_storage_stats = {
            'successful': len([r for r in final_results if r.get('table_storage', {}).get('stored', False)]),
            'failed': len([r for r in final_results if not r.get('table_storage', {}).get('stored', False)])
        }
        
        # Print summary (your exact format)
        successful_count = len([r for r in final_results if r.get('success', False)])
        failed_count = len(final_results) - successful_count
        
        total_time = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"📊 ENHANCED PARALLEL RFI PROCESSING + AZURE TABLE STORAGE SUMMARY")
        print(f"{'='*80}")
        print(f"⏱️ Phase 1 (Parallel Azure DI with Rate Limiting): {phase1_time:.2f}s")
        print(f"⏱️ Phase 2 (Parallel Content Extraction with Rate Limiting): {phase2_time:.2f}s")
        print(f"⏱️ Total Processing Time: {total_time:.2f}s")
        print(f"✅ Successfully processed: {successful_count}/{len(uploaded_files)} documents")
        print(f"❌ Failed to process: {failed_count} documents")
        print(f"📋 Total chunks created: {len(successful_chunks)}")
        print(f"🗃️ Azure Table Storage:")
        print(f"   ✅ Successful metadata storage: {table_storage_stats['successful']} documents")
        print(f"   ❌ Failed metadata storage: {table_storage_stats['failed']} documents")
        print(f"🔧 Rate Limiting: Applied - Max {self.max_concurrent_documents} concurrent documents")
        
        # Print all chunks to terminal (your exact logic)
        if successful_chunks:
            self._print_all_chunks_to_terminal(successful_chunks)
        
        return final_results

    async def _process_single_rfi_document_async(self, uploaded_file) -> Dict[str, Any]:
        """
        Process a single RFI document asynchronously with Azure Table Storage integration
        (This method is kept for compatibility but not used in the optimized flow)
        """
        filename = uploaded_file.name
        
        try:
            print(f"🔍 Processing: {filename}")
            
            # Validate file
            if not self.file_handler.validate_file(filename):
                return {
                    'filename': filename,
                    'success': False,
                    'error': f"Unsupported file format: {self.file_handler.get_file_extension(filename)}",
                    'chunks': [],
                    'metadata': {},
                    'table_storage': {'stored': False, 'error': 'Invalid file format'}
                }
            
            # Convert to bytes
            file_bytes = self.file_handler.process_file(uploaded_file)
            print(f"📄 Analyzing {filename} with Azure Document Intelligence...")
            
            # Analyze with Azure DI
            result, client, operation_id = self.azure_processor.analyze_document(file_bytes, filename)
            
            print(f"📝 Extracting content from {filename}...")
            print(f"💾 Storing metadata in Azure Table Storage for {filename}...")
            
            # Extract all content using the enhanced content extractor WITH TABLE STORAGE
            extracted_content = await self.content_extractor.extract_all_content(
                result,
                filename,
                client=client,
                operation_id=operation_id
            )
            
            print(f"✅ Successfully processed {filename}")
            
            # Check if table storage was successful
            table_storage_enabled = extracted_content.get('enhancement_info', {}).get('table_storage_enabled', False)
            
            # Return structured result
            return {
                'filename': filename,
                'success': True,
                'error': None,
                'chunks': extracted_content.get('text_chunks', []),
                'metadata': extracted_content.get('document_metadata', {}),
                'document_type': extracted_content.get('document_type', 'RFI'),
                'project_id': extracted_content.get('project_id', 'unknown'),
                'stats': extracted_content.get('stats', {}),
                'enhancement_info': extracted_content.get('enhancement_info', {}),
                'table_storage': {
                    'stored': table_storage_enabled,
                    'file_metadata': table_storage_enabled,
                    'component_data': table_storage_enabled and extracted_content.get('document_type') == 'RFI'
                },
                'processing_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            return {
                'filename': filename,
                'success': False,
                'error': str(e),
                'chunks': [],
                'metadata': {},
                'table_storage': {'stored': False, 'error': str(e)},
                'processing_time': datetime.now().isoformat()
            }

    





    def _print_all_chunks_to_terminal(self, all_chunks: List[Dict]):
        """
        Print all chunks from all documents to terminal in a formatted way (Enhanced with Table Storage info)
        (Your exact existing method - NO CHANGES)
        """
        print(f"\n{'='*100}")
        print(f"📋 ALL RFI CHUNKS OUTPUT - ENHANCED COMPONENT FORMAT + AZURE TABLE STORAGE")
        print(f"{'='*100}")
        print(f"Total chunks across all documents: {len(all_chunks)}")
        print(f"🗃️ All metadata and components stored in Azure Table Storage")
        
        # Group chunks by document/project
        chunks_by_project = {}
        for chunk in all_chunks:
            project_id = chunk.get('project_id', 'unknown')
            if project_id not in chunks_by_project:
                chunks_by_project[project_id] = []
            chunks_by_project[project_id].append(chunk)
        
        # Print chunks grouped by document
        for project_id, chunks in chunks_by_project.items():
            print(f"\n{'-'*80}")
            print(f"📄 PROJECT: {project_id} ({len(chunks)} chunks)")
            print(f"🗃️ Table Storage: FileMetadataV2 + ComponentDataV2 records created")
            print(f"{'-'*80}")
            
            for i, chunk in enumerate(chunks, 1):
                # print(f"\nCHUNK {i}:")
                # print(f"  📋 Chunk ID: {chunk.get('chunk_id', 'N/A')}")
                # print(f"  📂 Project ID: {chunk.get('project_id', 'N/A')}")
                # print(f"  🏢 Project Name: {chunk.get('project_name', 'N/A')}")
                # print(f"  🏭 Client: {chunk.get('client', 'N/A')}")
                # print(f"  🌍 Industry: {chunk.get('industry', 'N/A')}")
                # print(f"  📍 Region: {chunk.get('region', 'N/A')}")
                # print(f"  📅 Prepared Date: {chunk.get('prepared_date', 'N/A')}")
                # print(f"  🏞️ Field Type: {chunk.get('field_type', 'N/A')}")
                # print(f"  🔌 Voltage Class: {chunk.get('voltage_class', 'N/A')}")
                # print(f"  📃 Contract Types: {chunk.get('contract_types', 'N/A')}")
                # print(f"  💰 Pricing: {chunk.get('pricing', 'N/A')}")
                
                # Print components (enhanced format with specific fields)
                components = chunk.get('components', {})
                if components:
                    print(f"  ⚙️ Components ({len(components)}) - Stored in ComponentDataV2:")
                    for comp_code, comp_data in components.items():
                        print(f"    • {comp_code} Component:")
                        print(f"      - Scope of Work: {len(comp_data.get('scope_of_work', ''))} chars")
                        print(f"      - Required Activities: {len(comp_data.get('required_activities', ''))} chars")
                        
                        # Print component-specific fields
                        for field_name, field_value in comp_data.items():
                            if field_name not in ['scope_of_work', 'required_activities']:
                                field_preview = (field_value[:50] + "...") if len(str(field_value)) > 50 else field_value
                                print(f"      - {field_name}: {field_preview}")
                else:
                    print(f"  ⚙️ Components: None identified")
                
                # print(f"  🕒 Created: {chunk.get('metadata', {}).get('created_at', 'N/A')}")
                # print(f"  🗃️ Table Storage: Metadata and component records created")
        
        print(f"\n{'='*100}")
        print(f"✅ TERMINAL OUTPUT COMPLETE - All {len(all_chunks)} chunks displayed")
        print(f"🗃️ AZURE TABLE STORAGE - All metadata and components stored for structured querying")
        print(f"📊 Query Tables: FileMetadataV2 (document metadata), ComponentDataV2 (component details)")
        print(f"{'='*100}")
    
    def _finalize_response(self, content: Dict, filename: str) -> Dict:
        with tracer.start_as_current_span("_finalize_response_fn") as span:
            """Finalize response with metadata (existing method - enhanced with table storage info)"""
            
            # Add processing metadata
            content.update({
                "filename": filename,
                "file_extension": self.file_handler.get_file_extension(filename),
                "processing_method": "azure_document_intelligence_with_table_storage"
            })
            
            # Calculate basic statistics if not already present
            if "stats" not in content:
                content["stats"] = {
                    "text_count": len(content.get("text_chunks", [])),
                    "table_count": len(content.get("tables", [])),
                    "image_count": len(content.get("images", []))
                }
            
            # Add table storage information
            content["table_storage_info"] = {
                "enabled": content.get("enhancement_info", {}).get("table_storage_enabled", False),
                "file_metadata_stored": True,  # Always true if processing succeeded
                "component_data_stored": content.get("document_type") == "RFI",  # Only for RFI documents
                "tables_used": ["FileMetadataV2"] + (["ComponentDataV2"] if content.get("document_type") == "RFI" else [])
            }
            
            return content

# Global instance for use in Streamlit
document_processor = DocumentProcessorMain()