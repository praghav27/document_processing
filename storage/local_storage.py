import os
import json
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
from config import TABLES_DIR, IMAGES_DIR, TEXT_DIR, CHUNKS_DIR
from typing import List, Dict

class LocalStorage:
    def __init__(self):
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        os.makedirs(TABLES_DIR, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.makedirs(TEXT_DIR, exist_ok=True)
        os.makedirs(CHUNKS_DIR, exist_ok=True)  # NEW: Structure-aware chunks
    
    def save_table(self, df: pd.DataFrame, filename: str, table_index: int) -> str:
        """Save table as CSV file"""
        csv_filename = f"{filename}_table_{table_index}.csv"
        csv_path = os.path.join(TABLES_DIR, csv_filename)
        df.to_csv(csv_path, index=False)
        return csv_path
    
    def save_figure_image(self, image_base64: str, filename: str, figure_index: int) -> str:
        """Save figure image from base64 data"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            img = Image.open(BytesIO(image_data))
            
            # Save as PNG
            img_filename = f"{filename}_figure_{figure_index}.png"
            img_path = os.path.join(IMAGES_DIR, img_filename)
            img.save(img_path, "PNG")
            
            return img_path
        except Exception as e:
            print(f"Error saving figure image {figure_index}: {e}")
            return None
    
    def save_figure_image_bytes(self, image_bytes: bytes, filename: str, figure_index: int) -> str:
        """Save figure image from raw bytes data"""
        try:
            # Determine image format and save appropriately
            img_filename = f"{filename}_figure_{figure_index}.png"
            img_path = os.path.join(IMAGES_DIR, img_filename)
            
            # Try to open with PIL to validate and convert to PNG
            try:
                img = Image.open(BytesIO(image_bytes))
                img.save(img_path, "PNG")
                print(f"✅ Saved figure image: {img_path}")
            except Exception:
                # If PIL fails, save raw bytes as PNG
                with open(img_path, 'wb') as f:
                    f.write(image_bytes)
                print(f"✅ Saved raw image bytes: {img_path}")
            
            return img_path
        except Exception as e:
            print(f"❌ Error saving figure image {figure_index}: {e}")
            return None
    
    def save_figure_text(self, text_content: str, filename: str, figure_index: int) -> str:
        """Save figure text content"""
        txt_filename = f"{filename}_figure_{figure_index}.txt"
        txt_path = os.path.join(IMAGES_DIR, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return txt_path
    
    def save_text_chunks(self, text_chunks: list, filename: str) -> str:
        """Save text chunks as JSON file"""
        json_filename = f"{filename}_text_chunks.json"
        json_path = os.path.join(TEXT_DIR, json_filename)
        
        chunk_data = {
            "filename": filename,
            "total_chunks": len(text_chunks),
            "chunks": [
                {
                    "index": i + 1,
                    "content": chunk,
                    "length": len(chunk)
                }
                for i, chunk in enumerate(text_chunks)
            ]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        
        return json_path
    
    def save_raw_text(self, raw_text: str, filename: str) -> str:
        """Save raw extracted text"""
        txt_filename = f"{filename}_raw_text.txt"
        txt_path = os.path.join(TEXT_DIR, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)
        
        return txt_path
    
    # NEW: Structure-aware chunking storage methods
    
    def save_structure_aware_chunks(self, chunks: List[Dict], filename: str) -> str:
        """Save structure-aware chunks with rich metadata"""
        json_filename = f"{filename}_structure_aware_chunks.json"
        json_path = os.path.join(CHUNKS_DIR, json_filename)
        
        # Prepare chunk data with metadata
        chunks_data = {
            "filename": filename,
            "total_chunks": len(chunks),
            "processing_method": "structure_aware_llm",
            "chunks": []
        }
        
        for chunk in chunks:
            # Create a clean chunk object for storage
            chunk_data = {
                "chunk_id": chunk.get("chunk_id", ""),
                "content": chunk.get("content", ""),
                "metadata": {
                    "section_type": chunk.get("section_type", ""),
                    "section_title": chunk.get("section_title", ""),
                    "section_hierarchy": chunk.get("section_hierarchy", ""),
                    "domain_category": chunk.get("domain_category", ""),
                    "service_category": chunk.get("service_category", ""),
                    "content_type": chunk.get("content_type", ""),
                    "page_number": chunk.get("page_number", 1),
                    "chunk_number": chunk.get("chunk_number", 1),
                    "total_chunks_in_section": chunk.get("total_chunks_in_section", 1),
                    "token_count": chunk.get("token_count", 0),
                    "char_count": chunk.get("char_count", 0),
                    "has_table_content": chunk.get("has_table_content", False),
                    "has_image_content": chunk.get("has_image_content", False),
                    "table_count": chunk.get("table_count", 0),
                    "image_count": chunk.get("image_count", 0),
                    "classification_confidence": chunk.get("classification_confidence", ""),
                },
                "document_metadata": {
                    "document_id": chunk.get("document_id", ""),
                    "document_title": chunk.get("document_title", ""),
                    "client_name": chunk.get("client_name", ""),
                    "vendor_name": chunk.get("vendor_name", ""),
                    "project_site": chunk.get("project_site", ""),
                    "submission_date": chunk.get("submission_date", ""),
                    "project_value": chunk.get("project_value", 0.0)
                }
            }
            chunks_data["chunks"].append(chunk_data)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(chunks)} structure-aware chunks to: {json_path}")
        return json_path
    
    def save_document_structure(self, structure: Dict, filename: str) -> str:
        """Save document structure analysis"""
        json_filename = f"{filename}_document_structure.json"
        json_path = os.path.join(CHUNKS_DIR, json_filename)
        
        structure_data = {
            "filename": filename,
            "analysis_method": structure.get("analysis_method", "llm_based"),
            "document_type": structure.get("document_type", "rfp"),
            "total_sections": structure.get("total_sections", 0),
            "sections": structure.get("sections", [])
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(structure_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved document structure to: {json_path}")
        return json_path
    
    def save_processing_metadata(self, metadata: Dict, filename: str) -> str:
        """Save processing metadata and statistics"""
        json_filename = f"{filename}_processing_metadata.json"
        json_path = os.path.join(CHUNKS_DIR, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved processing metadata to: {json_path}")
        return json_path
    
    def load_chunks_with_metadata(self, filename: str) -> List[Dict]:
        """Load structure-aware chunks with metadata"""
        json_filename = f"{filename}_structure_aware_chunks.json"
        json_path = os.path.join(CHUNKS_DIR, json_filename)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("chunks", [])
        except Exception as e:
            print(f"Error loading chunks: {e}")
            return []
    
    def load_document_structure(self, filename: str) -> Dict:
        """Load document structure analysis"""
        json_filename = f"{filename}_document_structure.json"
        json_path = os.path.join(CHUNKS_DIR, json_filename)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading document structure: {e}")
            return {}
    
    def load_processing_metadata(self, filename: str) -> Dict:
        """Load processing metadata"""
        json_filename = f"{filename}_processing_metadata.json"
        json_path = os.path.join(CHUNKS_DIR, json_filename)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading processing metadata: {e}")
            return {}
    
    def get_storage_summary(self, filename: str) -> Dict:
        """Get summary of all stored files for a document"""
        base_filename = os.path.splitext(filename)[0]
        
        summary = {
            "base_filename": base_filename,
            "files": {
                "text": [],
                "tables": [],
                "images": [],
                "chunks": [],
                "structure": [],
                "metadata": []
            },
            "storage_stats": {
                "total_files": 0,
                "total_size_mb": 0
            }
        }
        
        # Check each directory for files
        directories = {
            "text": TEXT_DIR,
            "tables": TABLES_DIR,
            "images": IMAGES_DIR,
            "chunks": CHUNKS_DIR
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
                            "size_mb": round(file_size, 2)
                        }
                        
                        summary["files"][category].append(file_info)
                        summary["storage_stats"]["total_files"] += 1
                        summary["storage_stats"]["total_size_mb"] += file_size
        
        summary["storage_stats"]["total_size_mb"] = round(summary["storage_stats"]["total_size_mb"], 2)
        
        return summary