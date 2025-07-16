import pandas as pd
from typing import Dict, List, Optional
from .azure_openai_client import AzureOpenAIClient

class MultimodalVerbalizer:
    """Converts tables and images to descriptive text for context-rich chunking"""
    
    def __init__(self):
        self.llm_client = AzureOpenAIClient()
    
    def verbalize_table(self, table_df: pd.DataFrame, context: str = "") -> str:
        """Convert table to descriptive text"""
        
        if table_df.empty:
            return "[TABLE]: Empty table"
        
        # Create basic table description
        basic_description = self._create_basic_table_description(table_df)
        
        # Enhanced description using LLM for complex tables
        if len(table_df) > 2 and len(table_df.columns) > 2:
            enhanced_description = self._create_enhanced_table_description(table_df, context, basic_description)
            return enhanced_description if enhanced_description else basic_description
        
        return basic_description
    
    def verbalize_image(self, image_content: str, context: str = "") -> str:
        """Convert image content to descriptive text"""
        
        if not image_content or image_content.strip() == "":
            return "[FIGURE]: Image with no extractable text content"
        
        # If content is already descriptive, enhance it
        if len(image_content) > 50:
            enhanced_description = self._create_enhanced_image_description(image_content, context)
            return enhanced_description if enhanced_description else f"[FIGURE]: {image_content}"
        
        return f"[FIGURE]: {image_content}"
    
    def integrate_verbalized_content(self, text: str, verbalized_items: List[Dict]) -> str:
        """Integrate verbalized tables and images into text content"""
        
        if not verbalized_items:
            return text
        
        # Sort items by their original position/page for logical placement
        sorted_items = sorted(verbalized_items, key=lambda x: x.get('page_number', 0))
        
        integrated_content = text
        
        for item in sorted_items:
            verbalized_text = item.get('verbalized_content', '')
            item_type = item.get('type', 'content')
            
            if verbalized_text:
                # Add verbalized content with clear separation
                integrated_content += f"\n\n{verbalized_text}"
        
        return integrated_content
    
    def create_section_with_multimodal_content(self, section_text: str, tables: List[Dict], images: List[Dict]) -> str:
        """Create enhanced section content with integrated multimodal elements"""
        
        verbalized_items = []
        
        # Verbalize tables
        for table in tables:
            if 'csv_path' in table and 'html' in table:
                try:
                    # Use the DataFrame if available, otherwise parse from CSV
                    df = pd.read_csv(table['csv_path']) if table.get('csv_path') else pd.DataFrame()
                    
                    verbalized_content = self.verbalize_table(
                        df, 
                        context=f"Table from page {table.get('page_number', 'unknown')}"
                    )
                    
                    verbalized_items.append({
                        'type': 'table',
                        'page_number': table.get('page_number', 0),
                        'verbalized_content': verbalized_content,
                        'original_content': table.get('content', '')
                    })
                    
                except Exception as e:
                    print(f"⚠️ Error verbalizing table: {e}")
                    # Fallback to basic content
                    verbalized_items.append({
                        'type': 'table',
                        'page_number': table.get('page_number', 0),
                        'verbalized_content': f"[TABLE]: {table.get('content', 'Table content unavailable')}",
                        'original_content': table.get('content', '')
                    })
        
        # Verbalize images
        for image in images:
            verbalized_content = self.verbalize_image(
                image.get('content', ''),
                context=f"Figure from page {image.get('page_number', 'unknown')}"
            )
            
            verbalized_items.append({
                'type': 'image',
                'page_number': image.get('page_number', 0),
                'verbalized_content': verbalized_content,
                'original_content': image.get('content', '')
            })
        
        # Integrate all content
        enhanced_content = self.integrate_verbalized_content(section_text, verbalized_items)
        
        return enhanced_content
    
    def _create_basic_table_description(self, df: pd.DataFrame) -> str:
        """Create basic table description without LLM"""
        
        rows, cols = df.shape
        
        description = f"[TABLE]: This table contains {rows} rows and {cols} columns"
        
        # Add column information
        if len(df.columns) <= 6:  # Only list columns if not too many
            columns = ', '.join([str(col) for col in df.columns])
            description += f" with columns: {columns}"
        
        # Add sample data for small tables
        if rows <= 3 and cols <= 4:
            try:
                sample_data = []
                for _, row in df.head(3).iterrows():
                    row_data = [str(val) for val in row.values]
                    sample_data.append(' | '.join(row_data))
                
                if sample_data:
                    description += f". Sample data: {'; '.join(sample_data)}"
            except:
                pass
        
        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            try:
                total_values = []
                for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                    col_sum = df[col].sum()
                    if not pd.isna(col_sum) and col_sum != 0:
                        total_values.append(f"{col}: {col_sum:,.0f}")
                
                if total_values:
                    description += f". Key totals: {', '.join(total_values)}"
            except:
                pass
        
        return description
    
    def _create_enhanced_table_description(self, df: pd.DataFrame, context: str, basic_description: str) -> Optional[str]:
        """Create enhanced table description using LLM"""
        
        try:
            # Create a concise table representation for LLM
            table_sample = self._create_table_sample_for_llm(df)
            
            system_message = """You are an expert at describing tables in RFP documents. 
            Create a clear, informative description that captures the table's purpose and key information.
            
            Focus on:
            1. What the table shows (purpose/content)
            2. Key data points or patterns
            3. Important totals, ranges, or categories
            4. Business relevance in RFP context
            
            Keep the description concise but informative (2-3 sentences).
            Start with "[TABLE]:" and write in a natural, descriptive style."""
            
            user_prompt = f"""Context: {context}

Table structure: {df.shape[0]} rows, {df.shape[1]} columns
Columns: {', '.join([str(col) for col in df.columns])}

Sample data:
{table_sample}

Create a descriptive summary of this table."""
            
            enhanced_description = self.llm_client.get_completion(user_prompt, system_message)
            
            # Validate the response
            if enhanced_description and len(enhanced_description) > len(basic_description) * 0.8:
                return enhanced_description.strip()
            
        except Exception as e:
            print(f"⚠️ Error creating enhanced table description: {e}")
        
        return None
    
    def _create_enhanced_image_description(self, image_content: str, context: str) -> Optional[str]:
        """Create enhanced image description using LLM"""
        
        try:
            system_message = """You are an expert at describing figures and diagrams in RFP documents.
            Based on the text content extracted from an image/figure, create a clear description.
            
            Focus on:
            1. What type of figure it is (diagram, chart, layout, etc.)
            2. Key elements or components shown
            3. Purpose or function in the RFP context
            4. Important details or specifications
            
            Keep the description clear and informative (1-2 sentences).
            Start with "[FIGURE]:" and write in a descriptive style."""
            
            user_prompt = f"""Context: {context}

Text extracted from figure: {image_content}

Create a descriptive summary of what this figure shows."""
            
            enhanced_description = self.llm_client.get_completion(user_prompt, system_message)
            
            # Validate the response
            if enhanced_description and len(enhanced_description.strip()) > 20:
                return enhanced_description.strip()
            
        except Exception as e:
            print(f"⚠️ Error creating enhanced image description: {e}")
        
        return None
    
    def _create_table_sample_for_llm(self, df: pd.DataFrame, max_rows: int = 5) -> str:
        """Create a concise table sample for LLM analysis"""
        
        # Take first few rows and important columns
        sample_df = df.head(max_rows)
        
        # If too many columns, select the most important ones
        if len(df.columns) > 6:
            # Try to keep first, last, and any numeric columns
            important_cols = []
            important_cols.append(df.columns[0])  # First column
            
            # Add numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            for col in numeric_cols[:3]:  # Up to 3 numeric columns
                if col not in important_cols:
                    important_cols.append(col)
            
            # Add last column if not already included
            if df.columns[-1] not in important_cols and len(important_cols) < 5:
                important_cols.append(df.columns[-1])
            
            sample_df = sample_df[important_cols]
        
        # Convert to string representation
        return sample_df.to_string(index=False, max_cols=6, max_rows=max_rows)
    
    def get_content_type_from_verbalization(self, has_tables: bool, has_images: bool) -> str:
        """Determine content type based on multimodal content presence"""
        
        if has_tables and has_images:
            return "text_with_multimodal"
        elif has_tables:
            return "text_with_table"
        elif has_images:
            return "text_with_image"
        else:
            return "text"
    
    def create_verbalization_summary(self, tables: List[Dict], images: List[Dict]) -> Dict:
        """Create summary of verbalization process"""
        
        summary = {
            "total_tables_verbalized": len(tables),
            "total_images_verbalized": len(images),
            "verbalization_details": {
                "tables": [],
                "images": []
            }
        }
        
        # Table details
        for i, table in enumerate(tables):
            table_info = {
                "index": i + 1,
                "page_number": table.get("page_number", "unknown"),
                "rows": table.get("row_count", 0),
                "columns": table.get("column_count", 0),
                "verbalization_method": "enhanced" if table.get("row_count", 0) > 2 else "basic"
            }
            summary["verbalization_details"]["tables"].append(table_info)
        
        # Image details
        for i, image in enumerate(images):
            image_info = {
                "index": i + 1,
                "page_number": image.get("page_number", "unknown"),
                "content_length": len(image.get("content", "")),
                "has_extractable_text": len(image.get("content", "").strip()) > 0,
                "verbalization_method": "enhanced" if len(image.get("content", "")) > 50 else "basic"
            }
            summary["verbalization_details"]["images"].append(image_info)
        
        return summary