import json
import re
from typing import Dict, List
from .prompts import DocumentMetadataPrompts
from processors.content_verbalizer import ContentVerbalizer

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)
 
class RFPExtractor:
    """Extract RFP metadata (11 fields) from documents using Azure OpenAI - Reuses existing client"""
   
    @tracer.start_as_current_span("RFPExtractor_init_fn")
    def __init__(self):
        """Initialize RFP extractor with existing Azure OpenAI client"""
        self.verbalizer = ContentVerbalizer()  # Reuse existing client - no duplicate initialization
        self.rfp_fields = [
            'project_title', 'client_name', 'vendor_name', 'submission_date',
            'domain_category', 'service_category', 'revenue_range', 'region',
            'project_value', 'equipments_used', 'compliance_standard'
        ]
       
        # Print initialization info without duplicate client setup
        # print("✅ RFP Extractor initialized - reusing existing Azure OpenAI client")
        # print(f"   📊 Fields: {len(self.rfp_fields)} RFP metadata fields")
        # print(f"   🔄 Client reuse: ✅ No duplicate initialization")


    @tracer.start_as_current_span("extract_metadata_fn")
    async def extract_metadata(self, text_elements: List[Dict]) -> Dict:
        """
        Extract RFP metadata (11 fields) from complete document text elements
       
        Args:
            text_elements: List of text elements from document (complete document, not just first 2 pages)
           
        Returns:
            Dict: Extracted metadata with 11 required fields for RFP
        """
        try:
            #print("🔍 Extracting RFP metadata from COMPLETE document using LLM")
            log_custom_event(
                 logger,
                 "Extracting RFP metadata from COMPLETE document using LLM",
                 level="info",
                )
           
            # Convert text elements to complete document text
            complete_document_text = self._prepare_complete_document_text(text_elements)
           
            if not complete_document_text.strip():
                #print("⚠️ No text found in document, using RFP defaults")
                return self._get_rfp_default_metadata()
           
            # print(f"📊 Complete document text prepared:")
            # print(f"   📄 Pages processed: {self._count_pages(text_elements)}")
            # print(f"   📝 Text length: {len(complete_document_text)} characters")
            # print(f"   🎯 Ready for comprehensive metadata extraction")
           
            # Generate metadata using Azure OpenAI (reusing existing client)
            if self.verbalizer.client:
                # metadata = self._extract_metadata_with_azure_openai(complete_document_text)
                metadata = await self._extract_metadata_with_azure_openai(complete_document_text)
            else:
                #print("❌ Azure OpenAI client not available")
                return self._get_rfp_default_metadata()
           
            # Validate and clean metadata for RFP (11 fields)
            validated_metadata = self._validate_rfp_metadata(metadata)
           
            #print("✅ RFP metadata extraction completed from complete document")
            return validated_metadata
           
        except Exception as e:
            #print(f"❌ Error extracting RFP metadata: {e}")
            return self._get_rfp_default_metadata()
   
    def _prepare_complete_document_text(self, text_elements: List[Dict]) -> str:
        """Convert text elements to complete document text (not just first 2 pages)"""
        complete_text = ""
       
        # Process ALL text elements from the complete document
        for element in text_elements:
            content = element.get('content', '').strip()
            role = element.get('role', 'unknown')
           
            # Add role context for better understanding
            if content:
                complete_text += f"[{role}] {content}\n\n"
       
        #print(f"🔍 Processing {len(text_elements)} text elements from complete document...")
        return complete_text
   
    def _count_pages(self, text_elements: List[Dict]) -> str:
        """Count total pages in document"""
        pages = set()
        for element in text_elements:
            page_num = element.get('page_number', 1)
            pages.add(page_num)
       
        total_pages = max(pages) if pages else 1
        return f"{total_pages}/{total_pages}"
   
    # def _extract_metadata_with_azure_openai(self, complete_document_text: str) -> Dict:
    async def _extract_metadata_with_azure_openai(self, complete_document_text: str) -> Dict:
        """Extract RFP metadata using Azure OpenAI API (reusing existing client)"""
        try:
            # print(f"📄 Sending {len(complete_document_text)} characters to LLM for RFP analysis")
            # print("🤖 Calling LLM for comprehensive metadata extraction...")
           
            # Get the RFP-specific prompt (11 fields)
            prompt = DocumentMetadataPrompts.get_rfp_extraction_prompt(complete_document_text)
           
            # response = self.verbalizer.client.chat.completions.create(
            response = await self.verbalizer.client.chat.completions.create(
                model="gpt-4o",  # Use same model as ContentVerbalizer
                messages=[
                    {"role": "system", "content": "You are an expert Power Business Unit RFP analyst. Extract metadata and match domains/services to the exact Power Business Unit lists provided. Return only valid JSON with the 11 required fields for RFP documents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,  # Increased for RFP (11 fields)
                temperature=0.1  # Low temperature for consistent extraction
            )
           
            response_text = response.choices[0].message.content.strip()
            #print(f"📝 LLM response: {len(response_text)} characters")
           
            # Clean and parse JSON response
            metadata = self._parse_json_response(response_text)
            #print("✅ Successfully parsed metadata from LLM")
            return metadata
               
        except Exception as e:
            #print(f"❌ Azure OpenAI API error: {e}")
            return self._get_rfp_default_metadata()
   
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
            # print(f"❌ JSON parsing failed: {e}")
            # print(f"Raw response: {response_text[:200]}...")
            return self._get_rfp_default_metadata()
   
    def _validate_rfp_metadata(self, metadata: Dict) -> Dict:
        """Validate and clean RFP metadata (11 fields)"""
        validated = {}
       
        for field in self.rfp_fields:
            value = metadata.get(field, 'Not Specified')
           
            # Clean and validate the value
            if isinstance(value, str):
                value = value.strip()
                value = re.sub(r'^["\']+|["\']+$', '', value)  # Remove quotes
                if not value or value.lower() in ['none', 'null', 'undefined', '', 'n/a']:
                    if field in ['domain_category', 'service_category', 'revenue_range', 'region', 'project_value', 'equipments_used', 'compliance_standard']:
                        value = 'Not mentioned in RFP'
                    else:
                        value = 'Not Specified'
                elif len(value) > 500:
                    value = value[:500] + '...'
            else:
                if field in ['domain_category', 'service_category', 'revenue_range', 'region', 'project_value', 'equipments_used', 'compliance_standard']:
                    value = 'Not mentioned in RFP'
                else:
                    value = 'Not Specified'
           
            validated[field] = value
       
        # Fallback vendor_name to tetratech if not found
        if validated['vendor_name'] == 'Not Specified':
            validated['vendor_name'] = 'tetratech'
       
        return validated
   
    def _get_rfp_default_metadata(self) -> Dict:
        """Get default RFP metadata structure (11 fields)"""
        return {
            'project_title': 'Not Specified',
            'client_name': 'Not Specified',
            'vendor_name': 'tetratech',
            'submission_date': 'Not Specified',
            'domain_category': 'Not mentioned in RFP',
            'service_category': 'Not mentioned in RFP',
            'revenue_range': 'Not mentioned in RFP',
            'region': 'Not mentioned in RFP',
            'project_value': 'Not mentioned in RFP',
            'equipments_used': 'Not mentioned in RFP',
            'compliance_standard': 'Not mentioned in RFP'
        }
   
    def get_status_info(self) -> Dict:
        """Get status information about the RFP metadata extractor"""
        return {
            "extractor_type": "RFP",
            "fields_count": len(self.rfp_fields),
            "fields": self.rfp_fields,
            "client_initialized": self.verbalizer.client is not None,
            "status": "ready" if self.verbalizer.client else "client_unavailable",
            "reuses_existing_client": True
        }
 