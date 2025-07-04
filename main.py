import os
from processors import AzureDocumentProcessor, ContentExtractor, FileHandler
from typing import Dict, Any

class DocumentProcessorMain:
    def __init__(self):
        self.azure_processor = AzureDocumentProcessor()
        self.content_extractor = ContentExtractor()
        self.file_handler = FileHandler()
    
    def process_document(self, uploaded_file, progress_callback=None) -> Dict[str, Any]:
        """Main processing pipeline"""
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
                progress_callback("📄 Analyzing document with Azure Document Intelligence...")
            
            # Analyze with Azure
            azure_result = self.azure_processor.analyze_document(file_bytes)
            
            if progress_callback:
                progress_callback("📝 Extracting text, tables, and images...")
            
            # Extract content (pass file_bytes for image extraction)
            extracted_content = self.content_extractor.extract_all_content(azure_result, filename, file_bytes)
            
            if progress_callback:
                progress_callback(f"✅ Processing complete! Found {extracted_content['stats']['text_count']} text chunks, {extracted_content['stats']['table_count']} tables, {extracted_content['stats']['image_count']} images")
            
            # Add metadata
            extracted_content.update({
                "filename": filename,
                "file_extension": self.file_handler.get_file_extension(filename),
                "processing_method": "Azure Document Intelligence"
            })
            
            return extracted_content
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error processing document: {str(e)}")
            raise e

# Global instance for use in Streamlit
document_processor = DocumentProcessorMain()