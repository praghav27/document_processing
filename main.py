import os
from processors import AzureDocumentProcessor, ContentExtractor, FileHandler
from chunking import StructureAwareChunker
from storage.local_storage import LocalStorage
from typing import Dict, Any

class DocumentProcessorMain:
    def __init__(self):
        self.azure_processor = AzureDocumentProcessor()
        self.content_extractor = ContentExtractor()
        self.file_handler = FileHandler()
        self.structure_chunker = StructureAwareChunker()
        self.storage = LocalStorage()
    
    def process_document(self, uploaded_file, progress_callback=None, use_structure_aware=True) -> Dict[str, Any]:
        """Main processing pipeline with optional structure-aware chunking"""
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
            
            # Extract basic content
            extracted_content = self.content_extractor.extract_all_content(
                result, 
                filename, 
                client=client, 
                operation_id=operation_id
            )
            
            if use_structure_aware:
                if progress_callback:
                    progress_callback("🧠 Performing LLM-based structure analysis...")
                
                # Test Azure OpenAI connection
                if not self._test_llm_connection():
                    if progress_callback:
                        progress_callback("⚠️ LLM connection failed, using basic chunking...")
                    use_structure_aware = False
                
                if use_structure_aware:
                    try:
                        # Create document metadata for structure-aware chunking
                        document_metadata = self._create_document_metadata(filename, extracted_content)
                        
                        if progress_callback:
                            progress_callback("🗺️ Mapping multimodal content to sections...")
                        
                        # Perform structure-aware chunking
                        chunking_result = self.structure_chunker.create_structure_based_chunks(
                            raw_text=extracted_content.get("raw_text", ""),
                            tables=extracted_content.get("tables", []),
                            images=extracted_content.get("images", []),
                            document_metadata=document_metadata
                        )
                        
                        if progress_callback:
                            progress_callback("💾 Saving structure-aware chunks...")
                        
                        # Save structure-aware chunks
                        base_filename = os.path.splitext(filename)[0]
                        chunks_file = self.storage.save_structure_aware_chunks(
                            chunking_result.get("chunks", []), 
                            base_filename
                        )
                        
                        # Save document structure
                        structure_file = self.storage.save_document_structure(
                            chunking_result.get("document_structure", {}),
                            base_filename
                        )
                        
                        # Save processing metadata
                        processing_metadata = {
                            "processing_method": "structure_aware_llm",
                            "statistics": chunking_result.get("statistics", {}),
                            "metadata_summary": chunking_result.get("metadata_summary", {}),
                            "processing_details": chunking_result.get("processing_details", {})
                        }
                        
                        metadata_file = self.storage.save_processing_metadata(
                            processing_metadata,
                            base_filename
                        )
                        
                        # Create enhanced response
                        enhanced_content = dict(extracted_content)
                        enhanced_content.update({
                            "structure_aware_chunks": chunking_result.get("chunks", []),
                            "document_structure": chunking_result.get("document_structure", {}),
                            "content_mapping": chunking_result.get("content_mapping", {}),
                            "chunking_statistics": chunking_result.get("statistics", {}),
                            "metadata_summary": chunking_result.get("metadata_summary", {}),
                            "chunks_file_path": chunks_file,
                            "structure_file_path": structure_file,
                            "metadata_file_path": metadata_file,
                            "processing_method": "structure_aware_llm"
                        })
                        
                        if progress_callback:
                            stats = chunking_result.get("statistics", {})
                            completion_message = f"✅ Structure-aware processing complete!"
                            completion_message += f" Created {stats.get('total_chunks', 0)} intelligent chunks"
                            completion_message += f" with {stats.get('multimodal_integration', {}).get('tables_integrated', 0)} tables"
                            completion_message += f" and {stats.get('multimodal_integration', {}).get('images_integrated', 0)} images integrated."
                            progress_callback(completion_message)
                        
                        return self._finalize_response(enhanced_content, filename, "structure_aware_llm")
                        
                    except Exception as e:
                        print(f"❌ Structure-aware chunking failed: {e}")
                        if progress_callback:
                            progress_callback(f"⚠️ Structure analysis failed ({str(e)}), using basic chunking...")
                        use_structure_aware = False
            
            # Fallback to basic chunking
            if not use_structure_aware:
                if progress_callback:
                    progress_callback("💾 Saving basic content...")
                
                return self._finalize_response(extracted_content, filename, "basic_azure_di")
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error processing document: {str(e)}")
            raise e
    
    def _test_llm_connection(self) -> bool:
        """Test Azure OpenAI connection"""
        try:
            from llm_processing import AzureOpenAIClient
            client = AzureOpenAIClient()
            return client.test_connection()
        except Exception as e:
            print(f"LLM connection test failed: {e}")
            return False
    
    def _create_document_metadata(self, filename: str, extracted_content: Dict) -> Dict:
        """Create document metadata for structure-aware chunking"""
        
        base_filename = os.path.splitext(filename)[0]
        
        # Extract basic document information
        document_metadata = {
            "document_id": base_filename,
            "document_title": self._extract_document_title(extracted_content.get("raw_text", "")),
            "filename": filename,
            "file_extension": os.path.splitext(filename)[1].lower()
        }
        
        # Try to extract RFP-specific metadata from content
        raw_text = extracted_content.get("raw_text", "")
        rfp_metadata = self._extract_rfp_metadata(raw_text)
        document_metadata.update(rfp_metadata)
        
        return document_metadata
    
    def _extract_document_title(self, raw_text: str) -> str:
        """Extract document title from raw text"""
        
        if not raw_text:
            return "Unknown Document"
        
        # Look for title in first few lines
        lines = raw_text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                # Check if line looks like a title
                if (line.isupper() or 
                    (line[0].isupper() and not line.endswith('.')) or
                    ':' in line):
                    return line
        
        # Fallback: use first substantial line
        for line in lines:
            line = line.strip()
            if len(line) > 20:
                return line[:100] + "..." if len(line) > 100 else line
        
        return "Unknown Document"
    
    def _extract_rfp_metadata(self, raw_text: str) -> Dict:
        """Extract RFP-specific metadata from document text"""
        
        import re
        from datetime import datetime
        
        metadata = {
            "client_name": "",
            "vendor_name": "",
            "project_site": "",
            "submission_date": "",
            "project_value": 0.0
        }
        
        if not raw_text:
            return metadata
        
        # Look for common RFP patterns in first 2000 characters
        text_sample = raw_text[:2000].lower()
        
        # Extract client/company names (simple patterns)
        client_patterns = [
            r'presented to[:\s]+([^\n]+)',
            r'client[:\s]+([^\n]+)',
            r'for[:\s]+([A-Z][^\n]+(?:inc|corp|ltd|llc))',
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                metadata["client_name"] = match.group(1).strip()[:50]
                break
        
        # Extract vendor/proposer name
        vendor_patterns = [
            r'submitted by[:\s]+([^\n]+)',
            r'prepared by[:\s]+([^\n]+)',
            r'([A-Z][^\n]+(?:tech|engineering|consulting))',
        ]
        
        for pattern in vendor_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                metadata["vendor_name"] = match.group(1).strip()[:50]
                break
        
        # Extract project site/location
        location_patterns = [
            r'project[:\s]+([^\n]+)',
            r'site[:\s]+([^\n]+)',
            r'location[:\s]+([^\n]+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 5 and len(location) < 100:
                    metadata["project_site"] = location
                    break
        
        # Extract dates
        date_patterns = [
            r'date[:\s]+([^\n]+)',
            r'submitted[:\s]+([^\n]*\d{4}[^\n]*)',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_sample, re.IGNORECASE)
            for match in matches:
                try:
                    # Try to parse as date
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    
                    # Simple date extraction
                    if re.search(r'\d{4}', match):
                        metadata["submission_date"] = match.strip()[:20]
                        break
                except:
                    continue
        
        # Extract project value (simple pattern)
        value_patterns = [
            r'\$[\d,]+(?:\.\d{2})?',
            r'budget[:\s]+\$?([\d,]+)',
            r'value[:\s]+\$?([\d,]+)',
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, text_sample, re.IGNORECASE)
            for match in matches:
                try:
                    # Extract numeric value
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    
                    numeric_value = re.sub(r'[^\d.]', '', str(match))
                    if numeric_value:
                        metadata["project_value"] = float(numeric_value)
                        break
                except:
                    continue
        
        return metadata
    
    def _finalize_response(self, content: Dict, filename: str, processing_method: str) -> Dict:
        """Finalize response with metadata"""
        
        # Add processing metadata
        content.update({
            "filename": filename,
            "file_extension": self.file_handler.get_file_extension(filename),
            "processing_method": processing_method,
            "supports_structure_aware": processing_method == "structure_aware_llm"
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