import os
import pandas as pd
from typing import List, Dict
from utils.helpers import semantic_chunking
from storage.local_storage import LocalStorage

class ContentExtractor:
    def __init__(self):
        self.storage = LocalStorage()
    
    def extract_all_content(self, result, filename: str, client=None, operation_id=None) -> Dict:
        """Extract text, tables, and images from Azure Document Intelligence result"""
        base_filename = os.path.splitext(filename)[0]
        
        # Extract content using only Azure DI
        text_elements = self._extract_text(result)
        tables = self._extract_tables(result, base_filename)
        figures = self._extract_figures(result, base_filename, client, operation_id)
        
        # Create text chunks from all text content
        all_text = "\n\n".join([elem["content"] for elem in text_elements])
        text_chunks = semantic_chunking(all_text)
        
        # Save text content to local storage
        if text_chunks:
            self.storage.save_text_chunks(text_chunks, base_filename)
        if all_text.strip():
            self.storage.save_raw_text(all_text, base_filename)
        
        return {
            "text_chunks": text_chunks,
            "tables": tables,
            "images": figures,  # Renamed for consistency with existing UI
            "raw_text": all_text,
            "stats": {
                "text_count": len(text_chunks),
                "table_count": len(tables),
                "image_count": len(figures)
            }
        }
    
    def _extract_text(self, result) -> List[Dict]:
        """Extract clean text content excluding tables and figures"""
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
                        "page_number": getattr(paragraph.bounding_regions[0], 'page_number', 1) if paragraph.bounding_regions else 1,
                        "paragraph_index": para_idx + 1
                    })
        
        return text_elements
    
    def _extract_tables(self, result, base_filename: str) -> List[Dict]:
        """Extract and save tables using Azure Document Intelligence"""
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
                            "column_count": len(df.columns),
                            "table_index": table_idx + 1
                        })
                except Exception as e:
                    print(f"Error processing table {table_idx + 1}: {e}")
                    continue
        
        return tables
    
    def _extract_figures(self, result, base_filename: str, client=None, operation_id=None) -> List[Dict]:
        """Extract figures/images using Azure Document Intelligence with proper image extraction"""
        figures = []
        
        if hasattr(result, 'figures') and result.figures:
            for fig_idx, figure in enumerate(result.figures):
                try:
                    # Extract text content from figure
                    text_content = self._extract_figure_content(figure, result)
                    page_number = getattr(figure.bounding_regions[0], 'page_number', 1) if figure.bounding_regions else 1
                    
                    figure_data = {
                        "content": text_content or f"Figure from page {page_number}",
                        "page_number": page_number,
                        "figure_index": fig_idx + 1,
                        "type": "figure",
                        "image_path": None,
                        "image_base64": None,
                        "width": None,
                        "height": None
                    }
                    
                    # Try to extract actual image using get_analyze_result_figure
                    if figure.id and client and operation_id:
                        try:
                            print(f"Extracting image for figure {fig_idx + 1} with ID: {figure.id}")
                            
                            # Get the raw image bytes
                            image_response = client.get_analyze_result_figure(
                                model_id=result.model_id,
                                result_id=operation_id,
                                figure_id=figure.id
                            )
                            
                            # Convert iterator to bytes
                            image_bytes = b''.join(image_response)
                            
                            if image_bytes:
                                # Save the image
                                image_path = self.storage.save_figure_image_bytes(
                                    image_bytes, 
                                    base_filename, 
                                    fig_idx + 1
                                )
                                
                                if image_path:
                                    # Convert to base64 for display
                                    import base64
                                    img_base64 = base64.b64encode(image_bytes).decode()
                                    
                                    figure_data.update({
                                        "image_path": image_path,
                                        "image_base64": img_base64,
                                        "type": "figure_with_image"
                                    })
                                    
                                    # Get image dimensions
                                    try:
                                        from PIL import Image
                                        from io import BytesIO
                                        img = Image.open(BytesIO(image_bytes))
                                        figure_data.update({
                                            "width": img.width,
                                            "height": img.height
                                        })
                                    except Exception as e:
                                        print(f"Error getting image dimensions: {e}")
                                
                                print(f"✅ Successfully extracted image for figure {fig_idx + 1}")
                            else:
                                print(f"⚠️ No image data received for figure {fig_idx + 1}")
                                
                        except Exception as e:
                            print(f"❌ Error extracting image for figure {fig_idx + 1}: {e}")
                            # Continue with text-only figure
                    
                    else:
                        if not figure.id:
                            print(f"ℹ️ Figure {fig_idx + 1} has no ID - text content only")
                        if not client or not operation_id:
                            print(f"ℹ️ Client or operation_id not provided - text content only")
                    
                    # Save text content if available
                    if text_content and text_content.strip():
                        text_path = self.storage.save_figure_text(text_content, base_filename, fig_idx + 1)
                    
                    figures.append(figure_data)
                    
                except Exception as e:
                    print(f"Error processing figure {fig_idx + 1}: {e}")
                    continue
        
        return figures
    
    def _table_to_dataframe(self, table) -> pd.DataFrame:
        """Convert Azure table to pandas DataFrame"""
        row_count = table.row_count
        column_count = table.column_count
        
        # Create empty grid
        grid = [["" for _ in range(column_count)] for _ in range(row_count)]
        
        # Fill grid with cell data
        for cell in table.cells:
            grid[cell.row_index][cell.column_index] = cell.content or ""
        
        # Create DataFrame
        if row_count > 1 and any(grid[0]):
            # First row as headers
            df = pd.DataFrame(grid[1:], columns=grid[0])
        else:
            # No headers
            df = pd.DataFrame(grid)
        
        # Clean up empty rows/columns
        df = df.dropna(how='all').loc[:, (df != '').any(axis=0)]
        return df
    
    def _extract_figure_content(self, figure, result) -> str:
        """Extract text content from figure using spans"""
        if hasattr(figure, 'spans') and figure.spans and hasattr(result, 'content'):
            content_parts = []
            for span in figure.spans:
                try:
                    span_content = result.content[span.offset:span.offset + span.length]
                    if span_content.strip():
                        content_parts.append(span_content.strip())
                except:
                    continue
            return " ".join(content_parts)
        return ""
    
    def _get_excluded_spans(self, result) -> set:
        """Get character spans that belong to tables and figures"""
        excluded_spans = set()
        
        # Exclude table spans
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                if hasattr(table, 'spans'):
                    for span in table.spans:
                        for i in range(span.offset, span.offset + span.length):
                            excluded_spans.add(i)
        
        # Exclude figure spans
        if hasattr(result, 'figures') and result.figures:
            for figure in result.figures:
                if hasattr(figure, 'spans'):
                    for span in figure.spans:
                        for i in range(span.offset, span.offset + span.length):
                            excluded_spans.add(i)
        
        return excluded_spans
    
    def _is_excluded_content(self, paragraph, excluded_spans: set) -> bool:
        """Check if paragraph content overlaps with excluded spans"""
        if hasattr(paragraph, 'spans') and paragraph.spans:
            for span in paragraph.spans:
                span_range = set(range(span.offset, span.offset + span.length))
                if span_range.intersection(excluded_spans):
                    return True
        return False