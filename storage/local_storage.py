import os
import json
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
from config import TABLES_DIR, IMAGES_DIR, TEXT_DIR

class LocalStorage:
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