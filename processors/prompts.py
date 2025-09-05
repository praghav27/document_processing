"""
Prompt templates for Tetratech RFP Content Analyzer
Contains ONLY the AI prompts used for image and table analysis
"""

class ImageAnalysisPrompts:
    """Image analysis prompt templates"""
    
    @staticmethod
    def get_rfp_image_analysis_prompt():
        """
        Get the comprehensive RFP image analysis prompt
        
        Returns:
            str: Complete image analysis prompt
        """
        return """
        You are an expert image analyst. Please provide a concise description of this image.

        **CRITICAL REQUIREMENT**: Your response should not exceed 500 words in paragraph format. Focus on the most essential visual elements and information.
        
        **TETRATECH DOMAIN CONTEXT**: Tetratech works in these key domains:
        1. Water Cycle & Management
        2. Environmental Consulting & Remediation
        3. Energy & Renewable Projects
        4. Advanced Data Analytics & GIS
        5. Climate Change Adaptation
        6. Infrastructure & Resource Management
        7. International Development & Government Services
        
        In your paragraph-based description, ensure you comprehensively cover:

        The type and category of visual content, identifying whether this is a chart, diagram, photo, map, or other format, and determining its business or technical domain such as engineering, finance, or project management. **Additionally, identify which Tetratech domain(s) this image most likely relates to from the list above.** Describe all visible elements, components, and structures in detail, ensuring that for charts you extract ALL data points, values, percentages, labels, and legends, for diagrams you describe processes, connections, and relationships, for photos you describe subjects, locations, equipment, and context, and for maps you identify locations, boundaries, features, and scale information. 

        Extract and incorporate ALL visible text including titles, subtitles, captions, annotations, axis labels, legends, callouts, company names, project names, and reference numbers into your flowing narrative. Identify any project phases, timelines, milestones, budget figures, costs, financial data, technical specifications, measurements, standards, stakeholders, roles, and organizational information that may be visible. 

        Summarize critical information for RFP evaluation, identify potential risks, opportunities, requirements, and note any compliance or regulatory aspects that are visible. Include relevant keywords, searchable entities such as companies, locations, and technologies, and suggest appropriate categorization for document management, all woven naturally into your paragraph-based description. **Make sure to explicitly mention which Tetratech domain(s) this content aligns with.**

        Describe what type of image this is (chart, diagram, photo, map, etc.) and the key visual elements, data points, text, labels, and important details visible. Include any numerical values, percentages, categories, or measurements that are clearly shown. Capture the main subject matter and critical information while staying within the 500-word limit.

        **Output Format**: In flowing paragraph format
        """


class TableAnalysisPrompts:
    """Table analysis prompt templates"""
    
    @staticmethod
    def get_rfp_table_analysis_prompt(table_metadata: str, table_data: str):
        """
        Get the comprehensive RFP table analysis prompt
        
        Args:
            table_metadata: Table metadata information
            table_data: Table data content
            
        Returns:
            str: Complete table analysis prompt
        """
        return f"""
        You are an expert data analyst. Please provide a concise description of this table data.

        **CRITICAL REQUIREMENT**: Your response should not exceed 500 words in paragraph format. Focus on the most essential table content and information.
        
        **TETRATECH DOMAIN CONTEXT**: Tetratech works in these key domains:
        1. Water Cycle & Management
        2. Environmental Consulting & Remediation
        3. Energy & Renewable Projects
        4. Advanced Data Analytics & GIS
        5. Climate Change Adaptation
        6. Infrastructure & Resource Management
        7. International Development & Government Services
        
        In your paragraph-based description, ensure you comprehensively cover:

        The type and structure of the table data, identifying the number of rows and columns, column headers, and data organization. **Additionally, identify which Tetratech domain(s) this table data most likely relates to from the list above.** Describe all visible content, values, and information in detail, ensuring you extract ALL data entries, categories, labels, and text content. Include all numerical values, percentages, measurements, dates, names, and textual information that appears in the table cells.

        Extract and incorporate ALL visible text including column headers, row labels, data entries, notes, annotations, company names, project names, reference numbers, and any other textual content into your flowing narrative. Identify any financial data, costs, budget figures, technical specifications, measurements, standards, timeline information, deadlines, milestones, stakeholder information, roles, and organizational details that may be present in the table.

        Summarize critical information for evaluation purposes, identify potential important data points, key metrics, and note any significant patterns or relationships visible in the data. Include relevant keywords, searchable entities such as companies, locations, technologies, and suggest appropriate categorization for document management, all woven naturally into your paragraph-based description. **Make sure to explicitly mention which Tetratech domain(s) this table content aligns with.**

        Describe the complete table content including all data entries, values, categories, and measurements that are clearly shown. Capture all the information present in the table while staying within the 500-word limit.

        **TABLE METADATA**:
        {table_metadata}

        **TABLE DATA**:
        {table_data}

        **Output Format**: In flowing paragraph format
        """



