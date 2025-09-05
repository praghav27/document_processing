import os
import json
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
from config import TABLES_DIR, IMAGES_DIR, TEXT_DIR
from typing import List, Dict
 
class LocalStorage:
    """Handle local storage of extracted content with enhanced chunking, verbalization, and LLM metadata support"""
   
    def __init__(self):
        self._ensure_directories()
   
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        os.makedirs(TABLES_DIR, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.makedirs(TEXT_DIR, exist_ok=True)
       
    def set_project_context(self, filename: str, document_type: str):
        """Set project ID and document type from filename (local storage compatibility)"""
        self.project_id = filename[:15] if filename else "unknown"
        self.document_type = document_type.lower()
        print(f"📁 Local storage context: {self.project_id}/{self.document_type}")
 
    def save_table(self, df: pd.DataFrame, filename: str, table_index: int) -> str:
        """Save table as CSV file"""
        csv_filename = f"{filename}_table_{table_index}.csv"
        # csv_path = os.path.join(TABLES_DIR, csv_filename)
        tables_dir = os.path.join("extracted_content", self.project_id, self.document_type, "tables")
        os.makedirs(tables_dir, exist_ok=True)
        csv_path = os.path.join(tables_dir, csv_filename)
        df.to_csv(csv_path, index=False)
        print(f"💾 Saved table {table_index}: {csv_path}")
        return csv_path
   
    def save_figure_image_bytes(self, image_bytes: bytes, filename: str, figure_index: int) -> str:
        """Save figure image from raw bytes data"""
        try:
            img_filename = f"{filename}_figure_{figure_index}.png"
            # Create the directory structure if it doesn't exist
            images_dir = os.path.join("extracted_content", self.project_id, self.document_type, "images")
            os.makedirs(images_dir, exist_ok=True)
            # img_path = os.path.join(IMAGES_DIR, img_filename)
            images_dir = os.path.join("extracted_content", self.project_id, self.document_type, "images")
            os.makedirs(images_dir, exist_ok=True)
            img_path = os.path.join(images_dir, img_filename)
 
           
            # Try to open with PIL to validate and convert to PNG
            try:
                img = Image.open(BytesIO(image_bytes))
                img.save(img_path, "PNG")
                print(f"💾 Saved figure image: {img_path}")
            except Exception:
                # If PIL fails, save raw bytes
                with open(img_path, 'wb') as f:
                    f.write(image_bytes)
                print(f"💾 Saved raw image bytes: {img_path}")
           
            return img_path
        except Exception as e:
            print(f"❌ Error saving figure image {figure_index}: {e}")
            return None
   
    def save_figure_text(self, text_content: str, filename: str, figure_index: int) -> str:
        """Save figure text content"""
        txt_filename = f"{filename}_figure_{figure_index}.txt"
        # Create the directory structure if it doesn't exist
        images_dir = os.path.join("extracted_content", self.project_id, self.document_type, "images")
        os.makedirs(images_dir, exist_ok=True)  
        # txt_path = os.path.join(IMAGES_DIR, txt_filename)
        images_dir = os.path.join("extracted_content", self.project_id, self.document_type, "images")
        os.makedirs(images_dir, exist_ok=True)
        txt_path = os.path.join(images_dir, txt_filename)
       
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
       
        print(f"💾 Saved figure text: {txt_path}")
        return txt_path

    def save_text_chunks(self, text_chunks: List[Dict], filename: str) -> tuple:
        """Save enhanced text chunks with verbalization and LLM metadata as JSON file - Returns (chunk_data, json_path)"""
        json_filename = f"{filename}_text_chunks.json"
        json_path = os.path.join(TEXT_DIR, json_filename)
       
        # Extract LLM metadata from chunks if available
        llm_metadata = {}
        if text_chunks and text_chunks[0].get('metadata', {}).get('llm_extracted_metadata'):
            llm_metadata = text_chunks[0]['metadata']['llm_extracted_metadata']
       
        # Convert chunks to serializable format with enhanced metadata including LLM data
        chunk_data = {
            "filename": filename,
            "total_chunks": len(text_chunks),
            "processing_method": "enhanced_chunking_with_verbalization_and_llm_metadata",
            "llm_extracted_metadata": llm_metadata,  # NEW: Store LLM metadata at document level
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
                "author": chunk.get("author", ""),  # Now includes LLM-extracted vendor_name
                "content": chunk.get("content", ""),
                "verbalized_content": chunk.get("verbalized_content", ""),
                'rfp_id': chunk.get("rfp_id", ""),
                "metadata": chunk.get("metadata", {})
            }
            chunk_data["chunks"].append(chunk_info)
        # print("Text chunks are as follows:")
        # print(chunk_data)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
       
        print(f"💾 Saved enhanced text chunks with LLM metadata: {json_path}")
        print(f"   📊 Chunk breakdown: {chunk_data['chunk_types']['text']} text, {chunk_data['chunk_types']['table']} table, {chunk_data['chunk_types']['image']} image")
        if llm_metadata:
            print(f"   🤖 LLM Metadata: Project='{llm_metadata.get('project_title', 'N/A')[:30]}...', Vendor='{llm_metadata.get('vendor_name', 'N/A')}', Domain='{llm_metadata.get('domain_category', 'N/A')}'")
       
        return chunk_data, json_path
 
    def save_text_chunks_RFI(self, text_chunks: List[Dict], filename: str) -> tuple:
        """Save enhanced text chunks with verbalization and LLM metadata as JSON file - Returns (chunk_data, json_path)"""
        json_filename = f"{filename}_text_chunks.json"
        json_path = os.path.join(TEXT_DIR, json_filename)
       
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
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
       
        print(f"💾 Saved enhanced text chunks with LLM metadata: {json_path}")
        print(f"   📊 Chunk breakdown: {chunk_data['chunk_types']['text']} text, {chunk_data['chunk_types']['table']} table, {chunk_data['chunk_types']['image']} image")
        if llm_metadata:
            print(f"   🤖 LLM Metadata: Project='{llm_metadata.get('project_title', 'N/A')[:30]}...', Vendor='{llm_metadata.get('vendor_name', 'N/A')}', Domain='{llm_metadata.get('domain_category', 'N/A')}'")
        return chunk_data, json_path

    def save_raw_text(self, raw_text: str, filename: str) -> str:
        """Save raw extracted text"""
        txt_filename = f"{filename}_raw_text.txt"
        # Create the directory structure if it doesn't exist
        text_dir = os.path.join("extracted_content", self.project_id, self.document_type, "text")
        os.makedirs(text_dir, exist_ok=True)
        txt_path = os.path.join(TEXT_DIR, txt_filename)
       
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)
       
        print(f"💾 Saved raw text: {txt_path}")
        return txt_path
   
    def save_document_metadata(self, metadata: Dict, filename: str) -> str:
        """Save LLM-extracted document metadata separately"""
        metadata_filename = f"{filename}_llm_metadata.json"
        metadata_path = os.path.join(TEXT_DIR, metadata_filename)
       
        metadata_data = {
            "filename": filename,
            "extraction_method": "llm_azure_openai",
            "extracted_metadata": metadata,
            "created_at": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
       
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=2, ensure_ascii=False)
       
        print(f"💾 Saved LLM-extracted document metadata: {metadata_path}")
        return metadata_path
   
    def save_extraction_summary(self, filename: str, summary_data: Dict) -> str:
        """Save extraction summary with all content types, verbalization, and LLM metadata info"""
        summary_filename = f"{filename}_extraction_summary.json"
        summary_path = os.path.join(TEXT_DIR, summary_filename)
       
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
       
        print(f"💾 Saved extraction summary: {summary_path}")
        return summary_path
   
    def save_section_analysis(self, filename: str, sections_data: List[Dict]) -> str:
        """Save section analysis data"""
        sections_filename = f"{filename}_sections_analysis.json"
        sections_path = os.path.join(TEXT_DIR, sections_filename)
       
        analysis_data = {
            "filename": filename,
            "total_sections": len(sections_data),
            "processing_method": "azure_document_intelligence_with_llm_metadata_and_verbalization",
            "sections": sections_data
        }
       
        with open(sections_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
       
        print(f"💾 Saved section analysis: {sections_path}")
        return sections_path
   
    def load_text_chunks(self, filename: str) -> List[Dict]:
        """Load enhanced text chunks with verbalization and LLM metadata from JSON file"""
        json_filename = f"{filename}_text_chunks.json"
        # json_path = os.path.join(TEXT_DIR, json_filename)
        text_dir = os.path.join("extracted_content", self.project_id, self.document_type, "text")
        os.makedirs(text_dir, exist_ok=True)
        json_path = os.path.join(text_dir, json_filename)
       
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
           
            chunks = data.get("chunks", [])
           
            # Ensure backward compatibility - add missing fields if needed
            for chunk in chunks:
                if "verbalized_content" not in chunk:
                    chunk["verbalized_content"] = chunk.get("content", "")
                # Ensure LLM metadata is present in chunk metadata
                if "metadata" in chunk and "llm_extracted_metadata" not in chunk["metadata"]:
                    chunk["metadata"]["llm_extracted_metadata"] = data.get("llm_extracted_metadata", {})
           
            print(f"📂 Loaded {len(chunks)} chunks with LLM metadata and verbalization support")
            if data.get("llm_extracted_metadata"):
                print(f"   🤖 Document metadata: {data['llm_extracted_metadata'].get('project_title', 'N/A')}")
            return chunks
           
        except Exception as e:
            print(f"❌ Error loading text chunks: {e}")
            return []
   
    def load_document_metadata(self, filename: str) -> Dict:
        """Load LLM-extracted document metadata"""
        metadata_filename = f"{filename}_llm_metadata.json"
        metadata_path = os.path.join(TEXT_DIR, metadata_filename)
       
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("extracted_metadata", {})
        except Exception as e:
            print(f"❌ Error loading document metadata: {e}")
            return {}
   
    def load_raw_text(self, filename: str) -> str:
        """Load raw text from file"""
        txt_filename = f"{filename}_raw_text.txt"
        # txt_path = os.path.join(TEXT_DIR, txt_filename)
        text_dir = os.path.join("extracted_content", self.project_id, self.document_type, "text")
        os.makedirs(text_dir, exist_ok=True)
        txt_path = os.path.join(text_dir, txt_filename)
       
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error loading raw text: {e}")
            return ""
   
    def load_extraction_summary(self, filename: str) -> Dict:
        """Load extraction summary"""
        summary_filename = f"{filename}_extraction_summary.json"
        summary_path = os.path.join(TEXT_DIR, summary_filename)
       
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading extraction summary: {e}")
            return {}
   
    def get_storage_summary(self, filename: str) -> Dict:
        """Get comprehensive summary of all stored files for a document with LLM metadata and verbalization info"""
        base_filename = os.path.splitext(filename)[0]
       
        summary = {
            "base_filename": base_filename,
            "files": {
                "text": [],
                "tables": [],
                "images": [],
                "analysis": []
            },
            "storage_stats": {
                "total_files": 0,
                "total_size_mb": 0
            },
            "verbalization_info": {
                "chunks_with_verbalization": 0,
                "verbalization_enabled": False
            },
            "llm_metadata_info": {
                "metadata_extracted": False,
                "extraction_method": "none",
                "document_metadata": {}
            }
        }
       
        # Check each directory for files
        directories = {
            "text": TEXT_DIR,
            "tables": TABLES_DIR,
            "images": IMAGES_DIR
        }
       
        for category, directory in directories.items():
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    if file.startswith(base_filename):
                        file_path = os.path.join(directory, file)
                        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                       
                        file_info = {
                            "filename": file,
                            "path": file_path,
                            "size_mb": round(file_size, 2),
                            "type": self._get_file_type(file)
                        }
                       
                        # Categorize analysis files
                        if file.endswith(('_summary.json', '_analysis.json', '_sections_analysis.json', '_llm_metadata.json')):
                            summary["files"]["analysis"].append(file_info)
                        else:
                            summary["files"][category].append(file_info)
                       
                        summary["storage_stats"]["total_files"] += 1
                        summary["storage_stats"]["total_size_mb"] += file_size
       
        # Check for verbalization info
        chunks_data = self.load_text_chunks(base_filename)
        if chunks_data:
            verbalized_chunks = [c for c in chunks_data if c.get('verbalized_content') and c.get('verbalized_content') != c.get('content', '')]
            summary["verbalization_info"]["chunks_with_verbalization"] = len(verbalized_chunks)
            summary["verbalization_info"]["verbalization_enabled"] = len(verbalized_chunks) > 0
       
        # Check for LLM metadata info
        llm_metadata = self.load_document_metadata(base_filename)
        if llm_metadata:
            summary["llm_metadata_info"]["metadata_extracted"] = True
            summary["llm_metadata_info"]["extraction_method"] = "llm_azure_openai"
            summary["llm_metadata_info"]["document_metadata"] = llm_metadata
       
        summary["storage_stats"]["total_size_mb"] = round(summary["storage_stats"]["total_size_mb"], 2)
       
        return summary
   
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        if filename.endswith('.json'):
            if 'chunks' in filename:
                return 'text_chunks_with_llm_metadata'
            elif 'llm_metadata' in filename:
                return 'llm_extracted_metadata'
            elif 'summary' in filename:
                return 'extraction_summary'
            elif 'analysis' in filename:
                return 'section_analysis'
            else:
                return 'json_data'
        elif filename.endswith('.txt'):
            if 'raw_text' in filename:
                return 'raw_text'
            elif 'figure' in filename:
                return 'figure_text'
            else:
                return 'text_file'
        elif filename.endswith('.csv'):
            return 'table_data'
        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            return 'figure_image'
        else:
            return 'unknown'
   
    def create_comprehensive_report(self, filename: str) -> Dict:
        """Create a comprehensive report of all extracted content with LLM metadata and verbalization"""
        base_filename = os.path.splitext(filename)[0]
       
        report = {
            "document_name": filename,
            "processing_timestamp": "",
            "content_summary": {
                "text_chunks": 0,
                "table_chunks": 0,
                "image_chunks": 0,
                "tables": 0,
                "figures": 0,
                "sections": 0
            },
            "verbalization_summary": {
                "total_verbalized_chunks": 0,
                "verbalized_tables": 0,
                "verbalized_images": 0,
                "verbalization_enabled": False
            },
            "llm_metadata_summary": {
                "metadata_extracted": False,
                "extraction_method": "none",
                "document_metadata": {},
                "chunks_with_llm_metadata": 0
            },
            "file_locations": {
                "text_files": [],
                "table_files": [],
                "image_files": [],
                "analysis_files": []
            },
            "storage_info": self.get_storage_summary(filename)
        }
       
        # Load text chunks info
        chunks_data = self.load_text_chunks(base_filename)
        if chunks_data:
            # Count chunks by type
            text_chunks = [c for c in chunks_data if c.get('content_type') == 'text']
            table_chunks = [c for c in chunks_data if c.get('content_type') == 'table']
            image_chunks = [c for c in chunks_data if c.get('content_type') == 'image']
           
            report["content_summary"]["text_chunks"] = len(text_chunks)
            report["content_summary"]["table_chunks"] = len(table_chunks)
            report["content_summary"]["image_chunks"] = len(image_chunks)
           
            # Count verbalized chunks
            verbalized_tables = [c for c in table_chunks if c.get('verbalized_content') and c.get('verbalized_content') != c.get('content', '')]
            verbalized_images = [c for c in image_chunks if c.get('verbalized_content') and c.get('verbalized_content') != c.get('content', '')]
           
            report["verbalization_summary"]["verbalized_tables"] = len(verbalized_tables)
            report["verbalization_summary"]["verbalized_images"] = len(verbalized_images)
            report["verbalization_summary"]["total_verbalized_chunks"] = len(verbalized_tables) + len(verbalized_images)
            report["verbalization_summary"]["verbalization_enabled"] = len(verbalized_tables) > 0 or len(verbalized_images) > 0
           
            # Count chunks with LLM metadata
            chunks_with_llm = [c for c in chunks_data if c.get('metadata', {}).get('llm_extracted_metadata')]
            report["llm_metadata_summary"]["chunks_with_llm_metadata"] = len(chunks_with_llm)
           
            # Extract sections info
            sections = set()
            for chunk in chunks_data:
                if chunk.get("section_name"):
                    sections.add(chunk["section_name"])
            report["content_summary"]["sections"] = len(sections)
       
        # Load LLM metadata
        llm_metadata = self.load_document_metadata(base_filename)
        if llm_metadata:
            report["llm_metadata_summary"]["metadata_extracted"] = True
            report["llm_metadata_summary"]["extraction_method"] = "llm_azure_openai"
            report["llm_metadata_summary"]["document_metadata"] = llm_metadata
       
        # Count tables and figures from files
        storage_summary = self.get_storage_summary(filename)
        report["content_summary"]["tables"] = len([f for f in storage_summary["files"]["tables"] if f["type"] == "table_data"])
        report["content_summary"]["figures"] = len([f for f in storage_summary["files"]["images"] if f["type"] == "figure_image"])
       
        # File locations
        report["file_locations"]["text_files"] = [f["path"] for f in storage_summary["files"]["text"]]
        report["file_locations"]["table_files"] = [f["path"] for f in storage_summary["files"]["tables"]]
        report["file_locations"]["image_files"] = [f["path"] for f in storage_summary["files"]["images"]]
        report["file_locations"]["analysis_files"] = [f["path"] for f in storage_summary["files"]["analysis"]]
       
        return report
   
    def cleanup_files(self, filename: str) -> bool:
        """Remove all files associated with a document"""
        base_filename = os.path.splitext(filename)[0]
        removed_files = []
       
        directories = [TEXT_DIR, TABLES_DIR, IMAGES_DIR]
       
        for directory in directories:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    if file.startswith(base_filename):
                        file_path = os.path.join(directory, file)
                        try:
                            os.remove(file_path)
                            removed_files.append(file_path)
                        except Exception as e:
                            print(f"❌ Error removing file {file_path}: {e}")
       
        print(f"🗑️ Removed {len(removed_files)} files for {filename}")
        return len(removed_files) > 0
   
    def get_verbalization_stats(self, filename: str) -> Dict:
        """Get detailed verbalization statistics for a document"""
        base_filename = os.path.splitext(filename)[0]
        chunks_data = self.load_text_chunks(base_filename)
       
        stats = {
            "total_chunks": 0,
            "verbalized_chunks": 0,
            "chunk_types": {
                "text": {"total": 0, "verbalized": 0},
                "table": {"total": 0, "verbalized": 0},
                "image": {"total": 0, "verbalized": 0}
            },
            "verbalization_rate": 0.0,
            "avg_verbalization_length": 0,
            "verbalization_enabled": False
        }
       
        if chunks_data:
            stats["total_chunks"] = len(chunks_data)
           
            verbalized_lengths = []
           
            for chunk in chunks_data:
                content_type = chunk.get('content_type', 'text')
                stats["chunk_types"][content_type]["total"] += 1
               
                # Check if chunk is verbalized (different from original content)
                original = chunk.get('content', '')
                verbalized = chunk.get('verbalized_content', '')
               
                if verbalized and verbalized != original:
                    stats["verbalized_chunks"] += 1
                    stats["chunk_types"][content_type]["verbalized"] += 1
                    verbalized_lengths.append(len(verbalized))
           
            if stats["total_chunks"] > 0:
                stats["verbalization_rate"] = stats["verbalized_chunks"] / stats["total_chunks"]
           
            if verbalized_lengths:
                stats["avg_verbalization_length"] = sum(verbalized_lengths) / len(verbalized_lengths)
                stats["verbalization_enabled"] = True
       
        return stats
   
    def get_llm_metadata_stats(self, filename: str) -> Dict:
        """Get detailed LLM metadata statistics for a document"""
        base_filename = os.path.splitext(filename)[0]
        chunks_data = self.load_text_chunks(base_filename)
        llm_metadata = self.load_document_metadata(base_filename)
       
        stats = {
            "metadata_extracted": False,
            "extraction_method": "none",
            "document_metadata": {},
            "chunks_with_metadata": 0,
            "metadata_fields_populated": 0,
            "metadata_completeness": 0.0,
            "chunk_integration": {
                "text": {"total": 0, "with_metadata": 0},
                "table": {"total": 0, "with_metadata": 0},
                "image": {"total": 0, "with_metadata": 0}
            }
        }
       
        # Check document-level metadata
        if llm_metadata:
            stats["metadata_extracted"] = True
            stats["extraction_method"] = "llm_azure_openai"
            stats["document_metadata"] = llm_metadata
           
            # Count populated fields
            required_fields = ['project_title', 'client_name', 'vendor_name', 'submission_date', 'domain_category', 'service_category']
            populated_fields = sum(1 for field in required_fields if llm_metadata.get(field) not in [None, '', 'Not Specified', 'Other'])
            stats["metadata_fields_populated"] = populated_fields
            stats["metadata_completeness"] = populated_fields / len(required_fields) if required_fields else 0
       
        # Check chunk-level integration
        if chunks_data:
            for chunk in chunks_data:
                content_type = chunk.get('content_type', 'text')
                stats["chunk_integration"][content_type]["total"] += 1
               
                # Check if chunk has LLM metadata integrated
                if chunk.get('metadata', {}).get('llm_extracted_metadata'):
                    stats["chunks_with_metadata"] += 1
                    stats["chunk_integration"][content_type]["with_metadata"] += 1
       
        return stats
 