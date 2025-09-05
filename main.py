


import os
from processors import AzureDocumentProcessor, ContentExtractor, FileHandler
# from storage.local_storage import LocalStorage
from storage.storage_factory import get_storage_instance
from typing import Dict, Any
import asyncio

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
            # self.storage = LocalStorage()
            self.storage = get_storage_instance() 
    
    def process_document(self, uploaded_file, progress_callback=None) -> Dict[str, Any]:
        with tracer.start_as_current_span("process_document_fn") as span:
            """Main processing pipeline with Azure Document Intelligence"""
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
                
                # Extract all content - NOW WITH ASYNC SUPPORT
                extracted_content = asyncio.run(self.content_extractor.extract_all_content(
                    result,
                    filename,
                    client=client,
                    operation_id=operation_id
                ))

                if progress_callback:
                    progress_callback("💾 Saving extracted content...")
                
                # Finalize and return response
                return self._finalize_response(extracted_content, filename)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"❌ Error processing document: {str(e)}")
                raise e
    
    def _finalize_response(self, content: Dict, filename: str) -> Dict:
        with tracer.start_as_current_span("_finalize_response_fn") as span:
            """Finalize response with metadata"""
            
            # Add processing metadata
            content.update({
                "filename": filename,
                "file_extension": self.file_handler.get_file_extension(filename),
                "processing_method": "azure_document_intelligence"
            })
            
            # Calculate basic statistics if not already present
            if "stats" not in content:
                content["stats"] = {
                    "text_count": len(content.get("text_chunks", [])),
                    "table_count": len(content.get("tables", [])),
                    "image_count": len(content.get("images", []))
                }
            
            return content

# Global instance for use in Streamlit
document_processor = DocumentProcessorMain()