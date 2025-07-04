import os
import pandas as pd
from PIL import Image
from config import TABLES_DIR, IMAGES_DIR

class LocalStorage:
    def __init__(self):
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        os.makedirs(TABLES_DIR, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)
    
    def save_table(self, df: pd.DataFrame, filename: str, table_index: int) -> str:
        """Save table as CSV file"""
        csv_filename = f"{filename}_table_{table_index}.csv"
        csv_path = os.path.join(TABLES_DIR, csv_filename)
        df.to_csv(csv_path, index=False)
        return csv_path
    
    def save_image(self, image_data: bytes, filename: str, image_index: int, extension: str = "png") -> str:
        """Save image file"""
        img_filename = f"{filename}_image_{image_index}.{extension}"
        img_path = os.path.join(IMAGES_DIR, img_filename)
        
        with open(img_path, 'wb') as f:
            f.write(image_data)
        
        return img_path