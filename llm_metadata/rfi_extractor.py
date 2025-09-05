
# import json
# import re
# from typing import Dict, List
# from .prompts import DocumentMetadataPrompts
# from processors.content_verbalizer import ContentVerbalizer

# class RFIExtractor:
#     """Extract RFI metadata (8 fields) from documents using Azure OpenAI - Enhanced with first page content"""
   
#     def __init__(self):
#         """Initialize RFI extractor with existing Azure OpenAI client"""
#         self.verbalizer = ContentVerbalizer()  # Reuse existing client
#         self.rfi_fields = [
#             'project_name', 'client', 'region', 'industry', 
#             'prepared_date', 'station_discipline', 'scope_of_work', 'required_activities'
#         ]
      
#         print("✅ Enhanced RFI Extractor initialized - WITH FIRST PAGE CONTENT")
#         print(f"   📊 Fields: {len(self.rfi_fields)} RFI metadata fields")
#         print(f"   🚫 Chunking: DISABLED for RFI documents")
#         print(f"   📄 First Page: ENABLED - extracts all content from page 1")
   
#     async def extract_metadata_only(self, text_elements: List[Dict], azure_di_result=None) -> Dict:
#         """
#         Extract ONLY RFI metadata (8 fields) from complete document text elements + first page content
#         NO CHUNKING - Only metadata extraction for indexing
#         """
#         try:
#             print("🔍 Enhanced RFI metadata extraction (DI text + First page content)")
           
#             # Step 1: Convert text elements to complete document text (existing)
#             complete_document_text = self._prepare_complete_document_text(text_elements)
#             print(f"📄 Document Intelligence extracted text: {len(complete_document_text)} characters")
           
#             # Step 2: NEW - Extract first page comprehensive content
#             first_page_content = ""
#             if azure_di_result:
#                 first_page_content = self._extract_first_page_comprehensive_content(azure_di_result)
#                 print(f"📄 First page comprehensive content: {len(first_page_content)} characters")
#             else:
#                 print("⚠️ No Azure DI result provided - skipping first page extraction")
           
#             # Step 3: Combine both contents
#             if first_page_content:
#                 combined_content = f"""=== DOCUMENT INTELLIGENCE EXTRACTED TEXT ===
# {complete_document_text}

# === FIRST PAGE COMPREHENSIVE CONTENT ===
# {first_page_content}"""
#                 print(f"🔗 Combined content: {len(combined_content)} characters")
#             else:
#                 combined_content = complete_document_text
#                 print(f"📝 Using DI text only: {len(combined_content)} characters")
           
#             if not combined_content.strip():
#                 print("⚠️ No text found in document, using RFI defaults")
#                 return self._get_rfi_default_metadata()
           
#             print(f"📊 Content prepared for LLM analysis:")
#             print(f"   📄 Pages processed: {self._count_pages(text_elements)}")
#             print(f"   📝 Total content length: {len(combined_content)} characters")
#             print(f"   🎯 Ready for enhanced metadata extraction")
           
#             # Step 4: Generate metadata using Azure OpenAI with combined content
#             if self.verbalizer.client:
#                 metadata = await self._extract_metadata_with_azure_openai(combined_content)
#             else:
#                 print("❌ Azure OpenAI client not available")
#                 return self._get_rfi_default_metadata()
           
#             # Step 5: Validate and clean metadata for RFI (8 fields)
#             validated_metadata = self._validate_rfi_metadata(metadata)
           
#             print("✅ Enhanced RFI metadata extraction completed (DI + First Page)")
#             return validated_metadata
           
#         except Exception as e:
#             print(f"❌ Error extracting enhanced RFI metadata: {e}")
#             return self._get_rfi_default_metadata()

#     def _extract_first_page_comprehensive_content(self, azure_di_result) -> str:
#         """
#         Extract ALL content from the first page of the document
#         Includes: text paragraphs, tables, and figures from page 1
#         """
#         try:
#             first_page_content = []
            
#             print("🔍 Extracting comprehensive first page content...")
            
#             # Extract text from page 1 paragraphs
#             if hasattr(azure_di_result, 'paragraphs') and azure_di_result.paragraphs:
#                 page_1_paragraphs = []
#                 for paragraph in azure_di_result.paragraphs:
#                     try:
#                         # Get page number safely
#                         page_num = 1
#                         if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
#                             page_num = getattr(paragraph.bounding_regions[0], 'page_number', 1)
                        
#                         if page_num == 1:  # Only first page
#                             content = getattr(paragraph, 'content', '')
#                             role = getattr(paragraph, 'role', 'paragraph')
#                             if content and content.strip():
#                                 page_1_paragraphs.append(f"[{role}] {content.strip()}")
#                     except Exception as e:
#                         continue
                
#                 if page_1_paragraphs:
#                     first_page_content.append("=== PAGE 1 TEXT CONTENT ===")
#                     first_page_content.extend(page_1_paragraphs)
#                     print(f"📝 Extracted {len(page_1_paragraphs)} paragraphs from page 1")
            
#             # Extract tables from page 1
#             if hasattr(azure_di_result, 'tables') and azure_di_result.tables:
#                 page_1_tables = []
#                 for idx, table in enumerate(azure_di_result.tables):
#                     try:
#                         # Get page number from table
#                         table_page = 1
#                         if hasattr(table, 'bounding_regions') and table.bounding_regions:
#                             table_page = getattr(table.bounding_regions[0], 'page_number', 1)
                        
