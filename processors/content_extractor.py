import os
import pandas as pd
from typing import List, Dict
from storage.local_storage import LocalStorage
import re
import uuid
from datetime import datetime

class SimpleChunker:
    """Simple text chunker for basic document processing"""
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.section_patterns = {
            'section_heading': r'\[ParagraphRole\.SECTION_HEADING\]',
            'numbered_section': r'^\s*(\d+\.\d+)\s+([A-Z\s]+)',
            'cleanup_tags': r'\[None\]\s*|\[ParagraphRole\.[^\]]+\]'
        }
    
    def chunk_text(self, text: str) -> List[Dict]:
        """Create chunks from text with metadata"""
        print(f"📝 Starting text chunking process...")
        print(f"   Input text length: {len(text)} characters")
        
        chunks = []
        
        # Split by sections first
        sections = self._split_by_sections(text)
        print(f"   Found {len(sections)} sections")
        
        for idx, section in enumerate(sections):
            if section.strip():
                cleaned_section = self._clean_text(section)
                if cleaned_section.strip():
                    # If section is too large, split it further
                    if len(cleaned_section) > self.max_chunk_size:
                        sub_chunks = self._split_large_section(cleaned_section)
                        for sub_idx, sub_chunk in enumerate(sub_chunks):
                            chunk = self._create_chunk(sub_chunk, f"{idx+1}.{sub_idx+1}")
                            chunks.append(chunk)
                    else:
                        chunk = self._create_chunk(cleaned_section, str(idx+1))
                        chunks.append(chunk)
        
        print(f"   Created {len(chunks)} chunks")
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """Split text by sections"""
        # Try splitting by section headings first
        sections = re.split(f'({self.section_patterns["section_heading"]})', text)
        
        # Combine heading markers with following content
        combined_sections = []
        i = 0
        while i < len(sections):
            section = sections[i].strip()
            if not section:
                i += 1
                continue
                
            if re.match(self.section_patterns['section_heading'], section):
                if i + 1 < len(sections):
                    next_section = sections[i + 1].strip()
                    combined_sections.append(section + '\n' + next_section)
                    i += 2
                else:
                    combined_sections.append(section)
                    i += 1
            else:
                combined_sections.append(section)
                i += 1
        
        # If we didn't get good results, try paragraph splitting
        if len(combined_sections) <= 1:
            combined_sections = [s.strip() for s in text.split('\n\n') if s.strip()]
        
        return combined_sections
    
    def _split_large_section(self, section: str) -> List[str]:
        """Split large sections into smaller chunks"""
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs
        paragraphs = [p.strip() for p in section.split('\n\n') if p.strip()]
        
        for paragraph in paragraphs:
            test_chunk = current_chunk + '\n\n' + paragraph if current_chunk else paragraph
            
            if len(test_chunk) > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Add overlap from previous chunk
                if self.overlap > 0 and len(current_chunk) > self.overlap:
                    current_chunk = current_chunk[-self.overlap:] + '\n\n' + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk = test_chunk
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean text but preserve important content"""
        # Remove Azure DI tags
        cleaned = re.sub(self.section_patterns['cleanup_tags'], '', text)
        
        # Normalize whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _extract_section_info(self, content: str) -> Dict:
        """Extract section information"""
        # Try numbered section pattern first
        match = re.search(self.section_patterns['numbered_section'], content)
        if match:
            return {
                'section_no': match.group(1),
                'section_name': match.group(2).strip()
            }
        
        # Find first meaningful line
        lines = content.split('\n')
        first_line = None
        
        for line in lines:
            line = line.strip()
            if line and not re.match(r'^\[.*\]$', line):
                first_line = line
                break
        
        if first_line:
            if (first_line.isupper() or 
                re.match(r'^\d+\.?\d*\s+[A-Z]', first_line) or
                len(first_line) < 100):
                return {
                    'section_no': 'auto',
                    'section_name': first_line[:50]
                }
        
        return {
            'section_no': 'unknown',
            'section_name': first_line[:50] if first_line else 'UNKNOWN_SECTION'
        }
    
    def _create_chunk(self, content: str, section_id: str) -> Dict:
        """Create chunk with metadata"""
        section_info = self._extract_section_info(content)
        
        return {
            'chunk_id': str(uuid.uuid4())[:8],
            'section_id': section_id,
            'section_name': section_info['section_name'],
            'section_no': section_info['section_no'],
            'content': content,
            'content_type': 'text',
            'metadata': {
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'word_count': len(content.split()),
                'char_count': len(content),
                'chunk_size': len(content)
            }
        }

class ContentExtractor:
    """Extract and process content from Azure Document Intelligence results"""
    
    def __init__(self):
        self.storage = LocalStorage()
        self.chunker = SimpleChunker()
    
    def extract_all_content(self, result, filename: str, client=None, operation_id=None) -> Dict:
        """Extract text, tables, and images from Azure Document Intelligence result"""
        base_filename = os.path.splitext(filename)[0]
        
        print(f"🔍 Extracting content from {filename}...")
        
        # Extract content using Azure DI
        text_elements = self._extract_text(result)
        tables = self._extract_tables(result, base_filename)
        images = self._extract_images(result, base_filename, client, operation_id)
        
        # Create combined text with role markers
        combined_text = self._combine_text_elements(text_elements)
        print(combined_text)
        section_text = combined_text.split("[ParagraphRole.SECTION_HEADING]")
        processed_sections = []
        for section in section_text:
            section = section.replace("[None] ", "")
            section = section.replace("\n\n", "")
            processed_sections.append(section.strip())
        
        print("Printing processed section:\n\n")
        for section in processed_sections:
            print("\n", section)
        # Create text chunks
        text_chunks = self.chunker.chunk_text(combined_text) if combined_text.strip() else []
        
        # Save content to local storage
        self._save_content(base_filename, combined_text, text_chunks, tables, images)
        
        print(f"✅ Content extraction complete:")
        print(f"   📝 Text chunks: {len(text_chunks)}")
        print(f"   📊 Tables: {len(tables)}")
        print(f"   🖼️ Images: {len(images)}")
        
        return {
            "text": combined_text,
            "text_chunks": text_chunks,
            "tables": tables,
            "images": images,
            "raw_text": combined_text,
            "stats": {
                "text_count": len(text_chunks),
                "table_count": len(tables),
                "image_count": len(images)
            }
        }
    
    def _extract_text(self, result) -> List[Dict]:
        """Extract text content excluding tables and figures"""
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
                        "role": getattr(paragraph, "role", "unknown"),
                        "page_number": getattr(paragraph.bounding_regions[0], 'page_number', 1) if paragraph.bounding_regions else 1,
                        "paragraph_index": para_idx + 1
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
                            "column_count": len(df.columns),
                            "table_index": table_idx + 1
                        })
                except Exception as e:
                    print(f"❌ Error processing table {table_idx + 1}: {e}")
                    continue
        
        return tables
    
    def _extract_images(self, result, base_filename: str, client=None, operation_id=None) -> List[Dict]:
        """Extract figures/images"""
        images = []
        
        if hasattr(result, 'figures') and result.figures:
            for fig_idx, figure in enumerate(result.figures):
                try:
                    # Extract text content from figure
                    text_content = self._extract_figure_content(figure, result)
                    page_number = getattr(figure.bounding_regions[0], 'page_number', 1) if figure.bounding_regions else 1
                    
                    image_data = {
                        "content": text_content or f"Figure from page {page_number}",
                        "page_number": page_number,
                        "figure_index": fig_idx + 1,
                        "type": "figure",
                        "image_path": None,
                        "image_base64": None,
                        "width": None,
                        "height": None
                    }
                    
                    # Try to extract actual image
                    if figure.id and client and operation_id:
                        try:
                            image_response = client.get_analyze_result_figure(
                                model_id=result.model_id,
                                result_id=operation_id,
                                figure_id=figure.id
                            )
                            
                            image_bytes = b''.join(image_response)
                            
                            if image_bytes:
                                image_path = self.storage.save_figure_image_bytes(
                                    image_bytes, 
                                    base_filename, 
                                    fig_idx + 1
                                )
                                
                                if image_path:
                                    import base64
                                    img_base64 = base64.b64encode(image_bytes).decode()
                                    
                                    image_data.update({
                                        "image_path": image_path,
                                        "image_base64": img_base64,
                                        "type": "figure_with_image"
                                    })
                                    
                                    # Get image dimensions
                                    try:
                                        from PIL import Image
                                        from io import BytesIO
                                        img = Image.open(BytesIO(image_bytes))
                                        image_data.update({
                                            "width": img.width,
                                            "height": img.height
                                        })
                                    except:
                                        pass
                                
                                print(f"✅ Extracted image for figure {fig_idx + 1}")
                                
                        except Exception as e:
                            print(f"❌ Error extracting image for figure {fig_idx + 1}: {e}")
                    
                    # Save text content if available
                    if text_content and text_content.strip():
                        self.storage.save_figure_text(text_content, base_filename, fig_idx + 1)
                    
                    images.append(image_data)
                    
                except Exception as e:
                    print(f"❌ Error processing figure {fig_idx + 1}: {e}")
                    continue
        
        return images
    
    def _combine_text_elements(self, text_elements: List[Dict]) -> str:
        """Combine text elements with role markers"""
        if not text_elements:
            return ""
        
        combined_parts = []
        for element in text_elements:
            role = element.get('role', 'unknown')
            content = element.get('content', '')
            if content.strip():
                combined_parts.append(f"[{role}] {content}")
        
        return "\n\n".join(combined_parts)
    
    def _save_content(self, base_filename: str, raw_text: str, text_chunks: List[Dict], tables: List[Dict], images: List[Dict]):
        """Save extracted content to local storage"""
        # Save raw text
        if raw_text.strip():
            self.storage.save_raw_text(raw_text, base_filename)
        
        # Save text chunks
        if text_chunks:
            self.storage.save_text_chunks(text_chunks, base_filename)
        
        print(f"💾 Saved content to local storage:")
        print(f"   📝 Raw text: {base_filename}_raw_text.txt")
        print(f"   🧩 Text chunks: {base_filename}_text_chunks.json")
        print(f"   📊 Tables: {len(tables)} CSV files")
        print(f"   🖼️ Images: {len(images)} image files")
    
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
            df = pd.DataFrame(grid[1:], columns=grid[0])
        else:
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