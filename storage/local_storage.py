import os
import json
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
from config import TABLES_DIR, IMAGES_DIR, TEXT_DIR
from typing import List, Dict

class LocalStorage:
    """Handle local storage of extracted content"""
    
    def __init__(self):
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        os.makedirs(TABLES_DIR, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.makedirs(TEXT_DIR, exist_ok=True)
    
    def save_table(self, df: pd.DataFrame, filename: str, table_index: int) -> str:
        """Save table as CSV file"""
        csv_filename = f"{filename}_table_{table_index}.csv"
        csv_path = os.path.join(TABLES_DIR, csv_filename)
        df.to_csv(csv_path, index=False)
        print(f"💾 Saved table {table_index}: {csv_path}")
        return csv_path
    
    def save_figure_image_bytes(self, image_bytes: bytes, filename: str, figure_index: int) -> str:
        """Save figure image from raw bytes data"""
        try:
            img_filename = f"{filename}_figure_{figure_index}.png"
            img_path = os.path.join(IMAGES_DIR, img_filename)
            
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
        txt_path = os.path.join(IMAGES_DIR, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        print(f"💾 Saved figure text: {txt_path}")
        return txt_path
    
    def save_text_chunks(self, text_chunks: List[Dict], filename: str) -> str:
        """Save text chunks as JSON file"""
        json_filename = f"{filename}_text_chunks.json"
        json_path = os.path.join(TEXT_DIR, json_filename)
        
        # Convert chunks to serializable format
        chunk_data = {
            "filename": filename,
            "total_chunks": len(text_chunks),
            "processing_method": "simple_chunking",
            "chunks": []
        }
        
        for chunk in text_chunks:
            chunk_info = {
                "chunk_id": chunk.get("chunk_id", ""),
                "section_id": chunk.get("section_id", ""),
                "section_name": chunk.get("section_name", ""),
                "section_no": chunk.get("section_no", ""),
                "content": chunk.get("content", ""),
                "content_type": chunk.get("content_type", "text"),
                "metadata": chunk.get("metadata", {})
            }
            chunk_data["chunks"].append(chunk_info)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved text chunks: {json_path}")
        return json_path
    
    def save_raw_text(self, raw_text: str, filename: str) -> str:
        """Save raw extracted text"""
        txt_filename = f"{filename}_raw_text.txt"
        txt_path = os.path.join(TEXT_DIR, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)
        
        print(f"💾 Saved raw text: {txt_path}")
        return txt_path
    
    def load_text_chunks(self, filename: str) -> List[Dict]:
        """Load text chunks from JSON file"""
        json_filename = f"{filename}_text_chunks.json"
        json_path = os.path.join(TEXT_DIR, json_filename)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("chunks", [])
        except Exception as e:
            print(f"❌ Error loading text chunks: {e}")
            return []
    
    def load_raw_text(self, filename: str) -> str:
        """Load raw text from file"""
        txt_filename = f"{filename}_raw_text.txt"
        txt_path = os.path.join(TEXT_DIR, txt_filename)
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error loading raw text: {e}")
            return ""
    
    def get_storage_summary(self, filename: str) -> Dict:
        """Get summary of all stored files for a document"""
        base_filename = os.path.splitext(filename)[0]
        
        summary = {
            "base_filename": base_filename,
            "files": {
                "text": [],
                "tables": [],
                "images": []
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
                            "size_mb": round(file_size, 2)
                        }
                        
                        summary["files"][category].append(file_info)
                        summary["storage_stats"]["total_files"] += 1
                        summary["storage_stats"]["total_size_mb"] += file_size
        
        summary["storage_stats"]["total_size_mb"] = round(summary["storage_stats"]["total_size_mb"], 2)
        
        return summary
    
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