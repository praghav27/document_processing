import os
import pandas as pd
from typing import List, Dict
from utils.helpers import semantic_chunking
from storage.local_storage import LocalStorage
import re
import uuid
from datetime import datetime

import re
import uuid
from datetime import datetime
# ...existing imports...

import re
import uuid
from datetime import datetime

class SimpleChunker:
    def __init__(self):
        self.section_patterns = {
            'section_heading': r'\[ParagraphRole\.SECTION_HEADING\]',
            'numbered_section': r'^\s*(\d+\.\d+)\s+([A-Z\s]+)',
            'cleanup_tags': r'\[None\]\s*|\[ParagraphRole\.[^\]]+\]'
        }
    
    def chunk_text(self, text: str) -> list:
        print(f"DEBUG: Input text length: {len(text)}")
        print(f"DEBUG: First 200 chars: {repr(text[:200])}")
        
        chunks = []
        
        # First, let's see what we're working with
        section_heading_matches = re.findall(self.section_patterns['section_heading'], text)
        print(f"DEBUG: Found {len(section_heading_matches)} section headings")
        
        # Split by sections but keep the delimiter
        sections = self._split_by_sections_improved(text)
        print(f"DEBUG: Split into {len(sections)} sections")
        
        for idx, section in enumerate(sections):
            print(f"DEBUG: Section {idx + 1} length: {len(section)}")
            print(f"DEBUG: Section {idx + 1} preview: {repr(section[:100])}")
            
            if section.strip():
                # Clean the section after splitting
                cleaned_section = self._clean_text(section)
                if cleaned_section.strip():  # Check again after cleaning
                    chunk = self._create_chunk(cleaned_section, idx)
                    chunks.append(chunk)
                    print(f"DEBUG: Created chunk {idx + 1} with {len(cleaned_section)} chars")
                else:
                    print(f"DEBUG: Section {idx + 1} became empty after cleaning")
            else:
                print(f"DEBUG: Section {idx + 1} was empty")
        
        print(f"DEBUG: Total chunks created: {len(chunks)}")
        return chunks
    
    def _split_by_sections_improved(self, text: str) -> list:
        """Improved section splitting that preserves content"""
        # Method 1: Try splitting with the section heading pattern
        sections = re.split(f'({self.section_patterns["section_heading"]})', text)
        
        # Remove empty sections and combine heading markers with following content
        combined_sections = []
        i = 0
        while i < len(sections):
            section = sections[i].strip()
            if not section:
                i += 1
                continue
                
            # If this is a section heading marker, combine with next section
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
        
        # If we didn't get good results, try alternative splitting
        if len(combined_sections) <= 1:
            # Fallback: split by double newlines or paragraph markers
            fallback_sections = re.split(r'\n\s*\n|\[ParagraphRole\.[^\]]+\]', text)
            combined_sections = [s.strip() for s in fallback_sections if s.strip()]
        
        return combined_sections
    
    def _clean_text(self, text: str) -> str:
        """Clean text but preserve important content"""
        # Remove cleanup tags but be more careful
        cleaned = re.sub(self.section_patterns['cleanup_tags'], '', text)
        
        # Normalize whitespace but don't be too aggressive
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 newlines
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Normalize spaces
        
        return cleaned.strip()
    
    def _extract_section_info(self, content: str) -> dict:
        """Extract section information with better fallbacks"""
        # Try numbered section pattern first
        match = re.search(self.section_patterns['numbered_section'], content)
        if match:
            return {
                'section_no': match.group(1),
                'section_name': match.group(2).strip()
            }
        
        # Try to find other patterns
        lines = content.split('\n')
        first_meaningful_line = None
        
        for line in lines:
            line = line.strip()
            if line and not re.match(r'^\[.*\]$', line):  # Skip tag-only lines
                first_meaningful_line = line
                break
        
        if first_meaningful_line:
            # Check if it looks like a section header
            if (first_meaningful_line.isupper() or 
                re.match(r'^\d+\.?\d*\s+[A-Z]', first_meaningful_line) or
                len(first_meaningful_line) < 100):
                return {
                    'section_no': 'auto',
                    'section_name': first_meaningful_line[:50]
                }
        
        return {
            'section_no': 'unknown',
            'section_name': first_meaningful_line[:50] if first_meaningful_line else 'UNKNOWN_SECTION'
        }
    
    def _create_chunk(self, content: str, idx: int) -> dict:
        section_info = self._extract_section_info(content)
        chunk = {
            'chunk_id': str(uuid.uuid4())[:8],
            'file_name': 'none',
            'section_name': section_info['section_name'],
            'section_no': section_info['section_no'],
            'domain': 'none',
            'content_type': 'text',
            'author': 'tetratech',
            'content': content,
            'metadata': {
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'chunk_index': idx,
                'word_count': len(content.split()),
                'char_count': len(content)
            }
        }
        return chunk
    
    def print_chunks(self, chunks: list):
        print(f"\n{'='*80}")
        print(f"CHUNKING RESULTS - Total chunks: {len(chunks)}")
        print(f"{'='*80}")
        
        if not chunks:
            print("⚠️  NO CHUNKS WERE CREATED!")
            print("This might indicate issues with:")
            print("- Section splitting regex patterns")
            print("- Text cleaning removing too much content")
            print("- Input text format not matching expected patterns")
            return
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- CHUNK {i} ---")
            print(f"ID: {chunk['chunk_id']}")
            print(f"File: {chunk['file_name']}")
            print(f"Section: {chunk['section_no']} - {chunk['section_name']}")
            print(f"Domain: {chunk['domain']}")
            print(f"Content Type: {chunk['content_type']}")
            print(f"Author: {chunk['author']}")
            print(f"Word Count: {chunk['metadata']['word_count']}")
            print(f"Created: {chunk['metadata']['created_at']}")
            print(f"Content Preview: {chunk['content']}...")
            if len(chunk['content']) > 150:
                print(f"... (truncated, total length: {len(chunk['content'])} chars)")
            print(f"-" * 60)
    def debug_text_analysis(self, text: str):
        """Debug method to analyze the input text"""
        print(f"\n{'='*60}")
        print("TEXT ANALYSIS DEBUG")
        print(f"{'='*60}")
        print(f"Total text length: {len(text)} characters")
        print(f"Total lines: {len(text.split(chr(10)))}")
        
        # Check for section headings
        section_headings = re.findall(self.section_patterns['section_heading'], text)
        print(f"Section headings found: {len(section_headings)}")
        
        # Check for numbered sections
        numbered_sections = re.findall(self.section_patterns['numbered_section'], text, re.MULTILINE)
        print(f"Numbered sections found: {len(numbered_sections)}")
        
        # Show some examples
        print("\nFirst 500 characters:")
        print(repr(text[:500]))
        
        print("\nLast 500 characters:")
        print(repr(text[-500:]))
        
        if section_headings:
            print(f"\nSection heading examples: {section_headings[:3]}")
        
        if numbered_sections:
            print(f"\nNumbered section examples: {numbered_sections[:3]}")
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
        # all_text = "\n\n".join([elem["content"] for elem in text_elements])
        # Include role in the output text
        all_text = "\n\n".join(
            [f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in text_elements]
        )
        # text_chunks = semantic_chunking(all_text)
        
        # Save text content to local storage
        # if text_chunks:
        #     self.storage.save_text_chunks(text_chunks, base_filename)
        if all_text.strip():
            self.storage.save_raw_text(all_text, base_filename)
        
        # print(all_text)
        section_text = all_text.split("[ParagraphRole.SECTION_HEADING]")
        processed_sections = []
        for section in section_text:
            section = section.replace("[None] ", "")
            section = section.replace("\n\n", "")
            processed_sections.append(section.strip())
        
        print("Printing processed section:\n\n")
        for section in processed_sections:
            print("\n", section)

        # In your ContentExtractor class, update the chunking section:
        chunker = SimpleChunker()

        # For debugging, first analyze the text
        chunker.debug_text_analysis(all_text)

        # Then create chunks
        chunks = chunker.chunk_text(all_text)
        chunker.print_chunks(chunks)
        # chunker = SimpleChunker()
        # chunks = chunker.chunk_text(all_text)
        # chunker.print_chunks(chunks)
        
        return {
            "text": all_text,
            "tables": tables,
            "images": figures,  # Renamed for consistency with existing UI
            "raw_text": all_text,
            "stats": {
                "text_count": 1 if all_text.strip() else 0,
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
                        "role": getattr(paragraph, "role", "unknown"),
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