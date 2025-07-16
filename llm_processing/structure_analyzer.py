import re
import json
from typing import Dict, List, Optional
from .azure_openai_client import AzureOpenAIClient
from config import STRUCTURE_ANALYSIS_CONFIG

class DocumentStructureAnalyzer:
    """Analyzes document structure using LLM to identify sections and hierarchy"""
    
    def __init__(self):
        self.llm_client = AzureOpenAIClient()
        self.config = STRUCTURE_ANALYSIS_CONFIG
    
    def analyze_document_structure(self, raw_text: str) -> Dict:
        """
        Main method to analyze complete document structure
        Returns hierarchical structure with sections, types, and boundaries
        """
        print("🔍 Starting LLM-based document structure analysis...")
        
        try:
            # Split large documents into analyzable chunks
            text_chunks = self.llm_client.chunk_text_for_analysis(raw_text, max_tokens=3000)
            
            all_sections = []
            char_offset = 0
            
            for i, chunk in enumerate(text_chunks):
                print(f"   Analyzing chunk {i+1}/{len(text_chunks)}...")
                
                chunk_sections = self._analyze_chunk_structure(chunk, char_offset)
                if chunk_sections:
                    all_sections.extend(chunk_sections)
                
                char_offset += len(chunk)
            
            # Merge and organize sections
            organized_structure = self._organize_sections(all_sections, raw_text)
            
            # Classify section types
            classified_structure = self._classify_sections(organized_structure, raw_text)
            
            print(f"✅ Structure analysis complete. Found {len(classified_structure.get('sections', []))} sections")
            
            return classified_structure
            
        except Exception as e:
            print(f"❌ Error in structure analysis: {e}")
            return self._fallback_structure_analysis(raw_text)
    
    def _analyze_chunk_structure(self, text_chunk: str, char_offset: int) -> List[Dict]:
        """Analyze structure of a single text chunk"""
        
        system_message = """You are a document structure analyzer specializing in RFP documents. 
        Analyze the given text and identify all document sections with their hierarchy.
        
        Return a JSON object with this exact structure:
        {
            "sections": [
                {
                    "title": "1.0 INTRODUCTION",
                    "hierarchy_level": 1,
                    "start_char": 0,
                    "end_char": 500,
                    "content_preview": "First 100 characters of section content..."
                }
            ]
        }
        
        Rules:
        1. Identify section titles (numbered like 1.0, 1.1, 2.1.1 or descriptive headings)
        2. Determine hierarchy level (1 = main section, 2 = subsection, 3 = sub-subsection)
        3. Provide character positions relative to the given text chunk
        4. Include a brief content preview
        5. Focus on actual document structure, not formatting artifacts"""
        
        user_prompt = f"""Analyze this RFP document text and identify all sections:

{text_chunk}

Return the section structure as specified JSON format."""
        
        try:
            response = self.llm_client.get_structured_completion(user_prompt, system_message)
            
            if "error" in response:
                print(f"⚠️ LLM analysis error: {response['error']}")
                return []
            
            sections = response.get("sections", [])
            
            # Adjust character positions with offset
            for section in sections:
                section["start_char"] += char_offset
                section["end_char"] += char_offset
            
            return sections
            
        except Exception as e:
            print(f"⚠️ Error analyzing chunk: {e}")
            return []
    
    def _organize_sections(self, all_sections: List[Dict], full_text: str) -> Dict:
        """Organize sections into hierarchical structure"""
        
        # Sort sections by start position
        all_sections.sort(key=lambda x: x.get("start_char", 0))
        
        # Remove duplicates and overlaps
        cleaned_sections = self._remove_duplicate_sections(all_sections)
        
        # Ensure complete text coverage
        complete_sections = self._ensure_text_coverage(cleaned_sections, full_text)
        
        return {
            "document_type": "rfp",
            "total_sections": len(complete_sections),
            "sections": complete_sections
        }
    
    def _classify_sections(self, structure: Dict, full_text: str) -> Dict:
        """Classify section types using LLM"""
        
        sections = structure.get("sections", [])
        classified_sections = []
        
        for section in sections:
            try:
                # Extract section content for classification
                start_pos = section.get("start_char", 0)
                end_pos = section.get("end_char", len(full_text))
                section_content = full_text[start_pos:end_pos]
                
                # Classify section type
                section_type = self._classify_single_section(
                    section.get("title", ""), 
                    section_content[:self.config["content_analysis_window"]]
                )
                
                section["section_type"] = section_type
                classified_sections.append(section)
                
            except Exception as e:
                print(f"⚠️ Error classifying section '{section.get('title', 'Unknown')}': {e}")
                section["section_type"] = "general"
                classified_sections.append(section)
        
        structure["sections"] = classified_sections
        return structure
    
    def _classify_single_section(self, title: str, content_preview: str) -> str:
        """Classify a single section type using LLM"""
        
        system_message = """You are an expert at classifying RFP document sections. 
        Analyze the section title and content to determine the most appropriate section type.
        
        Choose from these section types:
        - introduction: Project overview, background, objectives
        - scope_of_work: Detailed work description, deliverables, tasks
        - technical_requirements: Technical specifications, standards, requirements
        - pricing: Cost information, pricing structure, payment terms
        - assumptions: Project assumptions, conditions
        - exclusions: Items excluded from scope, limitations
        - qualifications: Vendor qualifications, experience requirements
        - timeline: Schedule, milestones, duration
        - evaluation: Selection criteria, evaluation process
        - contact_information: Contact details, submission instructions
        - terms_conditions: Legal terms, contract conditions
        - general: Any other content that doesn't fit above categories
        
        Return only the section type (one word)."""
        
        user_prompt = f"""Section Title: {title}
        
Content Preview: {content_preview}

What section type is this?"""
        
        try:
            response = self.llm_client.get_completion(user_prompt, system_message)
            section_type = response.strip().lower()
            
            # Validate response
            valid_types = [
                "introduction", "scope_of_work", "technical_requirements", 
                "pricing", "assumptions", "exclusions", "qualifications",
                "timeline", "evaluation", "contact_information", 
                "terms_conditions", "general"
            ]
            
            if section_type in valid_types:
                return section_type
            else:
                return "general"
                
        except Exception as e:
            print(f"⚠️ Error classifying section type: {e}")
            return "general"
    
    def _remove_duplicate_sections(self, sections: List[Dict]) -> List[Dict]:
        """Remove duplicate and overlapping sections"""
        if not sections:
            return []
        
        cleaned = []
        
        for section in sections:
            is_duplicate = False
            
            for existing in cleaned:
                # Check for significant overlap
                existing_start = existing.get("start_char", 0)
                existing_end = existing.get("end_char", 0)
                section_start = section.get("start_char", 0)
                section_end = section.get("end_char", 0)
                
                overlap_start = max(existing_start, section_start)
                overlap_end = min(existing_end, section_end)
                overlap_length = max(0, overlap_end - overlap_start)
                
                section_length = section_end - section_start
                if section_length > 0 and overlap_length / section_length > 0.7:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                cleaned.append(section)
        
        return cleaned
    
    def _ensure_text_coverage(self, sections: List[Dict], full_text: str) -> List[Dict]:
        """Ensure complete text coverage by filling gaps"""
        if not sections:
            return [{
                "title": "Complete Document",
                "hierarchy_level": 1,
                "start_char": 0,
                "end_char": len(full_text),
                "section_type": "general",
                "content_preview": full_text[:100] + "..." if len(full_text) > 100 else full_text
            }]
        
        # Sort by start position
        sections.sort(key=lambda x: x.get("start_char", 0))
        
        complete_sections = []
        last_end = 0
        
        for i, section in enumerate(sections):
            start_pos = section.get("start_char", 0)
            end_pos = section.get("end_char", len(full_text))
            
            # Fill gap before this section
            if start_pos > last_end:
                gap_content = full_text[last_end:start_pos].strip()
                if len(gap_content) > self.config["min_section_length"]:
                    gap_section = {
                        "title": f"Content Section {len(complete_sections) + 1}",
                        "hierarchy_level": 1,
                        "start_char": last_end,
                        "end_char": start_pos,
                        "section_type": "general",
                        "content_preview": gap_content[:100] + "..." if len(gap_content) > 100 else gap_content
                    }
                    complete_sections.append(gap_section)
            
            # Add current section
            complete_sections.append(section)
            last_end = max(last_end, end_pos)
        
        # Fill final gap
        if last_end < len(full_text):
            final_content = full_text[last_end:].strip()
            if len(final_content) > self.config["min_section_length"]:
                final_section = {
                    "title": "Final Content Section",
                    "hierarchy_level": 1,
                    "start_char": last_end,
                    "end_char": len(full_text),
                    "section_type": "general",
                    "content_preview": final_content[:100] + "..." if len(final_content) > 100 else final_content
                }
                complete_sections.append(final_section)
        
        return complete_sections
    
    def _fallback_structure_analysis(self, raw_text: str) -> Dict:
        """Fallback structure analysis using regex patterns"""
        print("🔄 Using fallback structure analysis...")
        
        sections = []
        
        # Use regex patterns to find sections
        for pattern in self.config["section_title_patterns"]:
            matches = list(re.finditer(pattern, raw_text, re.MULTILINE | re.IGNORECASE))
            for match in matches:
                sections.append({
                    "title": match.group(0).strip(),
                    "hierarchy_level": 1,
                    "start_char": match.start(),
                    "end_char": match.end(),
                    "section_type": "general",
                    "content_preview": raw_text[match.start():match.start()+100] + "..."
                })
        
        # Remove duplicates and organize
        sections = self._remove_duplicate_sections(sections)
        sections = self._ensure_text_coverage(sections, raw_text)
        
        return {
            "document_type": "rfp",
            "total_sections": len(sections),
            "sections": sections,
            "analysis_method": "fallback_regex"
        }
    
    def validate_structure(self, structure: Dict) -> bool:
        """Validate the document structure"""
        if not isinstance(structure, dict):
            return False
        
        sections = structure.get("sections", [])
        if not sections:
            return False
        
        # Check that sections have required fields
        required_fields = ["title", "start_char", "end_char", "section_type"]
        for section in sections:
            if not all(field in section for field in required_fields):
                return False
        
        # Check for overlapping sections
        for i, section1 in enumerate(sections):
            for j, section2 in enumerate(sections[i+1:], i+1):
                if (section1["start_char"] < section2["end_char"] and 
                    section2["start_char"] < section1["end_char"]):
                    # Allow small overlaps but not major ones
                    overlap = min(section1["end_char"], section2["end_char"]) - max(section1["start_char"], section2["start_char"])
                    section1_length = section1["end_char"] - section1["start_char"]
                    if overlap > section1_length * 0.5:
                        return False
        
        return True