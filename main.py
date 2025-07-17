import os
from processors import AzureDocumentProcessor, ContentExtractor, FileHandler
from storage.local_storage import LocalStorage
from typing import Dict, Any

class DocumentProcessorMain:
    def __init__(self):
        self.azure_processor = AzureDocumentProcessor()
        self.content_extractor = ContentExtractor()
        self.file_handler = FileHandler()
        self.storage = LocalStorage()
    
    def process_document(self, uploaded_file, progress_callback=None) -> Dict[str, Any]:
        """Main processing pipeline with Azure Document Intelligence"""
        filename = uploaded_file.name
        
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
            
            # Extract all content
            extracted_content = self.content_extractor.extract_all_content(
                result, 
                filename, 
                client=client, 
                operation_id=operation_id
            )
            
            if progress_callback:
                progress_callback("💾 Saving extracted content...")
            
            # Finalize and return response
            return self._finalize_response(extracted_content, filename)
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error processing document: {str(e)}")
            raise e
    
    def _finalize_response(self, content: Dict, filename: str) -> Dict:
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