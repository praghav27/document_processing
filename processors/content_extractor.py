import os
import pandas as pd
import tempfile
import fitz  # PyMuPDF
import base64
import io
from PIL import Image
from typing import List, Dict, Tuple
from utils.helpers import semantic_chunking
from storage.local_storage import LocalStorage

class ContentExtractor:
    def __init__(self):
        self.storage = LocalStorage()
    
    def extract_all_content(self, result, filename: str, file_bytes: bytes = None) -> Dict:
        """Extract text, tables, and images from Azure result"""
        base_filename = os.path.splitext(filename)[0]
        
        # Extract content
        text_elements = self._extract_text(result)
        tables = self._extract_tables(result, base_filename)
        
        # Extract images intelligently (avoid duplicates)
        all_images = self._extract_images_combined(result, base_filename, file_bytes)
        # Create text chunks
        all_text = "\n\n".join([elem["content"] for elem in text_elements])
        text_chunks = semantic_chunking(all_text)
    
        return {
        "text_chunks": text_chunks,
        "tables": tables,
        "images": all_images,
        "stats": {
            "text_count": len(text_chunks),
            "table_count": len(tables),
            "image_count": len(all_images)
        }
        }
    
    def _extract_images_combined(self, result, base_filename: str, file_bytes: bytes = None) -> List[Dict]:
        """Extract images combining Azure DI text with actual image files"""
        # Get figure text from Azure DI
        figure_texts = self._extract_figures(result, base_filename)
    
        # Get actual images from PyMuPDF
        actual_images = self._extract_actual_images(file_bytes, base_filename) if file_bytes else []
    
        # Combine: If we have actual images, merge with figure text by page number
        if actual_images:
            combined_images = []
        
            # Create a map of figure texts by page number
            figure_text_map = {fig["page_number"]: fig["content"] for fig in figure_texts}
        
            # Add actual images with their text content
            for img in actual_images:
                page_num = img["page_number"]
                figure_text = figure_text_map.get(page_num, f"Image from page {page_num}")
            
                combined_images.append({
                    **img,
                    "content": figure_text,  # Use Azure DI text if available
                    "type": "image_with_content"
                })
        
            # Add any figure texts that don't have corresponding images
            for fig in figure_texts:
                if fig["page_number"] not in [img["page_number"] for img in actual_images]:
                    combined_images.append({
                        **fig,
                        "type": "figure_text_only"
                    })
        
            return combined_images
        else:
            # No actual images found, return figure texts only
            return figure_texts

    def _extract_actual_images(self, file_bytes: bytes, base_filename: str) -> List[Dict]:
        """Extract actual image files from PDF"""
        images = []
        
        if not file_bytes:
            return images
        
        try:
            # Save bytes to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_bytes)
                pdf_path = tmp_file.name
            
            try:
                doc = fitz.open(pdf_path)
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            # Get image data
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            
                            # Convert to PIL Image - FIXED
                            if pix.n - pix.alpha < 4:  # GRAY or RGB
                                img_data = pix.tobytes("png")
                                
                                # Use BytesIO for PIL Image
                                pil_image = Image.open(io.BytesIO(img_data))
                                
                                # Save image locally
                                image_path = self.storage.save_image(img_data, base_filename, len(images) + 1, "png")
                                
                                # Convert to base64 for display
                                img_base64 = base64.b64encode(img_data).decode()
                                
                                images.append({
                                    "content": f"Image extracted from page {page_num + 1}",
                                    "page_number": page_num + 1,
                                    "image_index": img_index + 1,
                                    "type": "actual_image",
                                    "image_path": image_path,
                                    "image_base64": img_base64,
                                    "width": pix.width,
                                    "height": pix.height
                                })
                            
                            pix = None
                            
                        except Exception as e:
                            print(f"Error extracting image {img_index + 1} from page {page_num + 1}: {e}")
                            continue
                
                doc.close()
                
            finally:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
                    
        except Exception as e:
            print(f"Error extracting images from PDF: {e}")
        
        return images
    
    def _extract_figures(self, result, base_filename: str) -> List[Dict]:
        """Extract figures with their text content from Azure result"""
        figures = []
        
        if hasattr(result, 'figures') and result.figures:
            for fig_idx, figure in enumerate(result.figures):
                try:
                    content = self._extract_figure_content(figure, result)
                    if content:
                        figures.append({
                            "content": content,
                            "page_number": getattr(figure.bounding_regions[0], 'page_number', 1) if figure.bounding_regions else 1,
                            "figure_index": fig_idx + 1,
                            "type": "figure_text",
                            "image_path": None,
                            "image_base64": None
                        })
                except Exception as e:
                    print(f"Error processing figure {fig_idx + 1}: {e}")
                    continue
        
        return figures
    
    # Keep all other existing methods...
    def _extract_text(self, result) -> List[Dict]:
        """Extract clean text excluding tables and figures"""
        text_elements = []
        excluded_spans = self._get_excluded_spans(result)
        
        if hasattr(result, 'paragraphs') and result.paragraphs:
            for para_idx, paragraph in enumerate(result.paragraphs):
                if self._is_excluded_content(paragraph, excluded_spans):
                    continue
                
                content = paragraph.content or ""
                if content.strip():
                    text_elements.append({
                        "content": content,
                        "page_number": getattr(paragraph.bounding_regions[0], 'page_number', 1) if paragraph.bounding_regions else 1
                    })
        
        return text_elements
    
    def _extract_tables(self, result, base_filename: str) -> List[Dict]:
        """Extract and save tables"""
        tables = []
        
        if hasattr(result, 'tables') and result.tables:
            for table_idx, table in enumerate(result.tables):
                try:
                    df = self._table_to_dataframe(table)
                    if not df.empty:
                        csv_path = self.storage.save_table(df, base_filename, table_idx + 1)
                        
                        tables.append({
                            "content": df.to_string(index=False),
                            "html": df.to_html(index=False, classes="table table-striped"),
                            "csv_path": csv_path,
                            "page_number": getattr(table.bounding_regions[0], 'page_number', 1) if table.bounding_regions else 1,
                            "row_count": len(df),
                            "column_count": len(df.columns)
                        })
                except Exception as e:
                    print(f"Error processing table {table_idx + 1}: {e}")
                    continue
        
        return tables
    
    def _table_to_dataframe(self, table) -> pd.DataFrame:
        """Convert Azure table to pandas DataFrame"""
        row_count = table.row_count
        column_count = table.column_count
        
        grid = [["" for _ in range(column_count)] for _ in range(row_count)]
        
        for cell in table.cells:
            grid[cell.row_index][cell.column_index] = cell.content or ""
        
        if row_count > 1 and any(grid[0]):
            df = pd.DataFrame(grid[1:], columns=grid[0])
        else:
            df = pd.DataFrame(grid)
        
        df = df.dropna(how='all').loc[:, (df != '').any(axis=0)]
        return df
    
    def _extract_figure_content(self, figure, result) -> str:
        """Extract text content from figure using spans"""
        if hasattr(figure, 'spans') and figure.spans and hasattr(result, 'content'):
            content_parts = []
            for span in figure.spans:
                span_content = result.content[span.offset:span.offset + span.length]
                content_parts.append(span_content)
            return " ".join(content_parts).strip()
        return ""
    
    def _get_excluded_spans(self, result) -> set:
        """Get spans belonging to tables and figures"""
        excluded_spans = set()
        
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                if hasattr(table, 'spans'):
                    for span in table.spans:
                        for i in range(span.offset, span.offset + span.length):
                            excluded_spans.add(i)
        
        if hasattr(result, 'figures') and result.figures:
            for figure in result.figures:
                if hasattr(figure, 'spans'):
                    for span in figure.spans:
                        for i in range(span.offset, span.offset + span.length):
                            excluded_spans.add(i)
        
        return excluded_spans
    
    def _is_excluded_content(self, paragraph, excluded_spans: set) -> bool:
        """Check if paragraph overlaps with excluded spans"""
        if hasattr(paragraph, 'spans') and paragraph.spans:
            for span in paragraph.spans:
                span_range = set(range(span.offset, span.offset + span.length))
                if span_range.intersection(excluded_spans):
                    return True
        return False