#                         if table_page == 1:  # Only first page
#                             # Convert table to text representation
#                             table_text = self._convert_table_to_text(table)
#                             if table_text:
#                                 page_1_tables.append(f"[TABLE_{idx+1}] {table_text}")
#                     except Exception as e:
#                         continue
                
#                 if page_1_tables:
#                     first_page_content.append("\n=== PAGE 1 TABLES ===")
#                     first_page_content.extend(page_1_tables)
#                     print(f"📊 Extracted {len(page_1_tables)} tables from page 1")
            
#             # Extract figures/images from page 1
#             if hasattr(azure_di_result, 'figures') and azure_di_result.figures:
#                 page_1_figures = []
#                 for idx, figure in enumerate(azure_di_result.figures):
#                     try:
#                         # Get page number from figure
#                         figure_page = 1
#                         if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
#                             figure_page = getattr(figure.bounding_regions[0], 'page_number', 1)
                        
#                         if figure_page == 1:  # Only first page
#                             # Extract figure text content
#                             figure_text = self._extract_figure_content(figure, azure_di_result)
#                             if figure_text:
#                                 page_1_figures.append(f"[FIGURE_{idx+1}] {figure_text}")
#                             else:
#                                 page_1_figures.append(f"[FIGURE_{idx+1}] Visual content from page 1")
#                     except Exception as e:
#                         continue
                
#                 if page_1_figures:
#                     first_page_content.append("\n=== PAGE 1 FIGURES ===")
#                     first_page_content.extend(page_1_figures)
#                     print(f"🖼️ Extracted {len(page_1_figures)} figures from page 1")
            
#             # Combine all first page content
#             combined_first_page = "\n\n".join(first_page_content)
            
#             print(f"✅ First page comprehensive extraction complete:")
#             print(f"   📄 Total first page content: {len(combined_first_page)} characters")
            
#             return combined_first_page
            
#         except Exception as e:
#             print(f"❌ Error extracting first page content: {e}")
#             return ""

#     def _convert_table_to_text(self, table) -> str:
#         """Convert Azure DI table to text representation"""
#         try:
#             if not hasattr(table, 'cells') or not table.cells:
#                 return ""
            
#             # Create a grid structure
#             max_row = max(cell.row_index for cell in table.cells) + 1
#             max_col = max(cell.column_index for cell in table.cells) + 1
            
#             # Initialize grid
#             grid = [["" for _ in range(max_col)] for _ in range(max_row)]
            
#             # Fill grid with cell content
#             for cell in table.cells:
#                 content = getattr(cell, 'content', '').strip()
#                 if content:
#                     grid[cell.row_index][cell.column_index] = content
            
#             # Convert grid to text
#             table_lines = []
#             for row in grid:
#                 if any(cell.strip() for cell in row):  # Skip empty rows
#                     row_text = " | ".join(cell.strip() for cell in row)
#                     table_lines.append(row_text)
            
#             return "\n".join(table_lines)
            
#         except Exception as e:
#             print(f"⚠️ Error converting table to text: {e}")
#             return ""

#     def _extract_figure_content(self, figure, result) -> str:
#         """Extract text content from figure using spans"""
#         try:
#             if hasattr(figure, 'spans') and figure.spans and hasattr(result, 'content'):
#                 content_parts = []
#                 for span in figure.spans:
#                     try:
#                         span_content = result.content[span.offset:span.offset + span.length]
#                         if span_content.strip():
#                             content_parts.append(span_content.strip())
#                     except:
#                         continue
#                 return " ".join(content_parts)
#             return ""
#         except Exception as e:
#             return ""
   
#     def _prepare_complete_document_text(self, text_elements: List[Dict]) -> str:
#         """Convert text elements to complete document text"""
#         complete_text = ""
      
#         # Process ALL text elements from the complete document
#         for element in text_elements:
#             content = element.get('content', '').strip()
#             role = element.get('role', 'unknown')
          
#             # Add role context for better understanding
#             if content:
#                 complete_text += f"[{role}] {content}\n\n"
      
#         print(f"🔍 Processing {len(text_elements)} text elements from complete document...")
#         return complete_text
  
#     def _count_pages(self, text_elements: List[Dict]) -> str:
#         """Count total pages in document"""
#         pages = set()
#         for element in text_elements:
#             page_num = element.get('page_number', 1)
#             pages.add(page_num)
      
#         total_pages = max(pages) if pages else 1
#         return f"{total_pages}/{total_pages}"
  
#     async def _extract_metadata_with_azure_openai(self, combined_content: str) -> Dict:
#         """Extract RFI metadata using Azure OpenAI API with combined content"""
#         try:
#             print(f"📄 Sending {len(combined_content)} characters to LLM for enhanced RFI analysis")
#             print("🤖 Calling LLM for metadata extraction (DI + First Page)...")
          
#             # Get the RFI-specific prompt with 8 fields
#             prompt = self._get_enhanced_rfi_extraction_prompt(combined_content)
          
#             response = await self.verbalizer.client.chat.completions.create(
#                 model="gpt-4o",  # Use same model as ContentVerbalizer
#                 messages=[
#                     {"role": "system", "content": "You are an expert RFI analyst. Extract the 8 metadata fields for RFI documents from the comprehensive content provided. Return only valid JSON."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 max_tokens=800,  # Sufficient for 8 fields
#                 temperature=0.1  # Low temperature for consistent extraction
#             )
          
