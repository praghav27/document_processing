import re
from typing import Dict, List, Optional
from .azure_openai_client import AzureOpenAIClient
from config import SECTION_CLASSIFICATION

class MetadataGenerator:
    """Generates rich metadata for document chunks using LLM analysis"""
    
    def __init__(self):
        self.llm_client = AzureOpenAIClient()
        self.classification_config = SECTION_CLASSIFICATION
    
    def generate_chunk_metadata(self, chunk_content: str, section_info: Dict, document_metadata: Dict, chunk_index: int, total_chunks: int) -> Dict:
        """Generate comprehensive metadata for a single chunk"""
        
        # Extract basic metadata
        base_metadata = {
            "chunk_id": self._generate_chunk_id(document_metadata, section_info, chunk_index),
            "content": chunk_content,
            "section_type": section_info.get("section_type", "general"),
            "section_title": section_info.get("title", "Unknown Section"),
            "section_hierarchy": self._extract_section_hierarchy(section_info.get("title", "")),
            "page_number": self._estimate_chunk_page(section_info, chunk_index, total_chunks),
            "chunk_number": chunk_index,
            "total_chunks_in_section": total_chunks,
            "token_count": self.llm_client.estimate_tokens(chunk_content),
            "char_count": len(chunk_content)
        }
        
        # Add document metadata
        base_metadata.update({
            "document_id": document_metadata.get("document_id", "unknown"),
            "document_title": document_metadata.get("document_title", ""),
            "client_name": document_metadata.get("client_name", ""),
            "vendor_name": document_metadata.get("vendor_name", ""),
            "project_site": document_metadata.get("project_site", ""),
            "submission_date": document_metadata.get("submission_date", ""),
            "project_value": document_metadata.get("project_value", 0.0)
        })
        
        # Generate LLM-based classifications
        llm_metadata = self._generate_llm_classifications(chunk_content, section_info)
        base_metadata.update(llm_metadata)
        
        # Determine content type
        base_metadata["content_type"] = self._determine_content_type(
            chunk_content, 
            section_info.get("has_tables", False),
            section_info.get("has_images", False)
        )
        
        # Add multimodal flags
        base_metadata.update({
            "has_table_content": section_info.get("has_tables", False),
            "has_image_content": section_info.get("has_images", False),
            "table_count": len(section_info.get("tables", [])),
            "image_count": len(section_info.get("images", []))
        })
        
        return base_metadata
    
    def _generate_chunk_id(self, document_metadata: Dict, section_info: Dict, chunk_index: int) -> str:
        """Generate unique, Azure Search compatible chunk ID"""
        
        document_id = document_metadata.get("document_id", "unknown")
        section_title = section_info.get("title", "unknown_section")
        
        # Clean and normalize section title for ID
        clean_section = re.sub(r'[^\w\s-]', '', section_title)
        clean_section = re.sub(r'\s+', '_', clean_section).lower()
        clean_section = clean_section[:30]  # Limit length
        
        # Clean document ID
        clean_doc_id = re.sub(r'[^\w-]', '_', document_id)
        
        # Create chunk ID
        chunk_id = f"{clean_doc_id}_section_{clean_section}_chunk_{chunk_index:02d}"
        
        # Ensure Azure Search compatibility
        chunk_id = re.sub(r'[^a-zA-Z0-9_\-=]', '_', chunk_id)
        
        # Limit total length
        if len(chunk_id) > 100:
            chunk_id = chunk_id[:100]
        
        return chunk_id
    
    def _generate_llm_classifications(self, chunk_content: str, section_info: Dict) -> Dict:
        """Generate domain and service classifications using LLM"""
        
        # Use content preview for efficiency
        content_preview = chunk_content[:800] if len(chunk_content) > 800 else chunk_content
        section_title = section_info.get("title", "")
        section_type = section_info.get("section_type", "general")
        
        try:
            system_message = """You are an expert at classifying RFP document content.
            Analyze the content and classify it into domain and service categories.
            
            Domain Categories:
            - engineering: Technical design, structural, electrical, mechanical work
            - environmental: Environmental impact, sustainability, compliance
            - financial: Pricing, budgets, costs, payments, financial analysis
            - legal: Legal terms, compliance, regulatory requirements
            - technical: Technical specifications, standards, requirements
            - administrative: Project management, coordination, documentation
            - general: Content that doesn't fit other categories
            
            Service Categories:
            - design: Design services, planning, conceptual work
            - construction_support: Construction assistance, supervision, field services
            - consulting: Advisory services, expertise, recommendations
            - maintenance: Ongoing support, maintenance, operations
            - analysis: Studies, assessments, evaluations, research
            - general: Services that don't fit other categories
            
            Return JSON format:
            {
                "domain_category": "category_name",
                "service_category": "category_name",
                "confidence": "high/medium/low"
            }"""
            
            user_prompt = f"""Section Title: {section_title}
Section Type: {section_type}

Content: {content_preview}

Classify this content's domain and service categories."""
            
            response = self.llm_client.get_structured_completion(user_prompt, system_message)
            
            if "error" not in response:
                return {
                    "domain_category": response.get("domain_category", "general"),
                    "service_category": response.get("service_category", "general"),
                    "classification_confidence": response.get("confidence", "medium")
                }
        
        except Exception as e:
            print(f"⚠️ Error in LLM classification: {e}")
        
        # Fallback to rule-based classification
        return self._fallback_classification(chunk_content, section_info)
    
    def _fallback_classification(self, chunk_content: str, section_info: Dict) -> Dict:
        """Fallback rule-based classification"""
        
        content_lower = chunk_content.lower()
        title_lower = section_info.get("title", "").lower()
        section_type = section_info.get("section_type", "general")
        
        # Domain classification rules
        domain_category = "general"
        if any(word in content_lower or word in title_lower for word in ["civil", "structural", "electrical", "mechanical", "engineering", "design", "technical"]):
            domain_category = "engineering"
        elif any(word in content_lower or word in title_lower for word in ["environmental", "sustainability", "impact", "compliance"]):
            domain_category = "environmental"
        elif any(word in content_lower or word in title_lower for word in ["cost", "price", "budget", "$", "financial", "payment"]):
            domain_category = "financial"
        elif any(word in content_lower or word in title_lower for word in ["legal", "contract", "terms", "conditions"]):
            domain_category = "legal"
        elif section_type in ["technical_requirements", "scope_of_work"]:
            domain_category = "technical"
        
        # Service classification rules
        service_category = "general"
        if any(word in content_lower or word in title_lower for word in ["design", "planning", "concept", "development"]):
            service_category = "design"
        elif any(word in content_lower or word in title_lower for word in ["construction", "installation", "implementation", "field"]):
            service_category = "construction_support"
        elif any(word in content_lower or word in title_lower for word in ["consulting", "advisory", "guidance", "recommendation"]):
            service_category = "consulting"
        elif any(word in content_lower or word in title_lower for word in ["maintenance", "support", "operation", "ongoing"]):
            service_category = "maintenance"
        elif any(word in content_lower or word in title_lower for word in ["analysis", "study", "assessment", "evaluation"]):
            service_category = "analysis"
        
        return {
            "domain_category": domain_category,
            "service_category": service_category,
            "classification_confidence": "low"
        }
    
    def _extract_section_hierarchy(self, section_title: str) -> str:
        """Extract section hierarchy number from title"""
        
        # Look for patterns like 1.0, 2.1, 3.1.2, etc.
        hierarchy_patterns = [
            r'^(\d+\.\d+\.\d+)',  # 1.1.1
            r'^(\d+\.\d+)',       # 1.1
            r'^(\d+\.)',          # 1.
            r'^(\d+)'             # 1
        ]
        
        for pattern in hierarchy_patterns:
            match = re.search(pattern, section_title.strip())
            if match:
                return match.group(1)
        
        return "0"  # Default if no hierarchy found
    
    def _estimate_chunk_page(self, section_info: Dict, chunk_index: int, total_chunks: int) -> int:
        """Estimate page number for chunk within section"""
        
        # Get section page range
        section_start_char = section_info.get("start_char", 0)
        section_end_char = section_info.get("end_char", 1000)
        
        # Rough estimation: ~3000 characters per page
        chars_per_page = 3000
        section_start_page = max(1, (section_start_char // chars_per_page) + 1)
        section_end_page = max(section_start_page, (section_end_char // chars_per_page) + 1)
        
        # Estimate chunk position within section
        if total_chunks <= 1:
            return section_start_page
        
        page_range = section_end_page - section_start_page + 1
        chunk_position = (chunk_index - 1) / (total_chunks - 1)  # 0 to 1
        estimated_page = section_start_page + int(chunk_position * max(0, page_range - 1))
        
        return max(section_start_page, estimated_page)
    
    def _determine_content_type(self, content: str, has_tables: bool, has_images: bool) -> str:
        """Determine content type based on multimodal content"""
        
        if has_tables and has_images:
            return "text_with_multimodal"
        elif has_tables:
            return "text_with_table"
        elif has_images:
            return "text_with_image"
        else:
            return "text"
    
    def extract_rfp_specific_metadata(self, content: str, document_metadata: Dict) -> Dict:
        """Extract RFP-specific metadata from content"""
        
        rfp_metadata = {}
        content_lower = content.lower()
        
        # Extract project details
        rfp_metadata.update({
            "mentions_timeline": any(word in content_lower for word in ["schedule", "timeline", "duration", "completion", "deadline"]),
            "mentions_budget": any(word in content_lower for word in ["$", "cost", "budget", "price", "fee", "amount"]),
            "mentions_deliverables": any(word in content_lower for word in ["deliverable", "provide", "deliver", "submit"]),
            "mentions_requirements": any(word in content_lower for word in ["requirement", "must", "shall", "specification"]),
            "mentions_qualifications": any(word in content_lower for word in ["experience", "qualification", "certified", "licensed"])
        })
        
        # Extract numerical information
        rfp_metadata.update(self._extract_numerical_metadata(content))
        
        # Extract key entities
        rfp_metadata.update(self._extract_key_entities(content))
        
        return rfp_metadata
    
    def _extract_numerical_metadata(self, content: str) -> Dict:
        """Extract numerical information from content"""
        
        numerical_metadata = {
            "contains_monetary_values": False,
            "contains_quantities": False,
            "contains_percentages": False,
            "contains_dates": False
        }
        
        # Check for monetary values
        if re.search(r'\$[\d,]+', content):
            numerical_metadata["contains_monetary_values"] = True
        
        # Check for quantities
        if re.search(r'\b\d+\s*(units?|pieces?|items?|quantities?)\b', content, re.IGNORECASE):
            numerical_metadata["contains_quantities"] = True
        
        # Check for percentages
        if re.search(r'\d+\s*%', content):
            numerical_metadata["contains_percentages"] = True
        
        # Check for dates
        if re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', content):
            numerical_metadata["contains_dates"] = True
        
        return numerical_metadata
    
    def _extract_key_entities(self, content: str) -> Dict:
        """Extract key entities and terms from content"""
        
        entities = {
            "key_terms": [],
            "technical_terms": [],
            "location_references": []
        }
        
        # Extract technical terms (simplified approach)
        technical_patterns = [
            r'\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b',  # Acronyms
            r'\b\d+(?:\.\d+)*[A-Z]+\b',  # Technical specifications like 230kV
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+\([^)]+\))?\b'  # Proper nouns with optional parentheses
        ]
        
        for pattern in technical_patterns[:1]:  # Limit to avoid over-extraction
            matches = re.findall(pattern, content)
            entities["technical_terms"].extend(matches[:5])  # Limit number
        
        # Extract location references (simple patterns)
        location_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\b',  # City, State
            r'\b[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr)\b'  # Street addresses
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            entities["location_references"].extend(matches[:3])  # Limit number
        
        return entities
    
    def validate_metadata(self, metadata: Dict) -> Dict:
        """Validate and clean metadata"""
        
        # Required fields
        required_fields = [
            "chunk_id", "content", "section_type", "section_title", 
            "domain_category", "service_category", "content_type"
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in metadata:
                metadata[field] = "unknown"
        
        # Validate classifications
        valid_domains = self.classification_config["domain_categories"]
        if metadata.get("domain_category") not in valid_domains:
            metadata["domain_category"] = "general"
        
        valid_services = self.classification_config["service_categories"]
        if metadata.get("service_category") not in valid_services:
            metadata["service_category"] = "general"
        
        valid_content_types = self.classification_config["content_types"]
        if metadata.get("content_type") not in valid_content_types:
            metadata["content_type"] = "text"
        
        # Ensure numeric fields
        metadata["token_count"] = max(0, metadata.get("token_count", 0))
        metadata["char_count"] = max(0, metadata.get("char_count", 0))
        metadata["chunk_number"] = max(1, metadata.get("chunk_number", 1))
        metadata["total_chunks_in_section"] = max(1, metadata.get("total_chunks_in_section", 1))
        metadata["page_number"] = max(1, metadata.get("page_number", 1))
        
        return metadata
    
    def create_metadata_summary(self, all_chunks_metadata: List[Dict]) -> Dict:
        """Create summary of metadata across all chunks"""
        
        if not all_chunks_metadata:
            return {}
        
        summary = {
            "total_chunks": len(all_chunks_metadata),
            "distribution": {
                "by_section_type": {},
                "by_domain_category": {},
                "by_service_category": {},
                "by_content_type": {}
            },
            "statistics": {
                "avg_chunk_size_tokens": 0,
                "avg_chunk_size_chars": 0,
                "total_tokens": 0,
                "total_chars": 0,
                "chunks_with_tables": 0,
                "chunks_with_images": 0,
                "chunks_with_multimodal": 0
            }
        }
        
        # Calculate distributions
        for chunk in all_chunks_metadata:
            # Section type distribution
            section_type = chunk.get("section_type", "unknown")
            summary["distribution"]["by_section_type"][section_type] = \
                summary["distribution"]["by_section_type"].get(section_type, 0) + 1
            
            # Domain category distribution
            domain = chunk.get("domain_category", "unknown")
            summary["distribution"]["by_domain_category"][domain] = \
                summary["distribution"]["by_domain_category"].get(domain, 0) + 1
            
            # Service category distribution
            service = chunk.get("service_category", "unknown")
            summary["distribution"]["by_service_category"][service] = \
                summary["distribution"]["by_service_category"].get(service, 0) + 1
            
            # Content type distribution
            content_type = chunk.get("content_type", "unknown")
            summary["distribution"]["by_content_type"][content_type] = \
                summary["distribution"]["by_content_type"].get(content_type, 0) + 1
            
            # Statistics
            summary["statistics"]["total_tokens"] += chunk.get("token_count", 0)
            summary["statistics"]["total_chars"] += chunk.get("char_count", 0)
            
            if chunk.get("has_table_content", False):
                summary["statistics"]["chunks_with_tables"] += 1
            
            if chunk.get("has_image_content", False):
                summary["statistics"]["chunks_with_images"] += 1
            
            if chunk.get("has_table_content", False) and chunk.get("has_image_content", False):
                summary["statistics"]["chunks_with_multimodal"] += 1
        
        # Calculate averages
        if len(all_chunks_metadata) > 0:
            summary["statistics"]["avg_chunk_size_tokens"] = \
                summary["statistics"]["total_tokens"] / len(all_chunks_metadata)
            summary["statistics"]["avg_chunk_size_chars"] = \
                summary["statistics"]["total_chars"] / len(all_chunks_metadata)
        
        return summary