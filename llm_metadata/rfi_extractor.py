import json
import re
import asyncio
import threading
from typing import Dict, List
from .prompts import DocumentMetadataPrompts
from processors.content_verbalizer import ContentVerbalizer

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace
# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)



class RFIExtractor:
    """Extract RFI metadata (17 components with sub-components and consolidated descriptions) from documents using Azure OpenAI, with rate limiting for parallel processing"""
    _rate_limiter = None  # Class-level rate limiter
    _request_tracker = {'success_count': 0, 'timeout_count': 0, 'error_count': 0}  # Track request outcomes
    
    @tracer.start_as_current_span("RFIExtractor_init_fn")
    def __init__(self):
        """Initialize RFI extractor with existing Azure OpenAI client and rate limiting"""
        self.verbalizer = ContentVerbalizer()  # Reuse existing client
        self.new_rfi_fields = [
            'project_name', 'client', 'industry', 'region', 'prepared_date', 'field_type','voltage','contract_types','pricing', 'location', 'state', 'country','components'
        ]
        
        # Updated component mapping with 17 separate components including consolidated description fields
        self.valid_components = {
            'electrical': {
                'name': 'Electrical',
                'sub_components': ['cables_and_accessories', 'buswork_and_insulators', 'electrical_others'],
                'description_field': 'electrical_description'
            },
            'equipment': {
                'name': 'Equipment',
                'sub_components': ['power_transformers', 'switching_equipment', 'equipment_others'],
                'description_field': 'equipment_description'
            },
            'auxiliary': {
                'name': 'Auxiliary',
                'sub_components': ['station_service_and_main_lv_panel', 'lighting_and_controls', 'auxiliary_others'],
                'description_field': 'auxiliary_description'
            },
            'line': {
                'name': 'Line',
                'sub_components': ['phase_conductors', 'insulators', 'line_others'],
                'description_field': 'line_description'
            },
            'site_preparation': {
                'name': 'Site Preparation',
                'sub_components': ['clearing_and_demolition', 'fencing_and_Gates', 'site_preparation_others'],
                'description_field': 'site_preparation_description'
            },
            'access_roads': {
                'name': 'Access Roads',
                'sub_components': ['subgrade', 'pavement', 'access_roads_others'],
                'description_field': 'access_roads_description'
            },
            'drainage': {
                'name': 'Drainage',
                'sub_components': ['culverts', 'storm_pipes', 'drainage_others'],
                'description_field': 'drainage_description'
            },
            'undergrounds': {
                'name': 'Undergrounds',
                'sub_components': ['ductbanks', 'conduits', 'undergrounds_others'],
                'description_field': 'undergrounds_description'
            },
            'environment': {
                'name': 'Environment',
                'sub_components': ['oil_containments', 'dust_and_noise', 'environment_others'],
                'description_field': 'environment_description'
            },
            'foundations': {
                'name': 'Foundations',
                'sub_components': ['concrete_foundations', 'steel_screw_piles', 'foundations_others'],
                'description_field': 'foundations_description'
            },
            'substation_structures': {
                'name': 'Substation Structures',
                'sub_components': ['equipment_and_support_structures', 'bus_support_structures', 'substation_structures_others'],
                'description_field': 'substation_structures_description'
            },
            'buildings': {
                'name': 'Buildings',
                'sub_components': ['frame_and_floors', 'walls_and_openings', 'buildings_others'],
                'description_field': 'buildings_description'
            },
            'firewalls_and_barriers': {
                'name': 'Firewalls and Barriers',
                'sub_components': ['transformer_firewalls', 'blast_and_arc_barriers', 'firewalls_and_barriers_others'],
                'description_field': 'firewalls_and_barriers_description'
            },
            'line_structures': {
                'name': 'Line Structures',
                'sub_components': ['monopoles', 'lattice_towers', 'line_structures_others'],
                'description_field': 'line_structures_description'
            },
            'protection_and_control': {
                'name': 'Protection and Control',
                'sub_components': ['protection_relays_and_schemes', 'scada_RTU_and_Automation', 'protection_and_control_others'],
                'description_field': 'protection_and_control_description'
            },
            'metering': {
                'name': 'Metering',
                'sub_components': ['metering_cts_and_vts', 'meters_and_recorders', 'metering_others'],
                'description_field': 'metering_description'
            },
            'telecom_and_teleprotection': {
                'name': 'Telecom and Teleprotection',
                'sub_components': ['switching_routing_and_transport', 'radio_and_wan_access', 'telecom_and_teleprotection_others'],
                'description_field': 'telecom_and_teleprotection_description'
            }
        }
      
        # ADD: Initialize rate limiter if not exists
        if RFIExtractor._rate_limiter is None:
            RFIExtractor._rate_limiter = asyncio.Semaphore(3)  # Max 3 concurrent LLM calls
        
        log_custom_event(
                 logger,
                 "Enhanced RFI Extractor initialized - 17 COMPONENTS WITH SUB-COMPONENTS AND CONSOLIDATED DESCRIPTIONS + Rate Limiting",
                 level="info",
                )
   
    @tracer.start_as_current_span("_wait_for_rfi_rate_limit_fn")
    async def _wait_for_rfi_rate_limit(self):
        """Wait for enhanced RFI rate limit (can be extended for external tracking)"""
        await asyncio.sleep(0.1)  # Simulate wait, can be replaced with external logic

    @tracer.start_as_current_span("extract_metadata_only_fn")
    async def extract_metadata_only(self, text_elements: List[Dict], azure_di_result=None) -> Dict:
        """
        Extract ONLY RFI metadata (17 components with sub-components and consolidated descriptions) from complete document text elements + first 10 pages content
        NO CHUNKING - Only metadata extraction for indexing
        Enhanced rate limiting for parallel processing
        """
        async with RFIExtractor._rate_limiter:
            # Enhanced rate limiting
            await self._wait_for_rfi_rate_limit()
            for attempt in range(3):  # 3 retry attempts
                try:
                    log_custom_event(
                                    logger,
                                    f"Enhanced RFI metadata extraction with 17 components and consolidated descriptions (Rate limited - Attempt {attempt + 1}/3)",
                                    level="info",
                                    )
                    # Step 1: Convert text elements to complete document text (existing)
                    complete_document_text = self._prepare_complete_document_text(text_elements)
                    log_custom_event(
                                    logger,
                                    f"Document Intelligence extracted text: {len(complete_document_text)} characters",
                                    level="info",
                                    )

                    # Step 2: NEW - Extract first 10 pages comprehensive content
                    first_10_pages_content = ""
                    if azure_di_result:
                        first_10_pages_content = self._extract_first_10_pages_comprehensive_content(azure_di_result)
                    else:
                        log_custom_event(
                                        logger,
                                        "No Azure DI result provided - skipping first 10 pages extraction",
                                        level="warning",
                                        )
                    # Step 3: Combine both contents
                    if first_10_pages_content:
                        combined_content = f"""=== DOCUMENT INTELLIGENCE EXTRACTED TEXT ===\n{complete_document_text}\n\n=== FIRST 10 PAGES COMPREHENSIVE CONTENT ===\n{first_10_pages_content}"""
                    else:
                        combined_content = complete_document_text
                        
                    if not combined_content.strip():
                        log_custom_event(
                                        logger,
                                        "No text found in document, using RFI defaults",
                                        level="warning",
                                        )
                        
                        return self._get_rfi_default_metadata()

                    # Step 4: Generate metadata using Azure OpenAI with combined content and timeout
                    if self.verbalizer.client:
                        metadata = await asyncio.wait_for(
                            self._extract_metadata_with_azure_openai(combined_content),
                            timeout=120.0  # 2 minute timeout
                        )
                        RFIExtractor._request_tracker['success_count'] += 1
                    else:
                        log_custom_event(
                                        logger,
                                        "Azure OpenAI client not available",
                                        level="warning",
                                        )
                        return self._get_rfi_default_metadata()
                    
                    # Step 5: Validate and clean metadata for RFI (enhanced format)
                    validated_metadata = self._validate_rfi_metadata(metadata)
                    return validated_metadata
                    
                except asyncio.TimeoutError:
                    RFIExtractor._request_tracker['timeout_count'] += 1
                    if attempt == 2:
                        return self._get_rfi_default_metadata()
                    await asyncio.sleep(1.0)  # Wait before retry
                except Exception as e:
                    RFIExtractor._request_tracker['error_count'] += 1
                    if attempt == 2:
                        return self._get_rfi_default_metadata()
                    await asyncio.sleep(1.0)  # Wait before retry

    @tracer.start_as_current_span("_extract_first_10_pages_comprehensive_content_fn")
    def _extract_first_10_pages_comprehensive_content(self, azure_di_result) -> str:
        """
        Extract ALL content from the first 10 pages of the document (or all pages if document has fewer than 10 pages)
        Includes: text paragraphs, tables, and figures from pages 1-10
        """
        try:
            first_10_pages_content = []
            
            log_custom_event(
                 logger,
                 "Extracting comprehensive first 10 pages content...",
                 level="info",
                )
            
            # Step 1: Determine the maximum page number in the document
            max_page_number = self._get_document_max_page_number(azure_di_result)
            pages_to_extract = min(10, max_page_number)
            
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
            
            # Combine all first 10 pages content
            combined_first_10_pages = "\n\n".join(first_10_pages_content)
            
            log_custom_event(
                            logger,
                            f"First 10 pages comprehensive extraction completed",
                            level="info",
                            )
            
            return combined_first_10_pages
            
        except Exception as e:
            return ""

    @tracer.start_as_current_span("_get_document_max_page_number_fn")
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
            
            log_custom_event(
                 logger,
                 f"Document maximum page number detected: {max_page}",
                 level="info",
                )
            return max_page
            
        except Exception as e:
            return 1

    @tracer.start_as_current_span("_convert_table_to_text_fn")
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
            return ""

    @tracer.start_as_current_span("_extract_figure_content_fn")
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
   
    @tracer.start_as_current_span("_prepare_complete_document_text_fn")
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
      
        return complete_text
  
    def _count_pages(self, text_elements: List[Dict]) -> str:
        """Count total pages in document"""
        pages = set()
        for element in text_elements:
            page_num = element.get('page_number', 1)
            pages.add(page_num)
      
        total_pages = max(pages) if pages else 1
        return f"{total_pages}/{total_pages}"
  
    @tracer.start_as_current_span("_extract_metadata_with_azure_openai_fn")
    async def _extract_metadata_with_azure_openai(self, combined_content: str) -> Dict:
        """Extract RFI metadata using Azure OpenAI API with combined content"""
        try:
            # Get the RFI-specific prompt with 17 components and consolidated descriptions format
            prompt = self._get_enhanced_rfi_extraction_prompt(combined_content)
          
            response = await self.verbalizer.client.chat.completions.create(
                model="gpt-4o",  # Use same model as ContentVerbalizer
                messages=[
                    {"role": "system", "content": "You are an expert RFI analyst. Extract the metadata fields for RFI documents from the comprehensive content provided. Return only valid JSON in the enhanced component-based format with 17 components, their sub-components, and consolidated description fields."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4500,  # Increased for 17 components with consolidated descriptions
                temperature=0.1  # Low temperature for consistent extraction
            )
          
            response_text = response.choices[0].message.content.strip()
          
            # Clean and parse JSON response
            metadata = self._parse_json_response(response_text)
          
            return metadata
              
        except Exception as e:
            return self._get_rfi_default_metadata()

    def _get_enhanced_rfi_extraction_prompt(self, combined_content: str) -> str:
        """Get the enhanced RFI metadata extraction prompt for 17 components with consolidated descriptions"""
        return f"""
You are an expert RFI (Request for Information) analyzer. Extract metadata fields from the comprehensive document content provided below. Return ONLY a valid JSON object in the ENHANCED 17-COMPONENT FORMAT with consolidated description fields.

**IMPORTANT**: The content below includes:
1. Document Intelligence extracted text (structured text elements)
2. First 10 pages comprehensive content (all text, tables, and figures from pages 1-10)

Use ALL this information to extract the most accurate metadata.

**COMBINED DOCUMENT CONTENT:**
{combined_content}

**EXTRACTION REQUIREMENTS:**

1. **project_name**: Extract ONLY the explicit Project Name from the document content.

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
- If no explicit "Project Name:" field exists, return exactly: ""

2. **client**: Identify the organization or client requesting the information. Look in both the Document Intelligence text and first 10 pages content for "Client:", "Owner:", issuing organization names, or companies requesting the RFI.

3. **industry**: Determine the industry sector this RFI relates to. Common industries include:
  - "Power & Energy", "Water & Wastewater", 
  - "Environmental", "Infrastructure"
  - Check first 10 pages content and tables for industry indicators
  - If not found, return exactly: ""

4. **region**: Extract geographical location information from all content. Look for:
  - Countries, provinces/states, cities
  - Project locations, service areas
  - Regional identifiers, geographical references
  - Check both structured text and first 10 pages tables/figures for location info
  - Include precise location + state + country (e.g., "Merivale TS, Ontario, Canada")
  - If the country is not explicitly mentioned but the state/province or region is mentioned, then infer the correct country.
  - Always return in the format: <precise location>, <state/province>, <country>
  - If not found, return exactly: "Not mentioned in the document"

5. **prepared_date**: Extract the document preparation date from ALL provided content.

DATE FORMAT RULES:
- ALWAYS convert to YYYY-MM-DD format (standardized ISO format)
- Examples: "11/15/2021" becomes "2021-11-15", "March 2023" becomes "2023-03-01", "2022-05-10" stays "2022-05-10"
- If only partial date available, use first day of month/year (e.g., "November 2021" becomes "2021-11-01")
- Ignore revision dates unless no preparation date exists
- If not found, return exactly: "Not mentioned in the document"

6. **field_type**: Extract the Field Type and identify whether the described project refers to:
    - "Green Field": creation of entirely new infrastructure
    - "Brown Field": modification/upgrade of existing infrastructure
    - "Not mentioned in the document": if unclear

7. **voltage**: Extract the specific voltage value(s) mentioned in the text.
    - If multiple voltage numbers are present, select only the highest number.
    - Do not return ranges (e.g., "115â€"230 kV"). Always pick the largest single value
      (along with the corresponding unit mentioned) within the range or list. ( eg : 230 kV, 120V )
    - If no voltage is found, return "Not mentioned in the document".

8. **contract_types**: Extract and classify contract type:
    - "Fixed Price": lump sum, fixed fee, turnkey
    - "T&M (Time and Materials)": hourly rate, cost-plus
    - "MSA (Master Service Agreement)": framework agreement
    - The result of the contract_type should always be "Fixed Price" for all hydro One projects (Hydro one, HONI, Hydro one Limited ). 
    - "Not mentioned in the document": if not evident

9. **pricing**: Extract specific project value or contract amount mentioned.
    - If not found: "Not mentioned in the document"

    
10. **location**: Extract the precise/local project or service location name that is part of the region field.
 - Example: if region = "Merivale TS, Ontario, Canada", then location = "Merivale TS"
 - Do not include state or country, only the local site name
 - Return only one value (no lists)
 - If not found, return exactly: "not mentioned in the document"

11. **state** : Extract the state or province name from the region field.
 - Example: if region = "Merivale TS, Ontario, Canada", then state/province = "Ontario"
 - Do not include city or country
 - Return only one value (no lists)
 - If not found, return exactly: "not mentioned in the document"

12. **country** : Extract the country name from the region field.
 - Example: if region = "Merivale TS, Ontario, Canada", then country = "Canada"
 - If the country is not explicitly mentioned, infer it from the state or region name.
 - Return only one value (no lists)
 - If not found, return exactly: "not mentioned in the document"
 

13. **components**: You are an expert document analyzer specializing in engineering documents.

**VALID COMPONENTS - 17 SEPARATE COMPONENTS:**


- "electrical" → Electrical Systems (sub-components: cables_and_accessories, buswork_and_insulators, electrical_others)
- "equipment" → Equipment (sub-components: power_transformers, switching_equipment, equipment_others)
- "auxiliary" → Auxiliary Systems (sub-components: station_service_and_main_lv_panel, lighting_and_controls, auxiliary_others)
- "line" → Line Systems (sub-components: phase_conductors, insulators, line_others)
- "site_preparation" → Site Preparation (sub-components: clearing_and_demolition, fencing_and_Gates, site_preparation_others)
- "access_roads" → Access Roads (sub-components: subgrade, pavement, access_roads_others)
- "drainage" → Drainage (sub-components: culverts, storm_pipes, drainage_others)
- "undergrounds" → Undergrounds (sub-components: ductbanks, conduits, undergrounds_others)
- "environment" → Environment (sub-components: oil_containments, dust_and_noise, environment_others)
- "foundations" → Foundations (sub-components: concrete_foundations, steel_screw_piles, foundations_others)
- "substation_structures" → Substation Structures (sub-components: equipment_and_support_structures, bus_support_structures, substation_structures_others)
- "buildings" → Buildings (sub-components: frame_and_floors, walls_and_openings, buildings_others)
- "firewalls_and_barriers" → Firewalls and Barriers (sub-components: transformer_firewalls, blast_and_arc_barriers, firewalls_and_barriers_others)
- "line_structures" → Line Structures (sub-components: monopoles, lattice_towers, line_structures_others)
- "protection_and_control" → Protection and Control (sub-components: protection_relays_and_schemes, scada_RTU_and_Automation, protection_and_control_others)
- "metering" → Metering (sub-components: metering_cts_and_vts, meters_and_recorders, metering_others)
- "telecom_and_teleprotection" → Telecom and Teleprotection (sub-components: switching_routing_and_transport, radio_and_wan_access, telecom_and_teleprotection_others)

**COMPONENT IDENTIFICATION AND EXTRACTION:**

For each identified component, extract ALL fields:

**SCOPE_OF_WORK**: Summarize the scope of work related to this SPECIFIC COMPONENT from ALL provided content into a concise paragraph. Look for scope sections under various headings like 'scope and deliverables', 'Project Description', 'Purpose', etc. Only include content relevant to this specific component. If not found: "not mentioned in document"

**REQUIRED_ACTIVITIES**: Summarize required activities for this SPECIFIC COMPONENT (up to 7 lines of 50 words). Look for activities under headings like 'Performance of the Work', 'Work Activities', 'Key Activities', etc. Only include activities relevant to this specific component. If not found: "not mentioned in document"

**SUB-COMPONENT FIELDS**: For each of the 3 sub-components per component, extract specific information related to that sub-component. If not found: "not mentioned in document"

**CONSOLIDATED DESCRIPTION FIELD**: For each component, create a consolidated summary that combines information from all 3 sub-components into a single comprehensive description field. This field should be named as follows:
- For "electrical": "electrical_description" 
- For "equipment": "equipment_description"
- For "auxiliary": "auxiliary_description"
- For "line": "line_description"
- For "site_preparation": "site_preparation_description"
- For "access_roads": "access_roads_description"
- For "drainage": "drainage_description"
- For "undergrounds": "undergrounds_description"
- For "environment": "environment_description"
- For "foundations": "foundations_description"
- For "substation_structures": "substation_structures_description"
- For "buildings": "buildings_description"
- For "firewalls_and_barriers": "firewalls_and_barriers_description"
- For "line_structures": "line_structures_description"
- For "protection_and_control": "protection_and_control_description"
- For "metering": "metering_description"
- For "telecom_and_teleprotection": "telecom_and_teleprotection_description"

The consolidated description should combine and summarize the content from all 3 sub-component fields for that component into a single, comprehensive paragraph.
If no meaningful content exists across all sub-components: "not mentioned in document"

**COMPONENT IDENTIFICATION RULES:**
1. Look for explicit mentions of component names or descriptions in document content
2. Analyze scope of work and activities to determine which components they relate to
3. DO NOT assume or infer components - only use components that are explicitly mentioned or clearly described
4. Each component must have ALL 6 fields: scope_of_work, required_activities, 3 sub-component fields, and 1 consolidated description field
5. Only include components that have meaningful content (not all "not mentioned in document")

**RESPONSE FORMAT - ONLY JSON:**
{{
   "project_name": "extracted project name or empty string",
   "client": "extracted client name or empty string",
   "industry": "extracted industry sector or empty string", 
   "region": "extracted region/location or empty string",
   "prepared_date": "date in YYYY-MM-DD format or empty string",
   "field_type": "extracted field type or Not mentioned in the document",
   "voltage": "extracted voltage or Not mentioned in the document",
   "contract_types": "extracted contract type or Not mentioned in the document",
   "pricing": "extracted pricing info or Not mentioned in the document",
   "location": "extracted location info or Not mentioned in the document" 
   "state": "extracted state info or Not mentioned in the document" ,
   "country": "extracted country info or Not mentioned in the document", 
   "components": {{
     "electrical": {{
       "scope_of_work": "electrical scope content or not mentioned in document",
       "required_activities": "electrical activities content or not mentioned in document",
       "cables_and_accessories": "cables and accessories info or not mentioned in document",
       "buswork_and_insulators": "buswork and insulator info or not mentioned in document",
       "electrical_others": "other electrical info or not mentioned in document",
       "electrical_description": "consolidated summary of cables_and_accessories + buswork_and_insulators + electrical_others or not mentioned in document"
     }},
     "equipment": {{
       "scope_of_work": "equipment scope content or not mentioned in document",
       "required_activities": "equipment activities content or not mentioned in document",
       "power_transformers": "transformer info or not mentioned in document",
       "switching_equipment": "switching equipment info or not mentioned in document",
       "equipment_others": "other equipment info or not mentioned in document",
       "equipment_description": "consolidated summary of power_transformers + switching_equipment + equipment_others or not mentioned in document"
     }},
     "site_preparation": {{
       "scope_of_work": "site preparation scope content or not mentioned in document",
       "required_activities": "site preparation activities content or not mentioned in document",
       "clearing_and_demolition": "clearing and demolition info or not mentioned in document",
       "fencing_and_Gates": "fencing and gates info or not mentioned in document",
       "site_preparation_others": "other site preparation info or not mentioned in document",
       "site_preparation_description": "consolidated summary of clearing_and_demolition + fencing_and_Gates + site_preparation_others or not mentioned in document"
     }},
     "access_roads": {{
       "scope_of_work": "access roads scope content or not mentioned in document",
       "required_activities": "access roads activities content or not mentioned in document",
       "subgrade": "subgrade info or not mentioned in document",
       "pavement": "pavement info or not mentioned in document",
       "access_roads_others": "other access roads info or not mentioned in document",
       "access_roads_description": "consolidated summary of subgrade + pavement + access_roads_others or not mentioned in document"
     }},
     "drainage": {{
       "scope_of_work": "drainage scope content or not mentioned in document",
       "required_activities": "drainage activities content or not mentioned in document",
       "culverts": "culverts info or not mentioned in document",
       "storm_pipes": "storm pipes info or not mentioned in document",
       "drainage_others": "other drainage info or not mentioned in document",
       "drainage_description": "consolidated summary of culverts + storm_pipes + drainage_others or not mentioned in document"
     }},
     "undergrounds": {{
       "scope_of_work": "undergrounds scope content or not mentioned in document",
       "required_activities": "undergrounds activities content or not mentioned in document",
       "ductbanks": "ductbanks info or not mentioned in document",
       "conduits": "conduits info or not mentioned in document",
       "undergrounds_others": "other undergrounds info or not mentioned in document",
       "undergrounds_description": "consolidated summary of ductbanks + conduits + undergrounds_others or not mentioned in document"
     }},
     "environment": {{
       "scope_of_work": "environment scope content or not mentioned in document",
       "required_activities": "environment activities content or not mentioned in document",
       "oil_containments": "oil containments info or not mentioned in document",
       "dust_and_noise": "dust and noise info or not mentioned in document",
       "environment_others": "other environment info or not mentioned in document",
       "environment_description": "consolidated summary of oil_containments + dust_and_noise + environment_others or not mentioned in document"
     }},
     "substation_structures": {{
       "scope_of_work": "substation structures scope content or not mentioned in document",
       "required_activities": "substation structures activities content or not mentioned in document",
       "equipment_and_support_structures": "equipment and support structures info or not mentioned in document",
       "bus_support_structures": "bus support structures info or not mentioned in document",
       "substation_structures_others": "other substation structures info or not mentioned in document",
       "substation_structures_description": "consolidated summary of equipment_and_support_structures + bus_support_structures + substation_structures_others or not mentioned in document"
     }},
     "firewalls_and_barriers": {{
       "scope_of_work": "firewalls and barriers scope content or not mentioned in document",
       "required_activities": "firewalls and barriers activities content or not mentioned in document",
       "transformer_firewalls": "transformer firewalls info or not mentioned in document",
       "blast_and_arc_barriers": "blast and arc barriers info or not mentioned in document",
       "firewalls_and_barriers_others": "other firewalls and barriers info or not mentioned in document",
       "firewalls_and_barriers_description": "consolidated summary of transformer_firewalls + blast_and_arc_barriers + firewalls_and_barriers_others or not mentioned in document"
     }},
     "line_structures": {{
       "scope_of_work": "line structures scope content or not mentioned in document",
       "required_activities": "line structures activities content or not mentioned in document",
       "monopoles": "monopoles info or not mentioned in document",
       "lattice_towers": "lattice towers info or not mentioned in document",
       "line_structures_others": "other line structures info or not mentioned in document",
       "line_structures_description": "consolidated summary of monopoles + lattice_towers + line_structures_others or not mentioned in document"
     }},
     "protection_and_control": {{
       "scope_of_work": "protection and control scope content or not mentioned in document",
       "required_activities": "protection and control activities content or not mentioned in document",
       "protection_relays_and_schemes": "protection relays and schemes info or not mentioned in document",
       "scada_RTU_and_Automation": "SCADA RTU and automation info or not mentioned in document",
       "protection_and_control_others": "other protection and control info or not mentioned in document",
       "protection_and_control_description": "consolidated summary of protection_relays_and_schemes + scada_RTU_and_Automation + protection_and_control_others or not mentioned in document"
     }},
     "metering": {{
       "scope_of_work": "metering scope content or not mentioned in document",
       "required_activities": "metering activities content or not mentioned in document",
       "metering_cts_and_vts": "metering CTs and VTs info or not mentioned in document",
       "meters_and_recorders": "meters and recorders info or not mentioned in document",
       "metering_others": "other metering info or not mentioned in document",
       "metering_description": "consolidated summary of metering_cts_and_vts + meters_and_recorders + metering_others or not mentioned in document"
     }},
     "telecom_and_teleprotection": {{
       "scope_of_work": "telecom and teleprotection scope content or not mentioned in document",
       "required_activities": "telecom and teleprotection activities content or not mentioned in document",
       "switching_routing_and_transport": "switching routing and transport info or not mentioned in document",
       "radio_and_wan_access": "radio and WAN access info or not mentioned in document",
       "telecom_and_teleprotection_others": "other telecom and teleprotection info or not mentioned in document",
       "telecom_and_teleprotection_description": "consolidated summary of switching_routing_and_transport + radio_and_wan_access + telecom_and_teleprotection_others or not mentioned in document"
     }}
   }}
}}

**CRITICAL**: 
- Return ONLY the JSON object. No explanation, no markdown, no extra text.
- Use empty strings ("") for basic fields where no information is found
- Use "not mentioned in document" for component-specific fields where no information is found
- Only include components in the components object that are actually identified in the document
- Date must be in YYYY-MM-DD format only
- Components must use the exact names from the valid list above
- Each included component MUST have all 6 fields: scope_of_work, required_activities, 3 sub-component fields, and 1 consolidated description field
- Do not perform mathematical calculations or interpretations for any component's fields

Extract the metadata now:
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
            return self._get_rfi_default_metadata()

    def _validate_rfi_metadata(self, metadata: Dict) -> Dict:
        """Validate and clean RFI metadata (17 components format with sub-components and consolidated descriptions)"""
        validated = {
            "project_name": "",
            "client": "",
            "industry": "", 
            "region": "",
            "prepared_date": "",
            "field_type": "",
            "voltage": "",
            "contract_types": "",
            "pricing": "",
            "location": "",
            "state": "",
            "country": "",
            "components": {}
        }
        
        # Validate basic fields
        for field in ['project_name', 'client', 'industry', 'region', 'prepared_date','field_type','voltage','contract_types','pricing','location','state','country']:
            value = metadata.get(field, '')
            if isinstance(value, str):
                value = value.strip()
                # Clean up common placeholder values
                if value.lower() in ['none', 'null', 'undefined', 'n/a', 'not specified', 'not mentioned in document']:
                    value = ''
                elif len(value) > 200:  # Limit field length
                    value = value[:200] + '...'
            validated[field] = value if isinstance(value, str) else ''
        
        # Validate components with 17 components structure including consolidated descriptions
        components = metadata.get('components', {})
        if isinstance(components, dict):
            for comp_code, comp_data in components.items():
                # Only allow valid component codes
                if comp_code in self.valid_components and isinstance(comp_data, dict):
                    validated_comp = {}
                    
                    # Validate common fields
                    for common_field in ['scope_of_work', 'required_activities']:
                        sub_value = comp_data.get(common_field, '')
                        if isinstance(sub_value, str):
                            sub_value = sub_value.strip()
                            if sub_value.lower() in ['none', 'null', 'undefined', 'n/a', 'not specified']:
                                sub_value = 'not mentioned in document'
                        validated_comp[common_field] = sub_value if isinstance(sub_value, str) else 'not mentioned in document'
                    
                    # Validate sub-component fields
                    sub_component_fields = self.valid_components[comp_code]['sub_components']
                    for sub_comp_field in sub_component_fields:
                        sub_value = comp_data.get(sub_comp_field, '')
                        if isinstance(sub_value, str):
                            sub_value = sub_value.strip()
                            if sub_value.lower() in ['none', 'null', 'undefined', 'n/a', 'not specified']:
                                sub_value = 'not mentioned in document'
                        validated_comp[sub_comp_field] = sub_value if isinstance(sub_value, str) else 'not mentioned in document'
                    
                    # Validate consolidated description field
                    description_field = self.valid_components[comp_code]['description_field']
                    desc_value = comp_data.get(description_field, '')
                    if isinstance(desc_value, str):
                        desc_value = desc_value.strip()
                        if desc_value.lower() in ['none', 'null', 'undefined', 'n/a', 'not specified']:
                            desc_value = 'not mentioned in document'
                    validated_comp[description_field] = desc_value if isinstance(desc_value, str) else 'not mentioned in document'
                    
                    # Only add component if it has some meaningful content (not all "not mentioned in document")
                    has_content = any(
                        value and value != 'not mentioned in document' 
                        for value in validated_comp.values()
                    )
                    
                    if has_content:
                        validated['components'][comp_code] = validated_comp
        
        return validated

    def _get_rfi_default_metadata(self) -> Dict:
        """Get default RFI metadata structure (17 components format with consolidated descriptions)"""
        return {
            "project_name": "",
            "client": "",
            "industry": "",
            "region": "",
            "prepared_date": "",
            "field_type": "",
            "voltage": "",
            "contract_types": "",
            "pricing": "",
            "location": "",
            "state": "",
            "country": "",
            "components": {}
        }

    def get_status_info(self) -> Dict:
        """Get status information about the enhanced RFI metadata extractor with 17 components and consolidated descriptions"""
        return {
            "extractor_type": "RFI_METADATA_17_COMPONENTS_WITH_SUB_COMPONENTS_AND_CONSOLIDATED_DESCRIPTIONS",
            "fields_count": len(self.new_rfi_fields),
            "fields": self.new_rfi_fields,
            "components": {comp_code: comp_info for comp_code, comp_info in self.valid_components.items()},
            "total_components": len(self.valid_components),
            "chunking_enabled": False,
            "verbalization_enabled": False,
            "first_10_pages_extraction": True,
            "component_sub_components": True,
            "consolidated_descriptions": True,
            "fields_per_component": 6,  # scope_of_work + required_activities + 3 sub-component fields + 1 consolidated description
            "client_initialized": self.verbalizer.client is not None,
            "status": "ready" if self.verbalizer.client else "client_unavailable",
            "reuses_existing_client": True,
            "enhancement": "DI_text + first_10_pages_comprehensive_content + 17_components_with_sub_components_and_consolidated_descriptions"
        }