#             response_text = response.choices[0].message.content.strip()
#             print(f"📝 LLM response: {len(response_text)} characters")
          
#             # Clean and parse JSON response
#             metadata = self._parse_json_response(response_text)
          
#             print("✅ Successfully parsed enhanced metadata from LLM")
#             return metadata
              
#         except Exception as e:
#             print(f"❌ Azure OpenAI API error: {e}")
#             return self._get_rfi_default_metadata()

#     def _get_enhanced_rfi_extraction_prompt(self, combined_content: str) -> str:
#         """Get the enhanced RFI metadata extraction prompt for 8 fields with combined content"""
#         return f"""
# You are an expert RFI (Request for Information) analyzer. Extract EXACTLY 8 metadata fields from the comprehensive document content provided below. Return ONLY a valid JSON object.

# **IMPORTANT**: The content below includes:
# 1. Document Intelligence extracted text (structured text elements)
# 2. First page comprehensive content (all text, tables, and figures from page 1)

# Use ALL this information to extract the most accurate metadata.

# **COMBINED DOCUMENT CONTENT:**
# {combined_content}

# **EXTRACTION REQUIREMENTS:**

# 1. **project_name**: You are an expert document analyzer specializing in Technical Information Packages (TIP) and engineering documents.

# Your task is to extract ONLY the explicit Project Name from the document content.

# SEARCH LOCATIONS (ONLY these specific fields):
# 1. Look for "Project Name:" label followed by the actual project name
# 2. Look for explicit project name fields in document metadata tables
# 3. Look for clearly labeled project identification sections
# 4. Check the first page comprehensive content for project titles

# STRICT RULES:
# - ONLY extract text that appears after explicit labels like "Project Name:", "Project:", or "Project Title:"
# - DO NOT extract document titles, headers, or section headings
# - DO NOT extract AR numbers, document types, or TIP titles
# - DO NOT extract station names unless they explicitly appear after "Project Name:" label
# - DO NOT infer or assume project names from document content
# - The project name must be explicitly stated and labeled as such
# - If no explicit "Project Name:" field exists, return exactly: "Not mentioned in document"

# Extract the project name ONLY if explicitly labeled as "Project Name:" in the document.

# 2. **client**: Identify the organization or client requesting the information. Look in both the Document Intelligence text and first page content for "Client:", "Owner:", issuing organization names, or companies requesting the RFI.

# 3. **region**: Extract geographical location information from all content. Look for:
#   - Countries, provinces/states, cities
#   - Project locations, service areas
#   - Regional identifiers, geographical references
#   - Check both structured text and first page tables/figures for location info

# 4. **industry**: Determine the industry sector this RFI relates to. Common industries include:
#   - "Power & Energy", "Water & Wastewater", 
#   - "Environmental", "Infrastructure"
#   - Check first page content and tables for industry indicators
#   - If not found, return exactly: "Not mentioned in document"

# 5. **prepared_date**: You are an expert document analyzer specializing in Technical Information Packages (TIP) and engineering documents.

# Your task is to extract the document preparation date from ALL provided content.

# SEARCH LOCATIONS (in order of priority):
# 1. Look for "Date:" field in document headers or metadata tables (including first page tables)
# 2. Look for "Prepared By:" sections followed by dates
# 3. Look for "Issue Date:", "Created:", or "Revision Date:" in all content
# 4. Look for dates in document footers or headers
# 5. Look for dates in format MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD in first page content

# RULES:
# - Extract the most recent or primary date associated with document preparation
# - Convert to YYYY-MM-DD format (e.g., 11/15/2021 becomes 2021-11-15)
# - If only partial date available, use what's available (e.g., 2021-11 for November 2021)
# - Ignore revision dates unless no preparation date exists
# - If not found, return exactly: "Not mentioned in document"

# Extract the preparation date from all the comprehensive document content.

# 6. **station_discipline**: You are an expert document analyzer specializing in Technical Information Packages (TIP) and engineering documents.

# Your task is to identify the engineering discipline and return ONLY the short keyword.

# SEARCH LOCATIONS:
# 1. Document titles containing discipline codes (e.g., "~ LINES – ENVIRONMENTAL ENV ~")
# 2. Section headers with discipline abbreviations in all content
# 3. TIP document type identifiers in first page content
# 4. Engineering discipline descriptions in scope of work

# DISCIPLINE MAPPING (return only the short keyword):
# - Environmental/Environmental Engineering → "ENV"
# - Electrical/Hardware/Electrical Engineering → "ELE" 
# - Mechanical/HVAC/Fire Systems → "MEC"
# - Lines/Transmission Lines → "LN"
# - Control/Control Systems → "CNT"
# - Protection/Protective Systems → "PRT"
# - Structural → "STR"
# - Site Preparation → "STE"
# - Auxiliary Systems → "AUX"
# - Equipment → "EQP"

# RULES:
# - Return ONLY the 2-4 letter discipline code (e.g., "ENV", "ELE", "MEC")
# - Look for discipline indicators in all provided content
# - If multiple disciplines exist, return the primary/main one
# - If not found or unclear, return exactly: "Not mentioned in document"

# Identify the station discipline from all the comprehensive document content.

# 7. **scope_of_work**: You are an expert business and technical writer. 
#   Your task is to summarize the 'Scope of Work' from ALL the provided content into a concise paragraph, 
#   retaining all critical information and technical details. 
  
