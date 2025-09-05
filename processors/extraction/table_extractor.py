

import os
import pandas as pd
import uuid
from datetime import datetime
from typing import List, Dict
# from storage.local_storage import LocalStorage
from storage.storage_factory import get_storage_instance
from processors.content_verbalizer import ContentVerbalizer
import asyncio


class TableExtractor:
    """Handle table extraction and chunking logic"""
    
    def __init__(self):
        # self.storage = LocalStorage()
        self.storage = get_storage_instance()
        self.verbalizer = ContentVerbalizer()

    def extract_tables(self, result, base_filename: str, section_mapper,storage=None) -> List[Dict]:
        """Extract and save tables using Azure Document Intelligence with section association"""
        tables = []
        
        if hasattr(result, 'tables') and result.tables:
            for table_idx, table in enumerate(result.tables):
                try:
                    df = self._table_to_dataframe(table)
                    if not df.empty:
                        
                        if storage:
                            csv_path = storage.save_table(df, base_filename, table_idx + 1)
                        else:
                            csv_path = self.storage.save_table(df, base_filename, table_idx + 1)
                        
                        # Get table position and find closest section
                        table_page = getattr(table.bounding_regions[0], 'page_number', 1) if table.bounding_regions else 1
                        table_position = self._get_table_position(table)
                        section_info = section_mapper.find_closest_section(table_page, table_position, [])  # Will need text_elements
                        
                        tables.append({
                            "content": df.to_string(index=False),
                            "html": df.to_html(index=False, classes="table table-striped"),
                            "csv_path": csv_path,
                            "page_number": table_page,
                            "row_count": len(df),
                            "column_count": len(df.columns),
                            "table_index": table_idx + 1,
                            "section_info": section_info,
                            "position": table_position
                        })
                except Exception as e:
                    print(f"Error processing table {table_idx + 1}: {e}")
                    continue
        
        return tables
    
    # async def create_table_chunks(self, tables: List[Dict], base_filename: str, document_metadata: Dict, section_mapper, text_elements: List[Dict], rfp_id: str = None) -> List[Dict]:
    async def create_table_chunks(self, tables: List[Dict], base_filename: str, document_metadata: Dict, section_mapper, text_elements: List[Dict], rfp_id: str = None, project_id: str = None) -> List[Dict]:
        """Create chunks for tables with ASYNC verbalization, section mapping, and LLM metadata"""
        table_chunks = []
       
        # Create a list of tasks for concurrent verbalization
        verbalization_tasks = []
        table_data_list = []
       
        for idx, table in enumerate(tables):
            try:
                # Get section info from closest text chunk
                section_mapping = section_mapper.get_section_info_from_closest_text_chunk(
                    table.get('page_number', 1),
                    table.get('position', {}),
                    text_elements
                )
               
                # Store table data and section mapping for later use
                table_info = {
                    'table': table,
                    'idx': idx,
                    'section_mapping': section_mapping,
                    'base_filename': base_filename,
                    'document_metadata': document_metadata
                }
                table_data_list.append(table_info)
               
                # Add verbalization task to concurrent execution
                verbalization_tasks.append(self.verbalizer.verbalize_table(table))
               
            except Exception as e:
                print(f"   ❌ Error preparing table chunk {idx + 1}: {e}")
                continue
       
        # Execute all verbalizations concurrently
        if verbalization_tasks:
            print(f"🤖 Running {len(verbalization_tasks)} table verbalizations concurrently...")
            try:
                verbalized_contents = await asyncio.gather(*verbalization_tasks, return_exceptions=True)
            except Exception as e:
                print(f"❌ Error in concurrent verbalization: {e}")
                verbalized_contents = [f"Error verbalizing table {i+1}" for i in range(len(verbalization_tasks))]
        else:
            verbalized_contents = []
       
        # Create chunks with verbalized content
        for i, table_info in enumerate(table_data_list):
            try:
                table = table_info['table']
                idx = table_info['idx']
                section_mapping = table_info['section_mapping']
                document_metadata = table_info['document_metadata']
               
                # Get verbalized content (handle exceptions from gather)
                if i < len(verbalized_contents) and not isinstance(verbalized_contents[i], Exception):
                    verbalized_content = verbalized_contents[i]
                else:
                    print(f"⚠️ Verbalization failed for table {idx + 1}, using fallback")
                    verbalized_content = f"Table from page {table.get('page_number', 'unknown')}"
               
                # Use LLM-extracted metadata for chunk creation
                file_name = document_metadata.get('project_title', base_filename)
                if file_name == 'Not Specified':
                    file_name = base_filename
                elif len(file_name) > 50:
                    file_name = file_name[:50]
               
                domain = document_metadata.get('domain_category', 'none')
                if domain == 'Not Specified' or domain == 'Other':
                    domain = 'none'
               
                vendor_name = document_metadata.get('vendor_name', 'tetratech')
                if vendor_name == 'Not Specified':
                    vendor_name = 'tetratech'
               
                # Create table chunk with LLM metadata integration
                chunk = {
                    'chunk_id': str(uuid.uuid4())[:8],
                    'file_name': file_name,
                    'project_id': project_id,
                    'section_name': section_mapping['section_name'],  # From closest text chunk
                    'section_no': section_mapping['section_no'],      # From closest text chunk
                    'domain': domain,                                  # From LLM extraction
                    'content_type': 'table',
                    'author': vendor_name,                             # From LLM extraction (vendor_name)
                    'content': table.get('content', ''),
                    'verbalized_content': verbalized_content,  # AI-generated description (ASYNC)
                    'rfp_id': rfp_id,  # RFP ID extracted from document
                    'metadata': {
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'chunk_index': idx,
                        'word_count': len(verbalized_content.split()),
                        'char_count': len(verbalized_content),
                        'table_info': {
                            'page_number': table.get('page_number', 1),
                            'row_count': table.get('row_count', 0),
                            'column_count': table.get('column_count', 0),
                            'csv_path': table.get('csv_path', ''),
                            'section_info': table.get('section_info', {})
                        },
                        # Store LLM-extracted metadata for reference
                        'llm_extracted_metadata': document_metadata
                    }
                }
               
                table_chunks.append(chunk)
                print(f"   ✅ Created table chunk {idx + 1} with ASYNC verbalization - Author: {vendor_name}, Domain: {domain}")
               
            except Exception as e:
                print(f"   ❌ Error creating table chunk {i + 1}: {e}")
                continue
       
        return table_chunks

    def _get_table_position(self, table):
        """Get table position from bounding regions"""
        if hasattr(table, 'bounding_regions') and table.bounding_regions:
            bounding_region = table.bounding_regions[0]
            if hasattr(bounding_region, 'polygon') and bounding_region.polygon:
                polygon = bounding_region.polygon
                if len(polygon) >= 2:
                    return {
                        "x": polygon[0],
                        "y": polygon[1],
                        "page": getattr(bounding_region, 'page_number', 1)
                    }
        return {"x": 0, "y": 0, "page": 1}
    
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