"""
Prompts for RFI and RFP document metadata extraction using LLM
Contains ONLY the prompts used for extracting document-level metadata
Specialized for both RFI (8 fields) and RFP (11 fields) documents
"""

class DocumentMetadataPrompts:
    """Document metadata extraction prompt templates for both RFI and RFP documents"""
    
    @staticmethod
    def get_rfi_description_prompt(full_document_text: str) -> str:
        """
        Get the RFI description generation prompt (800 words comprehensive summary)
        
        Args:
            full_document_text: Complete text content from RFI document
            
        Returns:
            str: Prompt for generating comprehensive RFI description
        """
        return f"""
You are an expert technical writer specializing in power infrastructure projects. Write a comprehensive 800-word summary of this RFI document in flowing paragraph format.

**CRITICAL: Write ONLY in paragraph format - NO JSON, NO bullet points, NO structured data.**

**RFI DOCUMENT CONTENT:**
{full_document_text}

**WRITING INSTRUCTIONS:**
Write exactly 800 words of flowing prose that covers:
- Document purpose and requesting organization
- Project scope, location, and technical requirements  
- Equipment specifications and infrastructure details
- Engineering standards and compliance requirements
- Information being requested from contractors
- Submission requirements and timeline
- Technical expertise and experience requirements
- All content from tables, images, and structured data

**WRITING STYLE:**
- Use natural paragraph transitions
- Write in third person professional tone
- Include specific technical details, numbers, and dates
- Maintain flow between topics
- Focus on power/energy infrastructure context

**SAMPLE OPENING:**
"This Request for Information document issued by [Organization] seeks comprehensive information from qualified engineering firms regarding the [Project Name] project. The initiative involves [technical scope] at [location] and encompasses [key requirements]..."

Write your 800-word summary now (paragraph format only):
        """

    @staticmethod     
    def get_duration_extraction_prompt(full_document_text: str) -> str:
        """
        Get the duration extraction prompt for RFI documents
        
        Args:
            full_document_text: Complete text content from RFI document
            
        Returns:
            str: Prompt for extracting project duration
        """
        return f"""
You are an expert at extracting project duration information from RFI documents.

**CRITICAL INSTRUCTION: Return ONLY the duration text - NO JSON, NO additional formatting.**

**FULL RFI DOCUMENT TEXT:**
{full_document_text}

**DURATION EXTRACTION REQUIREMENTS:**

Look for project duration information in these formats:
1. **Direct Duration Statements**: "Project duration: X months/years", "Timeline: X months", "Duration: X years"
2. **Timeline Ranges**: "Start date to end date", "From [date] to [date]"
3. **Phase-based Duration**: Multiple phases with individual durations
4. **Milestone-based Timeline**: "Implementation over X months", "Delivery within X months/years"
5. **Tables and Schedules**: Project schedules, timeline charts, milestone tables
6. **Response Timeline**: "Information needed for X-year project", "Long-term project spanning X years"

**EXTRACTION GUIDELINES:**
- Look across ALL pages and sections for timeline information
- Check tables and structured content for timeline information
- If multiple durations mentioned, prioritize the overall project duration
- Include units (months, years, weeks)
- If only start/end dates given, calculate the duration
- Consider both development and implementation phases

**RESPONSE FORMAT:**
Return ONLY the duration in simple text format:
- "24 months" or "3 years" or "18-24 months"
- If no duration found: "Not mentioned in RFI"
- If unclear: "Duration not clearly specified"

**EXAMPLES OF GOOD RESPONSES:**
- "24 months"
- "3 years"
- "18-24 months"
- "109 weeks"
- "Not mentioned in RFI"

Extract the duration now (return ONLY the duration text):
        """

    @staticmethod
    def get_rfi_extraction_prompt(document_text: str):
        """
        Get the RFI metadata extraction prompt for 8 fields
        
        Args:
            document_text: Complete text content from document
            
        Returns:
            str: Complete metadata extraction prompt for RFI with 8 fields
        """
        return f"""
You are an expert RFI (Request for Information) analyzer. Extract EXACTLY 8 metadata fields from the document. Return ONLY a valid JSON object.

**DOCUMENT TEXT:**
{document_text}

**EXTRACTION REQUIREMENTS:**

1. **document_id**: Find the RFI number, document ID, or reference number. Look for patterns like "RFI No:", "Document ID:", "Reference:", etc.

2. **client_name**: Identify the organization requesting the information. Look for "Client:", "Owner:", issuing organization names, or companies requesting the RFI.

3. **domain_category**: MUST select from these domains ONLY:
   - "Renewable Energy"
   - "Energy Infrastructure & Grid Modernization"  
   - "Conventional Power Systems"
   - "Resource Sector Electrification & Integration"
   - "Environmental & Regulatory Services"
   - "International & Remote Community Energy Projects"
   
   If no clear domain is found, use "Not mentioned in RFI"

4. **service_category**: MUST select from these services ONLY:

   **For Renewable Energy:**
   - "Site selection and feasibility studies"
   - "Resource assessment (wind speed, solar irradiation, hydrology)"
   - "Environmental permitting and approvals"
   - "Detailed electrical and civil engineering design"
   - "Grid interconnection and impact studies"
   - "Independent Engineer (IE) and Owner's Engineer (OE) services"
   - "Procurement and construction oversight"
   - "SCADA and control systems integration"

   **For Energy Infrastructure & Grid Modernization:**
   - "Power system planning (load flow, short-circuit, contingency analysis)"
   - "Substation layout and protection design"
   - "Smart meter and grid automation consulting"
   - "Renewable integration into existing grids"
   - "Distributed energy system modeling and control"
   - "Grid modernization roadmap development"
   - "SCADA and communication systems design"
   - "Arc flash and grounding studies"

   **For Conventional Power Systems:**
   - "Retrofit design and emissions reduction planning"
   - "Regulatory compliance and license support"
   - "Equipment and system upgrade engineering"
   - "Decommissioning and remediation planning"
   - "Safety analysis and QA/QC inspections"
   - "Performance optimization and life extension analysis"

   **For Resource Sector Electrification & Integration:**
   - "Power supply studies for remote operations"
   - "Diesel replacement with renewables or hybrid systems"
   - "Transmission line routing and permitting"
   - "On-site energy storage and backup systems"
   - "Load forecasting and reliability assessments"
   - "Grid connection strategy and economic analysis"

   **For Environmental & Regulatory Services:**
   - "Environmental impact assessments (EIA)"
   - "Public and Indigenous consultation support"
   - "Permitting (federal, provincial, municipal)"
   - "Climate risk and adaptation planning"
   - "Biodiversity, habitat, and wildlife impact studies"
   - "GHG emissions and carbon accounting"
   - "Sustainability/ESG reporting and disclosures"

   **For International & Remote Community Energy Projects:**
   - "Off-grid and hybrid system design"
   - "Stakeholder and community engagement"
   - "Socioeconomic impact assessments"
   - "Electrification master planning"
   - "Capacity building and training"
   - "Procurement and construction monitoring"

   If no matching service is found, use "Not mentioned in RFI"

5. **project_title**: Find the main project name, RFI title, or subject. Look for document titles, project names, or RFI subjects in headers or main content.

6. **rfi_description**: Create a comprehensive 800-word description of the RFI content, requirements, scope, and key information. Include project details, technical requirements, and important context.

7. **submission_date**: Extract response deadline or submission dates. Look for "Response Deadline:", "Due Date:", "Submission Date:", etc. Use YYYY-MM-DD format.

8. **duration**: Extract project timeline, duration, or schedule information. Look for project phases, timelines, completion dates, or duration estimates.

**RESPONSE FORMAT - ONLY JSON:**
{{
    "document_id": "extracted ID or 'Not Specified'",
    "client_name": "extracted client name or 'Not Specified'",
    "domain_category": "exact domain from list or 'Not mentioned in RFI'",
    "service_category": "exact service from list or 'Not mentioned in RFI'",
    "project_title": "extracted title or 'Not Specified'",
    "rfi_description": "comprehensive 800-word description",
    "submission_date": "date in YYYY-MM-DD or 'Not Specified'",
    "duration": "extracted timeline/duration or 'Not Specified'"
}}

**CRITICAL**: Return ONLY the JSON object. No explanation, no markdown, no extra text.
        """

    @staticmethod
    def get_rfp_extraction_prompt(document_text: str):
        """
        Get the RFP metadata extraction prompt for 11 fields
        
        Args:
            document_text: Complete text content from document
            
        Returns:
            str: Complete metadata extraction prompt for RFP with 11 fields
        """
        return f"""
You are an expert Power Business Unit RFP analyzer. Extract EXACTLY 11 metadata fields from the document. Return ONLY a valid JSON object.

**DOCUMENT TEXT:**
{document_text}

**EXTRACTION REQUIREMENTS:**

1. **project_title**: Find the main project name, RFP title, or proposal subject. Look for document titles, project codes, or proposal names in headers or main content.

2. **client_name**: Identify the organization requesting the services. Look for "To:", "Client:", recipient names, or organizations issuing the RFP.

3. **vendor_name**: Find the service provider or responding organization. Look for "From:", company names submitting the proposal, or service provider information.

4. **submission_date**: Extract document dates. Look for submission dates, proposal dates, or document creation dates. Use YYYY-MM-DD format.

5. **domain_category**: MUST select from these Power Business Unit domains ONLY:
   - "Renewable Energy"
   - "Energy Infrastructure & Grid Modernization"  
   - "Conventional Power Systems"
   - "Resource Sector Electrification & Integration"
   - "Environmental & Regulatory Services"
   - "International & Remote Community Energy Projects"
   
   If no clear domain is found, use "Not mentioned in RFP"

6. **service_category**: MUST select from these Power Business Unit services ONLY:

   **For Renewable Energy:**
   - "Site selection and feasibility studies"
   - "Resource assessment (wind speed, solar irradiation, hydrology)"
   - "Environmental permitting and approvals"
   - "Detailed electrical and civil engineering design"
   - "Grid interconnection and impact studies"
   - "Independent Engineer (IE) and Owner's Engineer (OE) services"
   - "Procurement and construction oversight"
   - "SCADA and control systems integration"

   **For Energy Infrastructure & Grid Modernization:**
   - "Power system planning (load flow, short-circuit, contingency analysis)"
   - "Substation layout and protection design"
   - "Smart meter and grid automation consulting"
   - "Renewable integration into existing grids"
   - "Distributed energy system modeling and control"
   - "Grid modernization roadmap development"
   - "SCADA and communication systems design"
   - "Arc flash and grounding studies"

   **For Conventional Power Systems:**
   - "Retrofit design and emissions reduction planning"
   - "Regulatory compliance and license support"
   - "Equipment and system upgrade engineering"
   - "Decommissioning and remediation planning"
   - "Safety analysis and QA/QC inspections"
   - "Performance optimization and life extension analysis"

   **For Resource Sector Electrification & Integration:**
   - "Power supply studies for remote operations"
   - "Diesel replacement with renewables or hybrid systems"
   - "Transmission line routing and permitting"
   - "On-site energy storage and backup systems"
   - "Load forecasting and reliability assessments"
   - "Grid connection strategy and economic analysis"

   **For Environmental & Regulatory Services:**
   - "Environmental impact assessments (EIA)"
   - "Public and Indigenous consultation support"
   - "Permitting (federal, provincial, municipal)"
   - "Climate risk and adaptation planning"
   - "Biodiversity, habitat, and wildlife impact studies"
   - "GHG emissions and carbon accounting"
   - "Sustainability/ESG reporting and disclosures"

   **For International & Remote Community Energy Projects:**
   - "Off-grid and hybrid system design"
   - "Stakeholder and community engagement"
   - "Socioeconomic impact assessments"
   - "Electrification master planning"
   - "Capacity building and training"
   - "Procurement and construction monitoring"

   If no matching service is found, use "Not mentioned in RFP"

7. **revenue_range**: Extract any revenue, budget, contract value, or financial information mentioned in the RFP. Look for:
   - Project budget ranges (e.g., "$1M-$5M", "Under $10M", "Between $500K-$2M")
   - Contract values or estimated costs
   - Financial scope indicators
   - Budget categories or spending ranges
   
   If no financial information is found, use "Not mentioned in RFP"

8. **region**: Extract geographical location information from the RFP. Look for:
   - **Countries**: Canada, USA, Mexico, UK, Australia, etc.
   - **Provinces/States**: Ontario, Alberta, British Columbia, California, Texas, etc.
   - **Cities**: Toronto, Calgary, Vancouver, Montreal, Ottawa, etc.
   - **Regions**: Atlantic Canada, Western Canada, Pacific Northwest, Northeast USA, etc.
   - **Project locations**: "Located in...", "Project site in...", "Service area..."
   - **Address information**: Street addresses, postal codes, regional identifiers
   - **Geographical references**: Northern Ontario, Southern Alberta, Coastal BC, etc.
   - **Administrative regions**: Federal districts, municipal areas, jurisdictions

   If no geographical location is found, use "Not mentioned in RFP"

9. **project_value**: Extract specific project value, contract amount, or total project cost mentioned in the RFP. Look for:
   - **Exact Contract Values**: "$2.5 million", "$500,000", "$1.2M contract"
   - **Total Project Cost**: "Project value: $3M", "Total cost: $1.5 million"
   - **Contract Amounts**: "Contract amount: $750K", "Award value: $2M"
   - **Project Budget**: "Project budget: $4.2M", "Allocated budget: $1.8M"
   - **Financial Scope**: "Value of services: $900K", "Professional fees: $450K"
   - **Specific Dollar Amounts**: Look for exact monetary values with currency symbols
   - **Project Investment**: "Capital investment: $5M", "Development cost: $3.2M"

   **Different from revenue_range**: This should be a SPECIFIC dollar amount mentioned for THIS project, not a general range.

   If no specific project value is found, use "Not mentioned in RFP"

10. **equipments_used**: Extract the list of equipments used for any power/energy renewable purposes mentioned in the RFP. Look for:
    - "equipment or hardware components"
    - "physical systems used in any power generation, transmission, distribution, or control domains"
    - "List all utility-scale components and grid-integrated systems mentioned"
    - "Identify the infrastructure components and control equipment discussed"
    - "The list of equipment can contain either a single item or multiple items"

    There are certain key equipments in Tech Power OU:
    **SCADA systems**: master stations, HMI, operator consoles
    **Programmable Logic Controllers (PLC)**: sensors, actuators
    **Remote Terminal Units (RTU)**: SEL-3530 RTAC, GE D20MX, SCADAPack 470, SCADAPack 474, ABB RTU560, Emerson ControlWave Micro, Siemens SICAM A8000, Motorola ACE1000, Motorola ACE3600, Sixnet VersaTRAK 
    **Communication infrastructure**: Ethernet/IP, Modbus, IEC 61850, DNP3, cellular systems, radio systems
    **HVAC systems**: heating, ventilation, air conditioning units—chillers, pumps, actuators, control sensors, DX systems, jet fans, ventilation units
    **Building Automation Systems (BAS)**: sensors, thermostats, DDC controllers, energy management control systems, integration with SCADA/BMS
    **Electrical & Instrumentation Hardware**: Transformers, switchgear, motor control centres (MCC), substation equipment, circuit breakers
    **Instrumentation and field devices**: current/voltage sensors, protective relays, arc‑flash mitigation devices, grounding systems, cable and load schedules 
    **Backup & Power Support**: UPS units, static transfer switches (STS), diesel generators, and emergency backup systems
    **Modern Energy & Grid Equipment**: Energy storage systems (battery energy storage), microgrid controllers, grid‑tie inverters, and generation and distribution lines

    If no specific equipment is found, use "Not mentioned in RFP"
    Make sure that there are no repetition in the final list.

11. **compliance_standard**: Extract the compliance standards mentioned in the RFPs. Look for:
    - regulatory requirements    
    - technical standards       
    - industry codes           
    - certification norms         
    - governing codes           
    - design compliance criteria  
    - engineering standards    
    - conformance specifications  
    - statutory guidelines    
    - mandated codes          
    - safety regulations          
    - utility compliance protocols

    **Compliance standards Examples:**
    "canadian_electrical_code", "cec", "ieee_standards", "csa_standards", "ul_certification",
    "iec_certification", "nerc_reliability_standards", "fips_140_encryption"

    If no compliance standards is found, use "Not mentioned in RFP"

**RESPONSE FORMAT - ONLY JSON:**
{{
    "project_title": "extracted title or 'Not Specified'",
    "client_name": "extracted client name or 'Not Specified'", 
    "vendor_name": "extracted vendor name or 'Not Specified'",
    "submission_date": "date in YYYY-MM-DD or 'Not Specified'",
    "domain_category": "exact domain from Power Business Unit list or 'Not mentioned in RFP'",
    "service_category": "exact service from Power Business Unit list or 'Not mentioned in RFP'",
    "revenue_range": "extracted budget/revenue range or 'Not mentioned in RFP'",
    "region": "extracted geographical location or 'Not mentioned in RFP'",
    "project_value": "extracted specific project value/contract amount or 'Not mentioned in RFP'",
    "equipments_used": "extracted equipment/tools/systems or 'Not mentioned in RFP'",
    "compliance_standard": "extracted specific compliance standard or 'Not mentioned in RFP'"
}}

**CRITICAL**: Return ONLY the JSON object. No explanation, no markdown, no extra text.
        """