#   The summary will be vectorized in Azure AI Search for vector search and retrieval purposes.  
  
#   RULES:
#   - The summary must contain only important information and must be concise
#   - Minimize the use of stop words and filler words
#   - Use information from both Document Intelligence text and first page comprehensive content
#   - Look for scope sections in tables and figures from first page
  
#   Extract and summarize the scope of work content from all the comprehensive document content.

# 8. **required_activities**: You are an expert summarizer for the section *Required Activities*. 
#   The summarized content can contain up to 7 lines of 50 words for this section.
  
#   Instructions: 
#   - **Do not miss any keywords** - Important keywords include installation of equipment 
#   - **Make sure all the points are covered and summarized** 
#   - **Include all the contents from each subheading of the section** 
#   - **Do not provide the result in bullet points/numbers** 
#   - **Use information from both Document Intelligence text AND first page content**
#   - **Check first page tables and figures for activity information**
#   - **If no clear information is found, use "Not mentioned in RFI"** 
  
#   Extract and summarize the required activities from all the comprehensive document content.

# **RESPONSE FORMAT - ONLY JSON:**
# {{
#    "project_name": "extracted project name or 'Not Specified'",
#    "client": "extracted client name or 'Not Specified'",
#    "region": "extracted region/location or 'Not Specified'",
#    "industry": "extracted industry sector or 'Not Specified'",
#    "prepared_date": "date in YYYY-MM-DD or 'Not Specified'",
#    "station_discipline": "extracted discipline or 'Not Specified'",
#    "scope_of_work": "short summary of work scope or 'Not Specified'",
#    "required_activities": "short summary of required activities or 'Not Specified'"
# }}

# **CRITICAL**: Return ONLY the JSON object. No explanation, no markdown, no extra text.
#         """
  
#     def _parse_json_response(self, response_text: str) -> Dict:
#         """Parse JSON response from Azure OpenAI"""
#         try:
#             # Remove any markdown formatting if present
#             if "```json" in response_text:
#                 response_text = response_text.split("```json")[1].split("```")[0].strip()
#             elif "```" in response_text:
#                 response_text = re.sub(r'```[^`]*```', '', response_text).strip()
          
#             # Clean up any remaining formatting
#             response_text = response_text.strip()
#             if response_text.startswith('json'):
#                 response_text = response_text[4:].strip()
          
#             # Parse JSON
#             metadata = json.loads(response_text)
#             return metadata
          
#         except json.JSONDecodeError as e:
#             print(f"❌ JSON parsing failed: {e}")
#             print(f"Raw response: {response_text[:200]}...")
#             return self._get_rfi_default_metadata()
  
#     def _validate_rfi_metadata(self, metadata: Dict) -> Dict:
#         """Validate and clean RFI metadata (8 fields)"""
#         validated = {}
      
#         for field in self.rfi_fields:
#             value = metadata.get(field, 'Not Specified')
          
#             # Clean and validate the value
#             if isinstance(value, str):
#                 value = value.strip()
#                 value = re.sub(r'^["\']+|["\']+$', '', value)  # Remove quotes
#                 if not value or value.lower() in ['none', 'null', 'undefined', '', 'n/a']:
#                     value = 'Not Specified'
#                 elif len(value) > 500:  # Limit field length
#                     value = value[:500] + '...'
#             else:
#                 value = 'Not Specified'
          
#             validated[field] = value
      
#         return validated
  
#     def _get_rfi_default_metadata(self) -> Dict:
#         """Get default RFI metadata structure (8 fields)"""
#         return {
#             'project_name': 'Not Specified',
#             'client': 'Not Specified',
#             'region': 'Not Specified',
#             'industry': 'Not Specified',
#             'prepared_date': 'Not Specified',
#             'station_discipline': 'Not Specified',
#             'scope_of_work': 'Not Specified',
#             'required_activities': 'Not Specified'
#         }
  
#     def get_status_info(self) -> Dict:
#         """Get status information about the enhanced RFI metadata extractor"""
#         return {
#             "extractor_type": "RFI_METADATA_ENHANCED",
#             "fields_count": len(self.rfi_fields),
#             "fields": self.rfi_fields,
#             "chunking_enabled": False,
#             "verbalization_enabled": False,
#             "first_page_extraction": True,
#             "client_initialized": self.verbalizer.client is not None,
#             "status": "ready" if self.verbalizer.client else "client_unavailable",
#             "reuses_existing_client": True,
#             "enhancement": "DI_text + first_page_comprehensive_content"
#         }



import json
import re
from typing import Dict, List
from .prompts import DocumentMetadataPrompts
from processors.content_verbalizer import ContentVerbalizer

