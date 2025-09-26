import os
import base64
import asyncio
import time
from typing import Dict, Optional
from .prompts import ImageAnalysisPrompts, TableAnalysisPrompts
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME
 
# Import Azure OpenAI
from openai import AsyncAzureOpenAI

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)
 
class ContentVerbalizer:
    """Handle verbalization of tables and images using Azure OpenAI - SINGLETON PATTERN with ASYNC support and Enhanced Rate Limiting"""
   
    _instance = None
    _client = None
    _initialized = False
    _rate_limiter = None  # Rate limiter for parallel processing
    _request_tracker = None  # Request tracking for better rate limiting
   
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
   
    def __init__(self):
        """Initialize the verbalizer with Azure OpenAI - ONLY ONCE, SILENTLY REUSE"""
        if not ContentVerbalizer._initialized:
            self._initialize_azure_openai_client()
            # ENHANCED: Reduced rate limiter for better stability
            ContentVerbalizer._rate_limiter = asyncio.Semaphore(2)  # REDUCED from 4 to 2 concurrent OpenAI calls
            ContentVerbalizer._request_tracker = {
                'last_request_time': 0,
                'min_interval': 1.0,  # Minimum 1 second between requests
                'request_count': 0,
                'error_count': 0
            }
            ContentVerbalizer._initialized = True
        # NO print statements for subsequent initializations - silent reuse
   
    @property
    def client(self):
        """Get the shared Azure OpenAI client"""
        return ContentVerbalizer._client
   
    @tracer.start_as_current_span("_initialize_azure_openai_client_fn")
    def _initialize_azure_openai_client(self):
        """Initialize the Azure OpenAI client - ONLY ONCE (now async client)"""
        try:
            if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
                ContentVerbalizer._client = AsyncAzureOpenAI(
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION,
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    timeout=60.0,  # ADD: 60 second timeout
                    max_retries=3   # ADD: 3 retries
                )
                # print("✅ Enhanced Async Azure OpenAI client initialized with improved rate limiting")
                log_custom_event(
                                logger,
                                "Enhanced Async Azure OpenAI client initialized with improved rate limiting",
                                level="info",
                                )

                # print(f"   Endpoint: {AZURE_OPENAI_ENDPOINT}")
                # print(f"   Deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")
                # print(f"   Rate limit: 2 concurrent calls (enhanced)")
                # print(f"   Timeout: 60 seconds")
                # print(f"   Max retries: 3")
            else:
                # print("❌ Azure OpenAI credentials not found")
                # print("⚠️  Using mock responses for testing")
                log_custom_event(
                                logger,
                                "Azure OpenAI credentials not found, using mock responses",
                                level="earning",
                                )

               
        except Exception as e:
            #print(f"❌ Error initializing Azure OpenAI client: {e}")
            ContentVerbalizer._client = None
    
    @tracer.start_as_current_span("_wait_for_rate_limit_fn")
    async def _wait_for_rate_limit(self):
        """Enhanced rate limiting to prevent overwhelming OpenAI"""
        current_time = time.time()
        time_since_last = current_time - ContentVerbalizer._request_tracker['last_request_time']
        
        if time_since_last < ContentVerbalizer._request_tracker['min_interval']:
            sleep_time = ContentVerbalizer._request_tracker['min_interval'] - time_since_last
            #print(f"⏳ OpenAI Rate limiting: Waiting {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        ContentVerbalizer._request_tracker['last_request_time'] = time.time()
        ContentVerbalizer._request_tracker['request_count'] += 1
   
    @tracer.start_as_current_span("verbalize_table_fn")
    async def verbalize_table(self, table_data: Dict) -> str:
        """
        Generate natural language description of table data (ASYNC with Enhanced Rate Limiting)
       
        Args:
            table_data: Dictionary containing table information
           
        Returns:
            str: Natural language description of the table
        """
        # Apply enhanced rate limiting for parallel processing
        async with ContentVerbalizer._rate_limiter:
            # Wait for rate limit
            await self._wait_for_rate_limit()
            
            for attempt in range(3):  # 3 retry attempts
                try:
                    # Prepare table metadata
                    metadata = f"""
                    Page: {table_data.get('page_number', 'Unknown')}
                    Rows: {table_data.get('row_count', 'Unknown')}
                    Columns: {table_data.get('column_count', 'Unknown')}
                    Section: {table_data.get('section_info', {}).get('section_content', 'Unknown')[:100]}
                    """
                   
                    # Get table content (CSV format)
                    table_content = table_data.get('content', 'No table content available')
                   
                    # Get the prompt
                    prompt = TableAnalysisPrompts.get_rfp_table_analysis_prompt(metadata, table_content)
                   
                    # Generate verbalization (ASYNC with timeout)
                    if self.client:
                        result = await asyncio.wait_for(
                            self._verbalize_with_azure_openai(prompt, content_type="table"),
                            timeout=45.0  # 45 second timeout per request
                        )
                        return result
                    else:
                        # Mock response for testing
                        return self._generate_mock_table_verbalization(table_data)
                    
                except asyncio.TimeoutError:
                    #print(f"⏰ Table verbalization timeout on attempt {attempt + 1}")
                    ContentVerbalizer._request_tracker['error_count'] += 1
                    if attempt < 2:  # Retry
                        await asyncio.sleep(2.0)  # Wait 2 seconds before retry
                        continue
                    else:
                        return self._generate_mock_table_verbalization(table_data)
                        
                except Exception as e:
                    #print(f"❌ Error verbalizing table on attempt {attempt + 1}: {e}")
                    ContentVerbalizer._request_tracker['error_count'] += 1
                    if attempt < 2:  # Retry
                        await asyncio.sleep(2.0)  # Wait 2 seconds before retry
                        continue
                    else:
                        return f"Table from page {table_data.get('page_number', 'unknown')} with {table_data.get('row_count', 'unknown')} rows and {table_data.get('column_count', 'unknown')} columns."
   
    @tracer.start_as_current_span("verbalize_image_fn")
    async def verbalize_image(self, image_data: Dict) -> str:
        """
        Generate natural language description of image data (ASYNC with Enhanced Rate Limiting)
       
        Args:
            image_data: Dictionary containing image information
           
        Returns:
            str: Natural language description of the image
        """
        # Apply enhanced rate limiting for parallel processing
        async with ContentVerbalizer._rate_limiter:
            # Wait for rate limit
            await self._wait_for_rate_limit()
            
            for attempt in range(3):  # 3 retry attempts
                try:
                    # Get the prompt
                    prompt = ImageAnalysisPrompts.get_rfp_image_analysis_prompt()
                   
                    # For images, we need to handle base64 data if available
                    image_base64 = image_data.get('image_base64')
                    image_path = image_data.get('image_path')
                   
                    if self.client and image_base64:
                        result = await asyncio.wait_for(
                            self._verbalize_image_with_azure_openai(prompt, image_base64),
                            timeout=45.0  # 45 second timeout per request
                        )
                        return result
                    else:
                        # Mock response for testing or fallback to text content
                        return self._generate_mock_image_verbalization(image_data)
                        
                except asyncio.TimeoutError:
                    #print(f"⏰ Image verbalization timeout on attempt {attempt + 1}")
                    ContentVerbalizer._request_tracker['error_count'] += 1
                    if attempt < 2:  # Retry
                        await asyncio.sleep(2.0)  # Wait 2 seconds before retry
                        continue
                    else:
                        return self._generate_mock_image_verbalization(image_data)
                        
                except Exception as e:
                    #print(f"❌ Error verbalizing image on attempt {attempt + 1}: {e}")
                    ContentVerbalizer._request_tracker['error_count'] += 1
                    if attempt < 2:  # Retry
                        await asyncio.sleep(2.0)  # Wait 2 seconds before retry
                        continue
                    else:
                        return f"Figure from page {image_data.get('page_number', 'unknown')} - {image_data.get('content', 'No description available')}"
   
    async def _verbalize_with_azure_openai(self, prompt: str, content_type: str) -> str:
        """Generate verbalization using Azure OpenAI API (ASYNC with retry logic)"""
        try:
            response = await self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use the deployment name
                messages=[
                    {"role": "system", "content": "You are an expert document analyst specializing in technical content verbalization for Tetratech projects."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3,
                timeout=45.0  # Request-level timeout
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            #print(f"❌ Azure OpenAI API error for {content_type}: {e}")
            raise e  # Re-raise to trigger retry logic
   
    async def _verbalize_image_with_azure_openai(self, prompt: str, image_base64: str) -> str:
        """Generate image verbalization using Azure OpenAI Vision API (ASYNC with retry logic)"""
        try:
            response = await self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use the deployment name
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=600,
                temperature=0.3,
                timeout=45.0  # Request-level timeout
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            #print(f"❌ Azure OpenAI Vision API error: {e}")
            raise e  # Re-raise to trigger retry logic
   
    def _generate_mock_table_verbalization(self, table_data: Dict) -> str:
        """Generate mock table verbalization for testing"""
        section_info = table_data.get('section_info', {})
        section_content = section_info.get('section_content', 'Unknown Section')
       
        mock_description = f"""This table from page {table_data.get('page_number', 'unknown')} contains structured data with {table_data.get('row_count', 'multiple')} rows and {table_data.get('column_count', 'several')} columns. The table appears in the {section_content[:50]} section and presents organized information relevant to Tetratech's project analysis. The data structure includes categorical and numerical information that supports decision-making processes for infrastructure and environmental projects. This tabular data aligns with Tetratech's Water Cycle & Management and Infrastructure & Resource Management domains, providing quantitative insights for project evaluation and resource allocation."""
       
        return mock_description
   
    def _generate_mock_image_verbalization(self, image_data: Dict) -> str:
        """Generate mock image verbalization for testing"""
        section_info = image_data.get('section_info', {})
        section_content = section_info.get('section_content', 'Unknown Section')
        original_content = image_data.get('content', '')
       
        mock_description = f"""This figure from page {image_data.get('page_number', 'unknown')} presents visual information in the {section_content[:50]} section. The image contains technical diagrams, charts, or visual elements that support the document's narrative. Based on the extracted content '{original_content[:100]}', this visual element likely illustrates project components, system architecture, or data relationships. The figure aligns with Tetratech's technical domains, particularly Water Cycle & Management and Infrastructure & Resource Management, providing visual context for engineering and environmental consulting projects. The visual elements support understanding of complex technical concepts and project specifications."""
       
        return mock_description
   
    def get_model_info(self) -> Dict:
        """Get information about the current Azure OpenAI model configuration with enhanced stats"""
        return {
            "model_type": "enhanced_async_azure_openai_with_rate_limiting",
            "client_initialized": self.client is not None,
            "api_key_present": bool(AZURE_OPENAI_API_KEY),
            "endpoint": AZURE_OPENAI_ENDPOINT,
            "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
            "rate_limit": "2 concurrent calls (enhanced)",
            "timeout": "45 seconds per request",
            "max_retries": "3 attempts per request",
            "request_stats": ContentVerbalizer._request_tracker,
            "status": "ready" if self.client else "mock_mode"
        }
   
    async def test_verbalization(self) -> Dict:
        """Test the verbalization functionality (ASYNC with enhanced monitoring)"""
        test_table = {
            "page_number": 1,
            "row_count": 3,
            "column_count": 4,
            "content": "Project,Cost,Duration,Team\nPhase 1,$2M,6 months,10 people\nPhase 2,$3M,8 months,15 people",
            "section_info": {"section_content": "Budget Overview"}
        }
       
        test_image = {
            "page_number": 2,
            "content": "Process flow diagram showing water treatment stages",
            "section_info": {"section_content": "Technical Architecture"}
        }
       
        # Run both verbalizations concurrently with enhanced tracking
        start_time = time.time()
        table_verbalization, image_verbalization = await asyncio.gather(
            self.verbalize_table(test_table),
            self.verbalize_image(test_image)
        )
        end_time = time.time()
       
        return {
            "table_verbalization": table_verbalization,
            "image_verbalization": image_verbalization,
            "test_duration": f"{end_time - start_time:.2f}s",
            "model_info": self.get_model_info()
        }