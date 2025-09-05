import os
import json
import uuid
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
from azure.storage.blob import BlobServiceClient
from config import (
    AZURE_STORAGE_CONNECTION_STRING, 
    INPUT_CONTAINER_NAME, 
    OUTPUT_CONTAINER_NAME
)
from typing import List, Dict

class AzureBlobStorage:
    """Handle blob storage of extracted content with UUID organization"""
    
    # _shared_uuid = None  # used for shared UUID
    
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        self.input_container = INPUT_CONTAINER_NAME
        self.output_container = OUTPUT_CONTAINER_NAME
        
        # # Use shared UUID if exists, otherwise create new one
        # if AzureBlobStorage._shared_uuid is None:
        #     AzureBlobStorage._shared_uuid = str(uuid.uuid4())
        #     print(f"🔵 Azure Blob Storage initialized with NEW UUID: {AzureBlobStorage._shared_uuid}")
        # else:
        #     print(f"🔵 Azure Blob Storage reusing SHARED UUID: {AzureBlobStorage._shared_uuid}")
            
        # self.document_uuid = AzureBlobStorage._shared_uuid

        self.project_id = None  
        self.document_type = None 
    
    def set_project_context(self, filename: str, document_type: str):
        """Set project ID and document type from filename"""
        # Extract first 15 characters as project_id
        self.project_id = filename[:15] if filename else "unknown"
        
        # Set document type (rfp_request or rfp_response)
        self.document_type = document_type.lower()
        print(f"📁 Storage context set: {self.project_id}/{self.document_type}")

    def _ensure_project_context(self):
        """Ensure project context is set before operations"""
        if not self.project_id or not self.document_type:
            raise ValueError("Project context not set. Call set_project_context() first.")

    def list_input_documents(self) -> List[str]:
        """List all PDF documents in input container"""
        try:
            container_client = self.blob_service_client.get_container_client(self.input_container)
            blobs = container_client.list_blobs()
            pdf_files = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
            return pdf_files
        except Exception as e:
            print(f"❌ Error listing documents: {e}")
            return []
    
    def read_document_bytes(self, blob_name: str) -> bytes:
        """Read document bytes from input container"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.input_container, 
                blob=blob_name
            )
            return blob_client.download_blob().readall()
        except Exception as e:
            print(f"❌ Error reading document {blob_name}: {e}")
            raise e
    
    def save_table(self, df: pd.DataFrame, filename: str, table_index: int) -> str:
        """Save table as CSV to blob"""
        self._ensure_project_context()
        csv_filename = f"{filename}_table_{table_index}.csv"
        # blob_path = f"{self.document_uuid}/tables/{csv_filename}"
        blob_path = f"{self.project_id}/{self.document_type}/tables/{csv_filename}"
        
        try:
            csv_data = df.to_csv(index=False)
            blob_client = self.blob_service_client.get_blob_client(
                container=self.output_container, 
                blob=blob_path
            )
            blob_client.upload_blob(csv_data, overwrite=True)
            print(f"💾 Saved table {table_index} to blob: {blob_path}")
            return blob_path
        except Exception as e:
            print(f"❌ Error saving table {table_index}: {e}")
            return None
    
    def save_figure_image_bytes(self, image_bytes: bytes, filename: str, figure_index: int) -> str:
        """Save figure image from raw bytes to blob"""
        self._ensure_project_context()
        try:
            img_filename = f"{filename}_figure_{figure_index}.png"
            # blob_path = f"{self.document_uuid}/images/{img_filename}"
            blob_path = f"{self.project_id}/{self.document_type}/images/{img_filename}"
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.output_container, 
                blob=blob_path
            )
            blob_client.upload_blob(image_bytes, overwrite=True)
            print(f"💾 Saved figure image to blob: {blob_path}")
            return blob_path
        except Exception as e:
            print(f"❌ Error saving figure image {figure_index}: {e}")
            return None
    
    def save_figure_text(self, text_content: str, filename: str, figure_index: int) -> str:
        """Save figure text content to blob"""
        self._ensure_project_context()
        txt_filename = f"{filename}_figure_{figure_index}.txt"
        # blob_path = f"{self.document_uuid}/images/{txt_filename}"
        blob_path = f"{self.project_id}/{self.document_type}/images/{txt_filename}"
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.output_container, 
                blob=blob_path
            )
            blob_client.upload_blob(text_content, overwrite=True)
            print(f"💾 Saved figure text to blob: {blob_path}")
            return blob_path
        except Exception as e:
            print(f"❌ Error saving figure text {figure_index}: {e}")
            return None
    
    # def save_text_chunks(self, text_chunks: List[Dict], filename: str) -> str:
        """Save text chunks as JSON to blob"""
        json_filename = f"{filename}_text_chunks.json"
        blob_path = f"{self.document_uuid}/text/{json_filename}"
        
        # Extract LLM metadata from chunks if available
        llm_metadata = {}
        if text_chunks and text_chunks[0].get('metadata', {}).get('llm_extracted_metadata'):
            llm_metadata = text_chunks[0]['metadata']['llm_extracted_metadata']
        
        # Convert chunks to serializable format
        chunk_data = {
            "filename": filename,
            "total_chunks": len(text_chunks),
            "processing_method": "enhanced_chunking_with_verbalization_and_llm_metadata",
            "llm_extracted_metadata": llm_metadata,
            "chunk_types": {
                "text": len([c for c in text_chunks if c['content_type'] == 'text']),
                "table": len([c for c in text_chunks if c['content_type'] == 'table']),
                "image": len([c for c in text_chunks if c['content_type'] == 'image'])
            },
            "created_at": text_chunks[0].get("metadata", {}).get("created_at", "") if text_chunks else "",
            "chunks": []
        }
        
        for chunk in text_chunks:
            chunk_info = {
                "chunk_id": chunk.get("chunk_id", ""),
                "file_name": chunk.get("file_name", ""),
                "section_name": chunk.get("section_name", ""),
                "section_no": chunk.get("section_no", ""),
                "domain": chunk.get("domain", ""),
                "content_type": chunk.get("content_type", "text"),
                "author": chunk.get("author", ""),
                "content": chunk.get("content", ""),
                "verbalized_content": chunk.get("verbalized_content", ""),
                "rfp_id": chunk.get("rfp_id", ""),
                "metadata": chunk.get("metadata", {})
            }
            chunk_data["chunks"].append(chunk_info)
        
        try:
            json_data = json.dumps(chunk_data, indent=2, ensure_ascii=False)
            blob_client = self.blob_service_client.get_blob_client(
                container=self.output_container, 
                blob=blob_path
            )
            blob_client.upload_blob(json_data, overwrite=True)
            
            print(f"💾 Saved text chunks to blob: {blob_path}")
            print(f"   📊 Chunk breakdown: {chunk_data['chunk_types']['text']} text, {chunk_data['chunk_types']['table']} table, {chunk_data['chunk_types']['image']} image")
            if llm_metadata:
                print(f"   🤖 LLM Metadata: Project='{llm_metadata.get('project_title', 'N/A')[:30]}...', Vendor='{llm_metadata.get('vendor_name', 'N/A')}', Domain='{llm_metadata.get('domain_category', 'N/A')}'")
            return blob_path
        except Exception as e:
            print(f"❌ Error saving text chunks: {e}")
            return None
    
    def save_text_chunks(self, text_chunks: List[Dict], filename: str) -> tuple:
        """Save text chunks as JSON to blob - Returns (chunk_data, blob_path)"""
        self._ensure_project_context()
        json_filename = f"{filename}_text_chunks.json"
        # blob_path = f"{self.document_uuid}/text/{json_filename}"
        blob_path = f"{self.project_id}/{self.document_type}/text/{json_filename}"
        
        # Extract LLM metadata from chunks if available
        llm_metadata = {}
        if text_chunks and text_chunks[0].get('metadata', {}).get('llm_extracted_metadata'):
            llm_metadata = text_chunks[0]['metadata']['llm_extracted_metadata']
        
        # Convert chunks to serializable format
        chunk_data = {
            "filename": filename,
            "total_chunks": len(text_chunks),
            "processing_method": "enhanced_chunking_with_verbalization_and_llm_metadata",
            "llm_extracted_metadata": llm_metadata,
            "chunk_types": {
                "text": len([c for c in text_chunks if c['content_type'] == 'text']),
                "table": len([c for c in text_chunks if c['content_type'] == 'table']),
                "image": len([c for c in text_chunks if c['content_type'] == 'image'])
            },
            "created_at": text_chunks[0].get("metadata", {}).get("created_at", "") if text_chunks else "",
            "chunks": []
        }
        
        for chunk in text_chunks:
            chunk_info = {
                "chunk_id": chunk.get("chunk_id", ""),
                "project_id": chunk.get("project_id", ""),  
                "file_name": chunk.get("file_name", ""),
                "section_name": chunk.get("section_name", ""),
                "section_no": chunk.get("section_no", ""),
                "domain": chunk.get("domain", ""),
                "content_type": chunk.get("content_type", "text"),
                "author": chunk.get("author", ""),
                "content": chunk.get("content", ""),
                "verbalized_content": chunk.get("verbalized_content", ""),
                "rfp_id": chunk.get("rfp_id", ""),
                "metadata": chunk.get("metadata", {})
            }
            chunk_data["chunks"].append(chunk_info)
        
        try:
            json_data = json.dumps(chunk_data, indent=2, ensure_ascii=False)
            blob_client = self.blob_service_client.get_blob_client(
                container=self.output_container, 
                blob=blob_path
            )
            blob_client.upload_blob(json_data, overwrite=True)
            
            print(f"💾 Saved text chunks to blob: {blob_path}")
            print(f"   📊 Chunk breakdown: {chunk_data['chunk_types']['text']} text, {chunk_data['chunk_types']['table']} table, {chunk_data['chunk_types']['image']} image")
            if llm_metadata:
                print(f"   🤖 LLM Metadata: Project='{llm_metadata.get('project_title', 'N/A')[:30]}...', Vendor='{llm_metadata.get('vendor_name', 'N/A')}', Domain='{llm_metadata.get('domain_category', 'N/A')}'")
            
            return chunk_data, blob_path
        except Exception as e:
            print(f"❌ Error saving text chunks: {e}")
            return None, None
        

    def save_text_chunks_RFI(self, text_chunks: List[Dict], filename: str) -> tuple:
            """Save enhanced text chunks with verbalization and LLM metadata as JSON file - Returns (chunk_data, json_path)"""
            self._ensure_project_context()
            json_filename = f"{filename}_text_chunks.json"
            # blob_path = f"{self.document_uuid}/text/{json_filename}"
            blob_path = f"{self.project_id}/{self.document_type}/text/{json_filename}"
        
            # Extract LLM metadata from chunks if available
            llm_metadata = {}
            if text_chunks and text_chunks[0].get('metadata', {}).get('llm_extracted_metadata'):
                llm_metadata = text_chunks[0]['metadata']['llm_extracted_metadata']
        
            # Convert chunks to serializable format with enhanced metadata including LLM data
            chunk_data = {
                "filename": filename,
                "total_chunks": len(text_chunks),
                "processing_method": "enhanced_chunking_with_verbalization_and_llm_metadata",
                # "llm_extracted_metadata": llm_metadata,  # NEW: Store LLM metadata at document level
                "chunk_types": {
                    "text": len([c for c in text_chunks if c['content_type'] == 'text']),
                    "table": len([c for c in text_chunks if c['content_type'] == 'table']),
                    "image": len([c for c in text_chunks if c['content_type'] == 'image'])
                },
                "created_at": text_chunks[0].get("metadata", {}).get("created_at", "") if text_chunks else "",
                "chunks": []
            }

            for chunk in text_chunks:
                chunk_info = {
                    "chunk_id": chunk.get("chunk_id", ""),
                    "project_id": chunk.get("project_id", ""),
                    "project_name": chunk.get("project_name", {}),
                    "client": chunk.get("client", {}),
                    "region": chunk.get("region", {}),
                    "industry": chunk.get("industry", {}),
                    "prepared_date": chunk.get("prepared_date", {}),
                    "station_discipline": chunk.get("station_discipline", {}),
                    "scope_of_work": chunk.get("scope_of_work", {}),
                    "required_activities": chunk.get("required_activities", {})
                }
                chunk_data["chunks"].append(chunk_info)
            try:
                json_data = json.dumps(chunk_data, indent=2, ensure_ascii=False)
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.output_container, 
                    blob=blob_path
                )
                blob_client.upload_blob(json_data, overwrite=True)
                
                print(f"💾 Saved text chunks to blob: {blob_path}")
                print(f"   📊 Chunk breakdown: {chunk_data['chunk_types']['text']} text, {chunk_data['chunk_types']['table']} table, {chunk_data['chunk_types']['image']} image")
                if llm_metadata:
                    print(f"   🤖 LLM Metadata: Project='{llm_metadata.get('project_title', 'N/A')[:30]}...', Vendor='{llm_metadata.get('vendor_name', 'N/A')}', Domain='{llm_metadata.get('domain_category', 'N/A')}'")
                
                return chunk_data, blob_path
            except Exception as e:
                print(f"❌ Error saving text chunks: {e}")
                return None, None
    def save_raw_text(self, raw_text: str, filename: str) -> str:
        """Save raw extracted text to blob"""
        self._ensure_project_context()
        txt_filename = f"{filename}_raw_text.txt"
        # blob_path = f"{self.document_uuid}/text/{txt_filename}"
        blob_path = f"{self.project_id}/{self.document_type}/text/{txt_filename}"
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.output_container, 
                blob=blob_path
            )
            blob_client.upload_blob(raw_text, overwrite=True)
            print(f"💾 Saved raw text to blob: {blob_path}")
            return blob_path
        except Exception as e:
            print(f"❌ Error saving raw text: {e}")
            return None