class RFIExtractor:
    """Extract RFI metadata (8 fields) from documents using Azure OpenAI - Enhanced with first 10 pages content"""
   
    def __init__(self):
        """Initialize RFI extractor with existing Azure OpenAI client"""
        self.verbalizer = ContentVerbalizer()  # Reuse existing client
        self.rfi_fields = [
            'project_name', 'client', 'region', 'industry', 
            'prepared_date', 'station_discipline', 'scope_of_work', 'required_activities'
        ]
      
        print("✅ Enhanced RFI Extractor initialized - WITH FIRST 10 PAGES CONTENT")
        print(f"   📊 Fields: {len(self.rfi_fields)} RFI metadata fields")
        print(f"   🚫 Chunking: DISABLED for RFI documents")
        print(f"   📄 First 10 Pages: ENABLED - extracts all content from pages 1-10")
   
    async def extract_metadata_only(self, text_elements: List[Dict], azure_di_result=None) -> Dict:
        """
        Extract ONLY RFI metadata (8 fields) from complete document text elements + first 10 pages content
        NO CHUNKING - Only metadata extraction for indexing
        """
        try:
            print("🔍 Enhanced RFI metadata extraction (DI text + First 10 pages content)")
           
            # Step 1: Convert text elements to complete document text (existing)
            complete_document_text = self._prepare_complete_document_text(text_elements)
            print(f"📄 Document Intelligence extracted text: {len(complete_document_text)} characters")
           
            # Step 2: NEW - Extract first 10 pages comprehensive content
            first_10_pages_content = ""
            if azure_di_result:
                first_10_pages_content = self._extract_first_10_pages_comprehensive_content(azure_di_result)
                print(f"📄 First 10 pages comprehensive content: {len(first_10_pages_content)} characters")
            else:
                print("⚠️ No Azure DI result provided - skipping first 10 pages extraction")
           
            # Step 3: Combine both contents
            if first_10_pages_content:
                combined_content = f"""=== DOCUMENT INTELLIGENCE EXTRACTED TEXT ===
{complete_document_text}

=== FIRST 10 PAGES COMPREHENSIVE CONTENT ===
{first_10_pages_content}"""
                print(f"🔗 Combined content: {len(combined_content)} characters")
            else:
                combined_content = complete_document_text
                print(f"📝 Using DI text only: {len(combined_content)} characters")
           
            if not combined_content.strip():
                print("⚠️ No text found in document, using RFI defaults")
                return self._get_rfi_default_metadata()
           
            print(f"📊 Content prepared for LLM analysis:")
            print(f"   📄 Pages processed: {self._count_pages(text_elements)}")
            print(f"   📝 Total content length: {len(combined_content)} characters")
            print(f"   🎯 Ready for enhanced metadata extraction")
           
            # Step 4: Generate metadata using Azure OpenAI with combined content
            if self.verbalizer.client:
                metadata = await self._extract_metadata_with_azure_openai(combined_content)
            else:
                print("❌ Azure OpenAI client not available")
                return self._get_rfi_default_metadata()
           
            # Step 5: Validate and clean metadata for RFI (8 fields)
            validated_metadata = self._validate_rfi_metadata(metadata)
           
            print("✅ Enhanced RFI metadata extraction completed (DI + First 10 Pages)")
            return validated_metadata
           
        except Exception as e:
            print(f"❌ Error extracting enhanced RFI metadata: {e}")
            return self._get_rfi_default_metadata()

    def _extract_first_10_pages_comprehensive_content(self, azure_di_result) -> str:
        """
        Extract ALL content from the first 10 pages of the document (or all pages if document has fewer than 10 pages)
        Includes: text paragraphs, tables, and figures from pages 1-10
        """
        try:
            first_10_pages_content = []
            
            print("🔍 Extracting comprehensive first 10 pages content...")
            
            # Step 1: Determine the maximum page number in the document
            max_page_number = self._get_document_max_page_number(azure_di_result)
            pages_to_extract = min(10, max_page_number)
            
            print(f"📄 Document has {max_page_number} pages, extracting content from pages 1-{pages_to_extract}")
            
            # Step 2: Extract text from pages 1-10 (or fewer if document is smaller)
            if hasattr(azure_di_result, 'paragraphs') and azure_di_result.paragraphs:
                pages_paragraphs = []
                for paragraph in azure_di_result.paragraphs:
                    try:
                        # Get page number safely
                        page_num = 1
                        if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                            page_num = getattr(paragraph.bounding_regions[0], 'page_number', 1)
                        
                        if 1 <= page_num <= pages_to_extract:  # Extract from pages 1 to pages_to_extract
                            content = getattr(paragraph, 'content', '')
                            role = getattr(paragraph, 'role', 'paragraph')
                            if content and content.strip():
                                pages_paragraphs.append(f"[Page {page_num}][{role}] {content.strip()}")
                    except Exception as e:
                        continue
                
                if pages_paragraphs:
                    first_10_pages_content.append(f"=== PAGES 1-{pages_to_extract} TEXT CONTENT ===")
                    first_10_pages_content.extend(pages_paragraphs)
                    print(f"📝 Extracted {len(pages_paragraphs)} paragraphs from pages 1-{pages_to_extract}")
            
            # Step 3: Extract tables from pages 1-10 (or fewer)
            if hasattr(azure_di_result, 'tables') and azure_di_result.tables:
                pages_tables = []
                for idx, table in enumerate(azure_di_result.tables):
                    try:
                        # Get page number from table
                        table_page = 1
                        if hasattr(table, 'bounding_regions') and table.bounding_regions:
                            table_page = getattr(table.bounding_regions[0], 'page_number', 1)
                        
                        if 1 <= table_page <= pages_to_extract:  # Extract from pages 1 to pages_to_extract
                            # Convert table to text representation
                            table_text = self._convert_table_to_text(table)
                            if table_text:
                                pages_tables.append(f"[Page {table_page}][TABLE_{idx+1}] {table_text}")
                    except Exception as e:
                        continue
                
                if pages_tables:
                    first_10_pages_content.append(f"\n=== PAGES 1-{pages_to_extract} TABLES ===")
                    first_10_pages_content.extend(pages_tables)
                    print(f"📊 Extracted {len(pages_tables)} tables from pages 1-{pages_to_extract}")
            
            # Step 4: Extract figures/images from pages 1-10 (or fewer)
            if hasattr(azure_di_result, 'figures') and azure_di_result.figures:
                pages_figures = []
                for idx, figure in enumerate(azure_di_result.figures):
                    try:
                        # Get page number from figure
                        figure_page = 1
                        if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
                            figure_page = getattr(figure.bounding_regions[0], 'page_number', 1)
                        
                        if 1 <= figure_page <= pages_to_extract:  # Extract from pages 1 to pages_to_extract
                            # Extract figure text content
                            figure_text = self._extract_figure_content(figure, azure_di_result)
                            if figure_text:
                                pages_figures.append(f"[Page {figure_page}][FIGURE_{idx+1}] {figure_text}")
                            else:
                                pages_figures.append(f"[Page {figure_page}][FIGURE_{idx+1}] Visual content from page {figure_page}")
                    except Exception as e:
                        continue
                
                if pages_figures:
                    first_10_pages_content.append(f"\n=== PAGES 1-{pages_to_extract} FIGURES ===")
                    first_10_pages_content.extend(pages_figures)
                    print(f"🖼️ Extracted {len(pages_figures)} figures from pages 1-{pages_to_extract}")
            
            # Combine all first 10 pages content
            combined_first_10_pages = "\n\n".join(first_10_pages_content)
            
            print(f"✅ First 10 pages comprehensive extraction complete:")
            print(f"   📄 Pages extracted: 1-{pages_to_extract} (out of {max_page_number} total)")
            print(f"   📄 Total first 10 pages content: {len(combined_first_10_pages)} characters")
            
            return combined_first_10_pages
            
        except Exception as e:
            print(f"❌ Error extracting first 10 pages content: {e}")
            return ""

    def _get_document_max_page_number(self, azure_di_result) -> int:
        """Get the maximum page number in the document"""
        max_page = 1
        try:
            # Check paragraphs for page numbers
            if hasattr(azure_di_result, 'paragraphs') and azure_di_result.paragraphs:
                for paragraph in azure_di_result.paragraphs:
                    if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                        page_num = getattr(paragraph.bounding_regions[0], 'page_number', 1)
                        max_page = max(max_page, page_num)
            
            # Check tables for page numbers
            if hasattr(azure_di_result, 'tables') and azure_di_result.tables:
                for table in azure_di_result.tables:
                    if hasattr(table, 'bounding_regions') and table.bounding_regions:
                        page_num = getattr(table.bounding_regions[0], 'page_number', 1)
                        max_page = max(max_page, page_num)
            
            # Check figures for page numbers
            if hasattr(azure_di_result, 'figures') and azure_di_result.figures:
                for figure in azure_di_result.figures:
                    if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
                        page_num = getattr(figure.bounding_regions[0], 'page_number', 1)
                        max_page = max(max_page, page_num)
            
            print(f"📄 Document maximum page number detected: {max_page}")
            return max_page
            
        except Exception as e:
            print(f"⚠️ Error detecting max page number: {e}, defaulting to 1")
            return 1

    def _convert_table_to_text(self, table) -> str:
        """Convert Azure DI table to text representation"""
        try:
            if not hasattr(table, 'cells') or not table.cells:
                return ""
            
            # Create a grid structure
            max_row = max(cell.row_index for cell in table.cells) + 1
            max_col = max(cell.column_index for cell in table.cells) + 1
            
            # Initialize grid
            grid = [["" for _ in range(max_col)] for _ in range(max_row)]
            
            # Fill grid with cell content
            for cell in table.cells:
                content = getattr(cell, 'content', '').strip()
                if content:
                    grid[cell.row_index][cell.column_index] = content
            
            # Convert grid to text
            table_lines = []
            for row in grid:
                if any(cell.strip() for cell in row):  # Skip empty rows
                    row_text = " | ".join(cell.strip() for cell in row)
                    table_lines.append(row_text)
            
            return "\n".join(table_lines)
            
        except Exception as e:
            print(f"⚠️ Error converting table to text: {e}")
            return ""

    def _extract_figure_content(self, figure, result) -> str:
        """Extract text content from figure using spans"""
        try:
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
        except Exception as e:
            return ""
   
    def _prepare_complete_document_text(self, text_elements: List[Dict]) -> str:
        """Convert text elements to complete document text"""
        complete_text = ""
      
        # Process ALL text elements from the complete document
        for element in text_elements:
            content = element.get('content', '').strip()
            role = element.get('role', 'unknown')
          
            # Add role context for better understanding
            if content:
                complete_text += f"[{role}] {content}\n\n"
      
        print(f"🔍 Processing {len(text_elements)} text elements from complete document...")
        return complete_text
  
    def _count_pages(self, text_elements: List[Dict]) -> str:
        """Count total pages in document"""
        pages = set()
        for element in text_elements:
            page_num = element.get('page_number', 1)
            pages.add(page_num)
      
        total_pages = max(pages) if pages else 1
        return f"{total_pages}/{total_pages}"
  
    async def _extract_metadata_with_azure_openai(self, combined_content: str) -> Dict:
        """Extract RFI metadata using Azure OpenAI API with combined content"""
        try:
            print(f"📄 Sending {len(combined_content)} characters to LLM for enhanced RFI analysis")
            print("🤖 Calling LLM for metadata extraction (DI + First 10 Pages)...")
          
            # Get the RFI-specific prompt with 8 fields
            prompt = self._get_enhanced_rfi_extraction_prompt(combined_content)
          
            response = await self.verbalizer.client.chat.completions.create(
                model="gpt-4o",  # Use same model as ContentVerbalizer
                messages=[
                    {"role": "system", "content": "You are an expert RFI analyst. Extract the 8 metadata fields for RFI documents from the comprehensive content provided. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,  # Sufficient for 8 fields
                temperature=0.1  # Low temperature for consistent extraction
            )
          
            response_text = response.choices[0].message.content.strip()
            print(f"📝 LLM response: {len(response_text)} characters")
          
            # Clean and parse JSON response
            metadata = self._parse_json_response(response_text)
          
            print("✅ Successfully parsed enhanced metadata from LLM")
            return metadata
              
        except Exception as e:
            print(f"❌ Azure OpenAI API error: {e}")
            return self._get_rfi_default_metadata()

    def _get_enhanced_rfi_extraction_prompt(self, combined_content: str) -> str:
        """Get the enhanced RFI metadata extraction prompt for 8 fields with combined content from first 10 pages"""
        return f"""
You are an expert RFI (Request for Information) analyzer. Extract EXACTLY 8 metadata fields from the comprehensive document content provided below. Return ONLY a valid JSON object.

**IMPORTANT**: The content below includes:
1. Document Intelligence extracted text (structured text elements)
2. First 10 pages comprehensive content (all text, tables, and figures from pages 1-10)

Use ALL this information to extract the most accurate metadata.

**COMBINED DOCUMENT CONTENT:**
{combined_content}

**EXTRACTION REQUIREMENTS:**

1. **project_name**: You are an expert document analyzer specializing in Technical Information Packages (TIP) and engineering documents.

Your task is to extract ONLY the explicit Project Name from the document content.

SEARCH LOCATIONS (ONLY these specific fields):
1. Look for "Project Name:" label followed by the actual project name
2. Look for explicit project name fields in document metadata tables
3. Look for clearly labeled project identification sections
4. Check the first 10 pages comprehensive content for project titles

STRICT RULES:
- ONLY extract text that appears after explicit labels like "Project Name:", "Project:", or "Project Title:"
- DO NOT extract document titles, headers, or section headings
- DO NOT extract AR numbers, document types, or TIP titles
- DO NOT extract station names unless they explicitly appear after "Project Name:" label
- DO NOT infer or assume project names from document content
- The project name must be explicitly stated and labeled as such
- If no explicit "Project Name:" field exists, return exactly: "Not mentioned in document"

Extract the project name ONLY if explicitly labeled as "Project Name:" in the document.

2. **client**: Identify the organization or client requesting the information. Look in both the Document Intelligence text and first 10 pages content for "Client:", "Owner:", issuing organization names, or companies requesting the RFI.

3. **region**: Extract geographical location information from all content. Look for:
  - Countries, provinces/states, cities
  - Project locations, service areas
  - Regional identifiers, geographical references
  - Check both structured text and first 10 pages tables/figures for location info

4. **industry**: Determine the industry sector this RFI relates to. Common industries include:
  - "Power & Energy", "Water & Wastewater", 
  - "Environmental", "Infrastructure"
  - Check first 10 pages content and tables for industry indicators
  - If not found, return exactly: "Not mentioned in document"

5. **prepared_date**: You are an expert document analyzer specializing in Technical Information Packages (TIP) and engineering documents.

Your task is to extract the document preparation date from ALL provided content.

SEARCH LOCATIONS (in order of priority):
1. Look for "Date:" field in document headers or metadata tables (including first 10 pages tables)
2. Look for "Prepared By:" sections followed by dates
3. Look for "Issue Date:", "Created:", or "Revision Date:" in all content
4. Look for dates in document footers or headers
5. Look for dates in format MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD in first 10 pages content

RULES:
- Extract the most recent or primary date associated with document preparation
- Convert to YYYY-MM-DD format (e.g., 11/15/2021 becomes 2021-11-15)
- If only partial date available, use what's available (e.g., 2021-11 for November 2021)
- Ignore revision dates unless no preparation date exists
- If not found, return exactly: "Not mentioned in document"

Extract the preparation date from all the comprehensive document content.

6. **station_discipline**: You are an expert document analyzer specializing in Technical Information Packages (TIP) and engineering documents.

Your task is to identify the engineering discipline and return ONLY the short keyword.

SEARCH LOCATIONS:
1. Document titles containing discipline codes (e.g., "~ LINES – ENVIRONMENTAL ENV ~")
2. Section headers with discipline abbreviations in all content
3. TIP document type identifiers in first 10 pages content
4. Engineering discipline descriptions in scope of work

DISCIPLINE MAPPING (return only the short keyword):
- Environmental/Environmental Engineering → "ENV"
- Electrical/Hardware/Electrical Engineering → "ELE" 
- Mechanical/HVAC/Fire Systems → "MEC"
- Lines/Transmission Lines → "LN"
- Control/Control Systems → "CNT"
- Protection/Protective Systems → "PRT"
- Structural → "STR"
- Site Preparation → "STE"
- Auxiliary Systems → "AUX"
- Equipment → "EQP"

RULES:
- IF AND ONLY IF ABOVE MENTIONED DISCIPLINE SECTIONS EXISTS THEN ONLY CONSIDER ABOVE DISCIPLINE MAPPING
- Return ONLY the 2-4 letter discipline code (e.g., "ENV", "ELE", "MEC")
- Look for discipline indicators in all provided content
- If multiple disciplines exist, return the primary/main one
- If not found or unclear, return exactly: "Not mentioned in document"

Identify the station discipline from all the comprehensive document content.

7. **scope_of_work**: You are an expert business and technical writer. 
  Your task is to summarize the 'Scope of Work' from ALL the provided content into a concise paragraph, 
  retaining all critical information and technical details.When analyzing the document, note that the 'scope of work' section may appear different but similar headings
  example : ['scope and deliverables', 'Project Description', 'Purpose','General', 'Introduction', 'Scope of Services', 'Work', 'Invitation',etc]
  Regardless of the variation in naming, identify and extract these sections consistently and treat them as part of 'scope of work'.
  
  The summary will be vectorized in Azure AI Search for vector search and retrieval purposes.  
  
  RULES:
  - The summary must contain only important information and must be concise
  - Minimize the use of stop words and filler words
  - Use information from both Document Intelligence text and first 20 pages comprehensive content
  - Look for scope sections in tables and figures from first 20 pages
  
  Extract and summarize the scope of work content from all the comprehensive document content.

8. **required_activities**: You are an expert summarizer for the section *Required Activities*. 
  The summarized content can contain up to 7 lines of 50 words for this section.
  When analyzing the document, note that the 'required activities' section may appear different but similar headings
  example : ['Performance of the Work', 'Work Activities', 'Site Preparation Activities', 'Installation Activities', 'Key Activities', 'Work Tasks', 'Activities', 'Work to be performed', 'Work Requirements', 'Services Required','Construction Requirements']
  Regardless of the variation in naming, identify and extract these sections consistently and treat them as part of 'required_activities'.
  Instructions: 
  - **Do not miss any keywords** - Important keywords include installation of equipment 
  - **Make sure all the points are covered and summarized** 
  - **Include all the contents from each subheading of the section** 
  - **Do not provide the result in bullet points/numbers** 
  - **Use information from both Document Intelligence text AND first 10 pages content**
  - **Check first 10 pages tables and figures for activity information**
  - **If no clear information is found, use "Not mentioned in RFI"** 
  
  Extract and summarize the required activities from all the comprehensive document content.

**RESPONSE FORMAT - ONLY JSON:**
{{
   "project_name": "extracted project name or 'Not Specified'",
   "client": "extracted client name or 'Not Specified'",
   "region": "extracted region/location or 'Not Specified'",
   "industry": "extracted industry sector or 'Not Specified'",
   "prepared_date": "date in YYYY-MM-DD or 'Not Specified'",
   "station_discipline": "extracted discipline or 'Not Specified'",
   "scope_of_work": "short summary of work scope or 'Not Specified'",
   "required_activities": "short summary of required activities or 'Not Specified'"
}}

**CRITICAL**: Return ONLY the JSON object. No explanation, no markdown, no extra text.
        """
  
    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON response from Azure OpenAI"""
        try:
            # Remove any markdown formatting if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = re.sub(r'```[^`]*```', '', response_text).strip()
          
            # Clean up any remaining formatting
            response_text = response_text.strip()
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
          
            # Parse JSON
            metadata = json.loads(response_text)
            return metadata
          
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw response: {response_text[:200]}...")
            return self._get_rfi_default_metadata()
  
    def _validate_rfi_metadata(self, metadata: Dict) -> Dict:
        """Validate and clean RFI metadata (8 fields)"""
        validated = {}
      
        for field in self.rfi_fields:
            value = metadata.get(field, 'Not Specified')
          
            # Clean and validate the value
            if isinstance(value, str):
                value = value.strip()
                value = re.sub(r'^["\']+|["\']+$', '', value)  # Remove quotes
                if not value or value.lower() in ['none', 'null', 'undefined', '', 'n/a']:
                    value = 'Not Specified'
                elif len(value) > 500:  # Limit field length
                    value = value[:500] + '...'
            else:
                value = 'Not Specified'
          
            validated[field] = value
      
        return validated
  
    def _get_rfi_default_metadata(self) -> Dict:
        """Get default RFI metadata structure (8 fields)"""
        return {
            'project_name': 'Not Specified',
            'client': 'Not Specified',
            'region': 'Not Specified',
            'industry': 'Not Specified',
            'prepared_date': 'Not Specified',
            'station_discipline': 'Not Specified',
            'scope_of_work': 'Not Specified',
            'required_activities': 'Not Specified'
        }
  
    def get_status_info(self) -> Dict:
        """Get status information about the enhanced RFI metadata extractor"""
        return {
            "extractor_type": "RFI_METADATA_ENHANCED_10_PAGES",
            "fields_count": len(self.rfi_fields),
            "fields": self.rfi_fields,
            "chunking_enabled": False,
            "verbalization_enabled": False,
            "first_10_pages_extraction": True,
            "client_initialized": self.verbalizer.client is not None,
            "status": "ready" if self.verbalizer.client else "client_unavailable",
            "reuses_existing_client": True,
            "enhancement": "DI_text + first_10_pages_comprehensive_content"
        }