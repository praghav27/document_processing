"""
Document type detection utility to determine if document is RFP or RFI
Fixed version with proper null checks and error handling
"""

import re
from typing import Dict, List

class DocumentTypeDetector:
    """Detect document type (RFP vs RFI) based on content analysis"""
    
    def __init__(self):
        # RFP indicators
        self.rfp_keywords = [
            'request for proposal', 'rfp', 'proposal submission', 'vendor proposal',
            'bid submission', 'tender', 'proposal requirements', 'proposal evaluation',
            'proposal deadline', 'pricing proposal', 'commercial proposal', 'technical proposal',
            'proposal guidelines', 'submission requirements', 'proposal format',
            'vendor selection', 'bid evaluation', 'contract award', 'procurement',
            'total cost', 'project value', 'budget', 'pricing table', 'revenue range'
        ]
        
        # RFI indicators - ENHANCED
        self.rfi_keywords = [
            'request for information', 'rfi', 'information request', 'seeking information',
            'rfi number', 'rfi no', 'rfi ref', 'rfi reference',
            'information gathering', 'preliminary information', 'market research',
            'capability statement', 'company information', 'technical capabilities',
            'experience information', 'qualification information', 'pre-qualification',
            'vendor information', 'supplier information', 'industry information',
            'feasibility information', 'technical approach', 'methodology information',
            'provide information', 'submit information', 'company profile',
            'past experience', 'relevant experience', 'project experience',
            'technical expertise', 'capabilities', 'qualifications'
        ]
        
        # Neutral keywords that appear in both
        self.neutral_keywords = [
            'project', 'requirements', 'technical', 'services', 'company',
            'experience', 'qualification', 'client', 'submission', 'deadline'
        ]
    
    def detect_document_type(self, text_elements: List[Dict]) -> Dict:
        """
        Detect document type based on text elements with proper error handling
        
        Args:
            text_elements: List of text elements from document
            
        Returns:
            Dict: Detection results with confidence score
        """
        try:
            if not text_elements or len(text_elements) == 0:
                return self._get_default_detection("No text elements provided")
            
            # Safely combine all text content
            full_text = self._safely_combine_text(text_elements)
            if not full_text or len(full_text.strip()) == 0:
                return self._get_default_detection("No text content found")
            
            full_text_lower = self._safe_lower(full_text)
            
            # Count keyword occurrences
            rfp_score = self._count_keywords(full_text_lower, self.rfp_keywords)
            rfi_score = self._count_keywords(full_text_lower, self.rfi_keywords)
            
            # Title and header analysis (higher weight) - ENHANCED
            title_text = self._extract_title_content(text_elements)
            title_text_lower = self._safe_lower(title_text)
            
            # Special check for explicit RFI/RFP in title
            explicit_rfi_in_title = any(keyword in title_text_lower for keyword in ['request for information', 'rfi number', 'rfi no', 'rfi ref'])
            explicit_rfp_in_title = any(keyword in title_text_lower for keyword in ['request for proposal', 'rfp number', 'rfp no', 'rfp ref'])
            
            title_rfp_score = self._count_keywords(title_text_lower, self.rfp_keywords) * 3
            title_rfi_score = self._count_keywords(title_text_lower, self.rfi_keywords) * 3
            
            # Give extra weight for explicit mentions in title
            if explicit_rfi_in_title:
                title_rfi_score += 15  # Strong boost for RFI
            if explicit_rfp_in_title:
                title_rfp_score += 15  # Strong boost for RFP
            
            # Total scores
            total_rfp_score = rfp_score + title_rfp_score
            total_rfi_score = rfi_score + title_rfi_score
            
            # Document structure analysis
            structure_analysis = self._analyze_document_structure(text_elements)
            
            # Determine document type - FIXED LOGIC
            if total_rfi_score > total_rfp_score:
                document_type = "RFI"
                confidence = min(0.95, (total_rfi_score / (total_rfi_score + total_rfp_score + 1)) * 1.2)
            elif total_rfp_score > total_rfi_score:
                document_type = "RFP"
                confidence = min(0.95, (total_rfp_score / (total_rfp_score + total_rfi_score + 1)) * 1.2)
            else:
                # Default to RFP if unclear
                document_type = "RFP"
                confidence = 0.5
            
            # Adjust confidence based on structure - FIXED
            if structure_analysis['has_pricing_sections'] and document_type == "RFI":
                # If both pricing and info requests exist, prioritize the higher score
                if total_rfi_score > total_rfp_score * 1.5:  # RFI score significantly higher
                    # Keep as RFI despite pricing sections
                    pass
                else:
                    # Change to RFP if scores are close
                    document_type = "RFP"
                    confidence = max(0.7, confidence)
            elif structure_analysis['has_info_request_sections'] and document_type == "RFP":
                # If both info requests and pricing exist, prioritize the higher score  
                if total_rfp_score > total_rfi_score * 1.5:  # RFP score significantly higher
                    # Keep as RFP despite info request sections
                    pass
                else:
                    # Change to RFI if scores are close
                    document_type = "RFI"
                    confidence = max(0.7, confidence)
            
            return {
                'document_type': document_type,
                'confidence': round(confidence, 2),
                'rfp_score': total_rfp_score,
                'rfi_score': total_rfi_score,
                'analysis': {
                    'title_analysis': {
                        'title_text': title_text[:100] if title_text else '',
                        'rfp_indicators': title_rfp_score // 3,  # Adjust for weighting
                        'rfi_indicators': title_rfi_score // 3
                    },
                    'content_analysis': {
                        'rfp_indicators': rfp_score,
                        'rfi_indicators': rfi_score,
                        'total_text_length': len(full_text)
                    },
                    'structure_analysis': structure_analysis
                },
                'reasoning': self._generate_reasoning(document_type, total_rfp_score, total_rfi_score, structure_analysis)
            }
            
        except Exception as e:
            #print(f"❌ Error in document type detection: {e}")
            return self._get_default_detection(f"Error during detection: {str(e)}")
    
    def _safely_combine_text(self, text_elements: List[Dict]) -> str:
        """Safely combine text elements with null checks"""
        try:
            text_parts = []
            for elem in text_elements:
                if elem and isinstance(elem, dict):
                    content = elem.get('content')
                    if content and isinstance(content, str) and content.strip():
                        text_parts.append(content.strip())
            return " ".join(text_parts)
        except Exception as e:
            #print(f"⚠️ Error combining text elements: {e}")
            return ""
    
    def _safe_lower(self, text: str) -> str:
        """Safely convert text to lowercase with null checks"""
        try:
            if text and isinstance(text, str):
                return text.lower()
            return ""
        except Exception as e:
            #print(f"⚠️ Error converting text to lowercase: {e}")
            return ""
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count keyword occurrences in text with null checks"""
        try:
            if not text or not isinstance(text, str) or not keywords:
                return 0
            
            count = 0
            for keyword in keywords:
                if keyword and isinstance(keyword, str):
                    # Use word boundaries to avoid partial matches
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    try:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        count += len(matches)
                    except Exception as e:
                        #print(f"⚠️ Error matching keyword '{keyword}': {e}")
                        continue
            return count
        except Exception as e:
            #print(f"⚠️ Error counting keywords: {e}")
            return 0
    
    def _extract_title_content(self, text_elements: List[Dict]) -> str:
        """Extract title and header content for focused analysis with null checks"""
        try:
            title_content = []
            
            if not text_elements:
                return ""
            
            for elem in text_elements:
                if not elem or not isinstance(elem, dict):
                    continue
                
                role = elem.get('role', '')
                content = elem.get('content', '')
                
                # Safe role and content checks
                if not isinstance(role, str):
                    role = ''
                if not isinstance(content, str):
                    content = ''
                
                role_lower = self._safe_lower(role)
                
                # Focus on titles, headings, and first few elements
                if any(title_role in role_lower for title_role in ['title', 'heading', 'section']):
                    if content.strip():
                        title_content.append(content.strip())
                elif elem.get('paragraph_index', 0) <= 3:  # First few paragraphs
                    if content.strip():
                        title_content.append(content.strip())
            
            return " ".join(title_content)
            
        except Exception as e:
            #(f"⚠️ Error extracting title content: {e}")
            return ""
    
    def _analyze_document_structure(self, text_elements: List[Dict]) -> Dict:
        """Analyze document structure for additional clues with null checks"""
        structure = {
            'has_pricing_sections': False,
            'has_info_request_sections': False,
            'has_technical_specs': False,
            'has_submission_requirements': False,
            'section_count': 0,
            'total_elements': len(text_elements) if text_elements else 0
        }
        
        try:
            if not text_elements:
                return structure
            
            # Pricing/cost indicators (suggest RFP)
            pricing_patterns = [
                r'pricing\s+table', r'cost\s+breakdown', r'budget', r'total\s+cost',
                r'project\s+value', r'contract\s+amount', r'financial\s+proposal',
                r'revenue', r'bid\s+price', r'quotation'
            ]
            
            # Information request indicators (suggest RFI)
            info_patterns = [
                r'provide\s+information', r'describe\s+your', r'company\s+background',
                r'relevant\s+experience', r'capability\s+statement', r'past\s+projects',
                r'technical\s+approach', r'methodology', r'qualifications'
            ]
            
            full_text = self._safely_combine_text(text_elements)
            full_text_lower = self._safe_lower(full_text)
            
            # Check for pricing sections
            for pattern in pricing_patterns:
                try:
                    if re.search(pattern, full_text_lower):
                        structure['has_pricing_sections'] = True
                        break
                except Exception as e:
                    #print(f"⚠️ Error checking pricing pattern '{pattern}': {e}")
                    continue
            
            # Check for information request sections
            for pattern in info_patterns:
                try:
                    if re.search(pattern, full_text_lower):
                        structure['has_info_request_sections'] = True
                        break
                except Exception as e:
                    #print(f"⚠️ Error checking info pattern '{pattern}': {e}")
                    continue
            
            # Count sections safely
            section_roles = ['sectionheading', 'title', 'subtitle']
            section_count = 0
            for elem in text_elements:
                if elem and isinstance(elem, dict):
                    role = elem.get('role', '')
                    if isinstance(role, str):
                        role_lower = self._safe_lower(role)
                        if role_lower in section_roles:
                            section_count += 1
            
            structure['section_count'] = section_count
            
        except Exception as e:
            #print(f"⚠️ Error analyzing document structure: {e}")
            print()
        
        return structure
    
    def _generate_reasoning(self, document_type: str, rfp_score: int, rfi_score: int, structure: Dict) -> str:
        """Generate reasoning for the detection with null checks"""
        try:
            reasoning_parts = []
            
            # Score-based reasoning
            if rfp_score > rfi_score:
                reasoning_parts.append(f"RFP indicators ({rfp_score}) outweigh RFI indicators ({rfi_score})")
            elif rfi_score > rfp_score:
                reasoning_parts.append(f"RFI indicators ({rfi_score}) outweigh RFP indicators ({rfp_score})")
            else:
                reasoning_parts.append(f"Equal indicators ({rfp_score} vs {rfi_score}), defaulting to RFP")
            
            # Structure-based reasoning
            if structure and isinstance(structure, dict):
                if structure.get('has_pricing_sections'):
                    reasoning_parts.append("Document contains pricing/cost sections typical of RFPs")
                
                if structure.get('has_info_request_sections'):
                    reasoning_parts.append("Document contains information request sections typical of RFIs")
                
                # Section analysis
                section_count = structure.get('section_count', 0)
                total_elements = structure.get('total_elements', 0)
                reasoning_parts.append(f"Document has {section_count} sections with {total_elements} total elements")
            
            return "; ".join(reasoning_parts)
            
        except Exception as e:
            #print(f"⚠️ Error generating reasoning: {e}")
            return f"Document detected as {document_type} with basic analysis"
    
    def _get_default_detection(self, reason: str = "No analysis possible") -> Dict:
        """Get default detection when analysis fails"""
        return {
            'document_type': 'RFP',  # Default to RFP
            'confidence': 0.5,
            'rfp_score': 0,
            'rfi_score': 0,
            'analysis': {
                'title_analysis': {'title_text': '', 'rfp_indicators': 0, 'rfi_indicators': 0},
                'content_analysis': {'rfp_indicators': 0, 'rfi_indicators': 0, 'total_text_length': 0},
                'structure_analysis': {
                    'has_pricing_sections': False,
                    'has_info_request_sections': False,
                    'has_technical_specs': False,
                    'has_submission_requirements': False,
                    'section_count': 0,
                    'total_elements': 0
                }
            },
            'reasoning': reason
        }
    
    def print_detection_summary(self, detection_result: Dict):
        """Print detection summary with null checks"""
        try:
            if not detection_result or not isinstance(detection_result, dict):
                #print("❌ No detection result to display")
                return
            
            # print(f"\n📄 DOCUMENT TYPE DETECTION")
            # print(f"{'='*50}")
            # print(f"🎯 Detected Type: {detection_result.get('document_type', 'Unknown')}")
            # print(f"📊 Confidence: {detection_result.get('confidence', 0):.1%}")
            # print(f"🔍 RFP Score: {detection_result.get('rfp_score', 0)}")
            # print(f"🔍 RFI Score: {detection_result.get('rfi_score', 0)}")
            # print(f"💭 Reasoning: {detection_result.get('reasoning', 'No reasoning available')}")
            
            analysis = detection_result.get('analysis', {})
            if analysis and isinstance(analysis, dict):
                title_analysis = analysis.get('title_analysis', {})
                if title_analysis and title_analysis.get('title_text'):
                    #print(f"📋 Title Content: {title_analysis['title_text']}")
                    print()
                
                structure = analysis.get('structure_analysis', {})
                if structure and isinstance(structure, dict):
                    section_count = structure.get('section_count', 0)
                    total_elements = structure.get('total_elements', 0)
                    #print(f"📄 Structure: {section_count} sections, {total_elements} elements")
                    
                    if structure.get('has_pricing_sections'):
                        #print("💰 Contains pricing/cost sections")
                        print()
                    if structure.get('has_info_request_sections'):
                        #print("ℹ️ Contains information request sections")
                        print()
        
        except Exception as e:
            # print(f"❌ Error printing detection summary: {e}")
            # print(f"🎯 Detected Type: {detection_result.get('document_type', 'Unknown') if detection_result else 'Error'}")
            print()