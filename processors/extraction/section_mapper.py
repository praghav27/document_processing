import re
from typing import Dict, List

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class SectionMapper:
    """Handle section mapping and position logic"""
    
    def __init__(self):
        pass
    
    # def _find_footer_position(self, page_number: int) -> dict:
    #     """Find footer X,Y position on given page using role attribute"""
    #     for element in self.text_elements:
    #         if (element.get('page_number') == page_number and 
    #             element.get('role') == 'pageFooter'):
    #             footer_pos = element.get('position', {})
    #             footer_x = footer_pos.get('x', 0)
    #             footer_y = footer_pos.get('y', 0)
    #             print(f"Footer found on page {page_number} at position: ({footer_x}, {footer_y})")
    #             return {"x": footer_x, "y": footer_y}
    #     return None
    
    def get_position_info(self, paragraph):
        """Extract position information from bounding regions"""
        if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
            bounding_region = paragraph.bounding_regions[0]
            if hasattr(bounding_region, 'polygon') and bounding_region.polygon:
                # Get the top-left point (usually first point in polygon)
                polygon = bounding_region.polygon
                if len(polygon) >= 2:
                    return {
                        "x": polygon[0],
                        "y": polygon[1],
                        "page": getattr(bounding_region, 'page_number', 1)
                    }
        return {"x": 0, "y": 0, "page": 1}
    
    def find_closest_section(self, target_page: int, target_position: Dict, text_elements: List[Dict]) -> Dict:
        """Find the closest preceding section header on the same page"""
        section_roles = ['sectionHeading', 'subsectionHeading', 'title']
        
        # Filter text elements to same page and section roles
        page_sections = [
            elem for elem in text_elements 
            if elem['page_number'] == target_page and elem['role'] in section_roles
        ]
        
        if not page_sections:
            # No sections on this page, try previous pages
            for page in range(target_page - 1, 0, -1):
                page_sections = [
                    elem for elem in text_elements 
                    if elem['page_number'] == page and elem['role'] in section_roles
                ]
                if page_sections:
                    # Get the last section from the previous page
                    closest_section = max(page_sections, key=lambda x: x['position']['y'])
                    distance = None  # Cross-page distance
                    break
            else:
                # No sections found anywhere
                return {
                    "section_role": "unknown",
                    "section_content": "No section header found",
                    "section_page": target_page,
                    "section_paragraph_index": None,
                    "distance_from_section": None
                }
        else:
            # Find sections that come before the target position
            preceding_sections = [
                elem for elem in page_sections 
                if elem['position']['y'] < target_position['y']
            ]
            
            if preceding_sections:
                # Get the closest preceding section (highest y value)
                closest_section = max(preceding_sections, key=lambda x: x['position']['y'])
                distance = abs(target_position['y'] - closest_section['position']['y'])
            else:
                # No preceding sections, get the first section on the page
                closest_section = min(page_sections, key=lambda x: x['position']['y'])
                distance = abs(target_position['y'] - closest_section['position']['y'])
        
        return {
            "section_role": closest_section['role'],
            "section_content": closest_section['content'][:100],  # Truncate for display
            "section_page": closest_section['page_number'],
            "section_paragraph_index": closest_section['paragraph_index'],
            "distance_from_section": distance
        }
    
    def get_section_info_from_closest_text_chunk(self, target_page: int, target_position: Dict, text_elements: List[Dict]) -> Dict:
        """Get section_name and section_no from closest text chunk for table/image mapping"""
        # Find the closest text chunk based on page and position
        closest_chunk = None
        min_distance = float('inf')
        section_info = self.find_closest_section(target_page, target_position, text_elements)
    
        # Extract section name and number from the section content
        section_content = section_info.get('section_content', '')
        # Try to extract section number and name from content
        match = re.match(r'^\s*(\d+\.\d+)\s+(.+)', section_content)
        if match:
            return {
                'section_name': match.group(2).strip(),
                'section_no': match.group(1)
            }
        else:
            return {
                'section_name': section_content[:50] if section_content else 'Unknown Section',
                'section_no': 'auto'
            }