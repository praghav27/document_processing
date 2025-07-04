import os
from processors import AzureDocumentProcessor, ContentExtractor, FileHandler
from typing import Dict, Any

class DocumentProcessorMain:
    def __init__(self):
        self.azure_processor = AzureDocumentProcessor()
        self.content_extractor = ContentExtractor()
        self.file_handler = FileHandler()
    
    def process_document(self, uploaded_file, progress_callback=None) -> Dict[str, Any]:
        """Main processing pipeline using Azure Document Intelligence with image extraction"""
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
                progress_callback("📄 Analyzing document with Azure Document Intelligence Layout Model (with figures)...")
            
            # Analyze with Azure DI (returns result, client, and operation_id for image extraction)
            result, client, operation_id = self.azure_processor.analyze_document(file_bytes, filename)
            
            if progress_callback:
                progress_callback("📝 Extracting text content from paragraphs...")
            
            if progress_callback:
                progress_callback("📊 Extracting tables and converting to CSV...")
            
            if progress_callback:
                progress_callback("🖼️ Extracting figures and downloading images...")
            
            # Extract all content using Azure DI with image extraction
            extracted_content = self.content_extractor.extract_all_content(
                result, 
                filename, 
                client=client, 
                operation_id=operation_id
            )
            
            if progress_callback:
                progress_callback("💾 Saving content to local storage...")
            
            stats = extracted_content['stats']
            
            # Create detailed completion message
            completion_message = f"✅ Processing complete! Found:"
            completion_message += f" {stats['text_count']} text chunks,"
            completion_message += f" {stats['table_count']} tables,"
            completion_message += f" {stats['image_count']} figures"
            
            # Count actual images vs text-only figures
            actual_images = sum(1 for img in extracted_content.get('images', []) if img.get('image_path'))
            if actual_images > 0:
                completion_message += f" ({actual_images} with actual images)"
            
            if progress_callback:
                progress_callback(completion_message)
            
            # Add metadata
            extracted_content.update({
                "filename": filename,
                "file_extension": self.file_handler.get_file_extension(filename),
                "processing_method": "Azure Document Intelligence Layout Model with Figure Extraction",
                "supports_image_extraction": True,
                "actual_images_extracted": actual_images
            })
            
            return extracted_content
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error processing document: {str(e)}")
            raise e

# Global instance for use in Streamlit
document_processor = DocumentProcessorMain()