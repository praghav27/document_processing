from typing import Dict, List, Optional, Tuple
import re
from .azure_openai_client import AzureOpenAIClient

class ContentMapper:
    """Maps tables and images to document sections using spatial and contextual analysis"""
    
    def __init__(self):
        self.llm_client = AzureOpenAIClient()
    
    def map_multimodal_to_sections(self, structure: Dict, tables: List[Dict], images: List[Dict]) -> Dict:
        """
        Main method to map tables and images to document sections
        Returns enhanced structure with multimodal content mapped to sections
        """
        print("🗺️ Mapping tables and images to document sections...")
        
        sections = structure.get("sections", [])
        content_map = {
            "sections": [],
            "unmapped_tables": [],
            "unmapped_images": [],
            "mapping_stats": {
                "total_tables": len(tables),
                "total_images": len(images),
                "mapped_tables": 0,
                "mapped_images": 0
            }
        }
        
        # Create enhanced sections with multimodal content
        for section in sections:
            enhanced_section = dict(section)  # Copy original section
            enhanced_section["tables"] = []
            enhanced_section["images"] = []
            
            # Map tables to this section
            section_tables = self._find_content_for_section(section, tables, "table")
            enhanced_section["tables"] = section_tables
            content_map["mapping_stats"]["mapped_tables"] += len(section_tables)
            
            # Map images to this section
            section_images = self._find_content_for_section(section, images, "image")
            enhanced_section["images"] = section_images
            content_map["mapping_stats"]["mapped_images"] += len(section_images)
            
            content_map["sections"].append(enhanced_section)
        
        # Find unmapped content
        mapped_table_indices = set()
        mapped_image_indices = set()
        
        for section in content_map["sections"]:
            for table in section["tables"]:
                mapped_table_indices.add(table.get("table_index", -1))
            for image in section["images"]:
                mapped_image_indices.add(image.get("figure_index", -1))
        
        # Add unmapped content
        content_map["unmapped_tables"] = [
            table for i, table in enumerate(tables) 
            if table.get("table_index", i+1) not in mapped_table_indices
        ]
        
        content_map["unmapped_images"] = [
            image for i, image in enumerate(images) 
            if image.get("figure_index", i+1) not in mapped_image_indices
        ]
        
        print(f"✅ Content mapping complete:")
        print(f"   📊 Tables: {content_map['mapping_stats']['mapped_tables']}/{content_map['mapping_stats']['total_tables']} mapped")
        print(f"   🖼️ Images: {content_map['mapping_stats']['mapped_images']}/{content_map['mapping_stats']['total_images']} mapped")
        
        return content_map
    
    def _find_content_for_section(self, section: Dict, content_items: List[Dict], content_type: str) -> List[Dict]:
        """Find tables or images that belong to a specific section"""
        section_content = []
        
        section_start = section.get("start_char", 0)
        section_end = section.get("end_char", float('inf'))
        
        # First pass: Use page-based proximity
        for item in content_items:
            item_page = item.get("page_number", 1)
            
            # Estimate section page range (rough approximation)
            estimated_section_pages = self._estimate_section_pages(section, section_start, section_end)
            
            # Check if item page is within section page range
            if self._is_page_in_section_range(item_page, estimated_section_pages):
                # Use contextual relevance to confirm mapping
                if self._is_contextually_relevant(section, item, content_type):
                    section_content.append(item)
        
        return section_content
    
    def _estimate_section_pages(self, section: Dict, start_char: int, end_char: int) -> Tuple[int, int]:
        """Estimate page range for a section based on character positions"""
        # Rough estimation: ~500 words per page, ~6 characters per word
        chars_per_page = 500 * 6  # ~3000 characters per page
        
        start_page = max(1, (start_char // chars_per_page) + 1)
        end_page = max(start_page, (end_char // chars_per_page) + 1)
        
        return (start_page, end_page)
    
    def _is_page_in_section_range(self, item_page: int, section_page_range: Tuple[int, int]) -> bool:
        """Check if item page is within section page range (with tolerance)"""
        start_page, end_page = section_page_range
        
        # Allow one page tolerance on either side
        tolerance = 1
        return (start_page - tolerance) <= item_page <= (end_page + tolerance)
    
    def _is_contextually_relevant(self, section: Dict, item: Dict, content_type: str) -> bool:
        """Use LLM to determine if content item is contextually relevant to section"""
        
        section_title = section.get("title", "Unknown Section")
        section_type = section.get("section_type", "general")
        item_content = item.get("content", "")
        
        # For simple cases, use rule-based matching
        if self._simple_relevance_check(section_title, section_type, item_content, content_type):
            return True
        
        # For complex cases, use LLM analysis (optional, to avoid too many API calls)
        if len(item_content) > 100:  # Only use LLM for substantial content
            return self._llm_relevance_check(section, item, content_type)
        
        return False
    
    def _simple_relevance_check(self, section_title: str, section_type: str, item_content: str, content_type: str) -> bool:
        """Simple rule-based relevance checking"""
        
        # Convert to lowercase for matching
        title_lower = section_title.lower()
        type_lower = section_type.lower()
        content_lower = item_content.lower()
        
        # Define keyword mappings
        relevance_keywords = {
            "electrical": ["electrical", "power", "transformer", "voltage", "circuit", "breaker", "wiring"],
            "civil": ["civil", "concrete", "foundation", "structural", "grading", "drainage"],
            "pricing": ["cost", "price", "$", "budget", "fee", "payment", "amount"],
            "technical": ["technical", "specification", "requirement", "standard", "design"],
            "scope": ["scope", "work", "deliverable", "task", "service", "installation"],
            "schedule": ["schedule", "timeline", "duration", "milestone", "phase", "completion"]
        }
        
        # Check if section keywords match item content
        for category, keywords in relevance_keywords.items():
            if any(keyword in title_lower or keyword in type_lower for keyword in keywords):
                if any(keyword in content_lower for keyword in keywords):
                    return True
        
        return False
    
    def _llm_relevance_check(self, section: Dict, item: Dict, content_type: str) -> bool:
        """Use LLM to check contextual relevance (used sparingly)"""
        
        section_title = section.get("title", "Unknown")
        section_type = section.get("section_type", "general")
        item_content = item.get("content", "")[:300]  # Limit content for API efficiency
        
        system_message = f"""You are analyzing whether a {content_type} belongs to a specific document section.
        
        Determine if the {content_type} content is relevant to the given section.
        Consider:
        1. Topical relevance (does the content relate to the section topic?)
        2. Functional relevance (does it support or explain the section?)
        3. Contextual fit (would this logically appear in this section?)
        
        Respond with only "YES" or "NO"."""
        
        user_prompt = f"""Section Title: {section_title}
Section Type: {section_type}

{content_type.title()} Content: {item_content}

Is this {content_type} relevant to this section?"""
        
        try:
            response = self.llm_client.get_completion(user_prompt, system_message)
            return response.strip().upper() == "YES"
        except Exception as e:
            print(f"⚠️ Error in LLM relevance check: {e}")
            return False  # Default to not relevant if LLM fails
    
    def calculate_content_proximity(self, content_page: int, section_pages: Tuple[int, int]) -> float:
        """Calculate proximity score between content and section pages"""
        start_page, end_page = section_pages
        
        if start_page <= content_page <= end_page:
            return 1.0  # Perfect match
        
        # Calculate distance from section
        if content_page < start_page:
            distance = start_page - content_page
        else:
            distance = content_page - end_page
        
        # Return inverse proximity score (closer = higher score)
        return max(0.0, 1.0 - (distance * 0.2))  # Each page away reduces score by 0.2
    
    def resolve_mapping_conflicts(self, mappings: Dict) -> Dict:
        """Resolve conflicts when content could belong to multiple sections"""
        
        sections = mappings.get("sections", [])
        
        # Find content items that appear in multiple sections
        table_counts = {}
        image_counts = {}
        
        for section in sections:
            for table in section.get("tables", []):
                table_id = table.get("table_index", id(table))
                table_counts[table_id] = table_counts.get(table_id, 0) + 1
            
            for image in section.get("images", []):
                image_id = image.get("figure_index", id(image))
                image_counts[image_id] = image_counts.get(image_id, 0) + 1
        
        # Remove duplicates, keeping the best match
        for section in sections:
            # Filter tables
            unique_tables = []
            for table in section.get("tables", []):
                table_id = table.get("table_index", id(table))
                if table_counts.get(table_id, 0) == 1:
                    unique_tables.append(table)
                elif self._is_best_match_for_content(section, table, sections, "table"):
                    unique_tables.append(table)
            section["tables"] = unique_tables
            
            # Filter images
            unique_images = []
            for image in section.get("images", []):
                image_id = image.get("figure_index", id(image))
                if image_counts.get(image_id, 0) == 1:
                    unique_images.append(image)
                elif self._is_best_match_for_content(section, image, sections, "image"):
                    unique_images.append(image)
            section["images"] = unique_images
        
        return mappings
    
    def _is_best_match_for_content(self, current_section: Dict, content_item: Dict, all_sections: List[Dict], content_type: str) -> bool:
        """Determine if current section is the best match for a content item"""
        
        content_id = content_item.get(f"{content_type[:-1]}_index" if content_type.endswith('e') else f"{content_type}_index", id(content_item))
        content_page = content_item.get("page_number", 1)
        
        best_score = 0
        best_section = None
        
        for section in all_sections:
            # Check if this section contains the content
            section_content = section.get(f"{content_type}s", [])
            if not any(item.get(f"{content_type[:-1]}_index" if content_type.endswith('e') else f"{content_type}_index", id(item)) == content_id for item in section_content):
                continue
            
            # Calculate relevance score
            section_pages = self._estimate_section_pages(
                section, 
                section.get("start_char", 0), 
                section.get("end_char", float('inf'))
            )
            
            proximity_score = self.calculate_content_proximity(content_page, section_pages)
            
            # Add relevance bonus
            relevance_bonus = 0.5 if self._simple_relevance_check(
                section.get("title", ""),
                section.get("section_type", ""),
                content_item.get("content", ""),
                content_type
            ) else 0
            
            total_score = proximity_score + relevance_bonus
            
            if total_score > best_score:
                best_score = total_score
                best_section = section
        
        return best_section == current_section if best_section else False
    
    def get_mapping_statistics(self, content_map: Dict) -> Dict:
        """Generate detailed mapping statistics"""
        
        stats = content_map.get("mapping_stats", {})
        sections = content_map.get("sections", [])
        
        detailed_stats = {
            "overview": stats,
            "section_breakdown": [],
            "unmapped_content": {
                "tables": len(content_map.get("unmapped_tables", [])),
                "images": len(content_map.get("unmapped_images", []))
            }
        }
        
        for section in sections:
            section_stats = {
                "section_title": section.get("title", "Unknown"),
                "section_type": section.get("section_type", "general"),
                "tables_count": len(section.get("tables", [])),
                "images_count": len(section.get("images", [])),
                "has_multimodal_content": len(section.get("tables", [])) > 0 or len(section.get("images", [])) > 0
            }
            detailed_stats["section_breakdown"].append(section_stats)
        
        return detailed_stats