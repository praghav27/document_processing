
# import os
# import base64
# from typing import Dict, Optional
# from .prompts import ImageAnalysisPrompts, TableAnalysisPrompts
# from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME

# # Import Azure OpenAI
# from openai import AzureOpenAI

# class ContentVerbalizer:
#     """Handle verbalization of tables and images using Azure OpenAI - SINGLETON PATTERN"""
    
#     _instance = None
#     _client = None
#     _initialized = False
    
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance
    
#     def __init__(self):
#         """Initialize the verbalizer with Azure OpenAI - ONLY ONCE, SILENTLY REUSE"""
#         if not ContentVerbalizer._initialized:
#             self._initialize_azure_openai_client()
#             ContentVerbalizer._initialized = True
#         # NO print statements for subsequent initializations - silent reuse
    
#     @property
#     def client(self):
#         """Get the shared Azure OpenAI client"""
#         return ContentVerbalizer._client
    
#     def _initialize_azure_openai_client(self):
#         """Initialize the Azure OpenAI client - ONLY ONCE"""
#         try:
#             if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
#                 ContentVerbalizer._client = AzureOpenAI(
#                     api_key=AZURE_OPENAI_API_KEY,
#                     api_version=AZURE_OPENAI_API_VERSION,
#                     azure_endpoint=AZURE_OPENAI_ENDPOINT
#                 )
#                 print("✅ Azure OpenAI client initialized")
#                 print(f"   Endpoint: {AZURE_OPENAI_ENDPOINT}")
#                 print(f"   Deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")
#             else:
#                 print("❌ Azure OpenAI credentials not found")
#                 print("⚠️  Using mock responses for testing")
                
#         except Exception as e:
#             print(f"❌ Error initializing Azure OpenAI client: {e}")
#             ContentVerbalizer._client = None
    
#     def verbalize_table(self, table_data: Dict) -> str:
#         """
#         Generate natural language description of table data
        
#         Args:
#             table_data: Dictionary containing table information
            
#         Returns:
#             str: Natural language description of the table
#         """
#         try:
#             # Prepare table metadata
#             metadata = f"""
#             Page: {table_data.get('page_number', 'Unknown')}
#             Rows: {table_data.get('row_count', 'Unknown')}
#             Columns: {table_data.get('column_count', 'Unknown')}
#             Section: {table_data.get('section_info', {}).get('section_content', 'Unknown')[:100]}
#             """
            
#             # Get table content (CSV format)
#             table_content = table_data.get('content', 'No table content available')
            
#             # Get the prompt
#             prompt = TableAnalysisPrompts.get_rfp_table_analysis_prompt(metadata, table_content)
            
#             # Generate verbalization
#             if self.client:
#                 return self._verbalize_with_azure_openai(prompt, content_type="table")
#             else:
#                 # Mock response for testing
#                 return self._generate_mock_table_verbalization(table_data)
                
#         except Exception as e:
#             print(f"❌ Error verbalizing table: {e}")
#             return f"Table from page {table_data.get('page_number', 'unknown')} with {table_data.get('row_count', 'unknown')} rows and {table_data.get('column_count', 'unknown')} columns."
    
#     def verbalize_image(self, image_data: Dict) -> str:
#         """
#         Generate natural language description of image data
        
#         Args:
#             image_data: Dictionary containing image information
            
#         Returns:
#             str: Natural language description of the image
#         """
#         try:
#             # Get the prompt
#             prompt = ImageAnalysisPrompts.get_rfp_image_analysis_prompt()
            
#             # For images, we need to handle base64 data if available
#             image_base64 = image_data.get('image_base64')
#             image_path = image_data.get('image_path')
            
#             if self.client and image_base64:
#                 return self._verbalize_image_with_azure_openai(prompt, image_base64)
#             else:
#                 # Mock response for testing or fallback to text content
#                 return self._generate_mock_image_verbalization(image_data)
                
#         except Exception as e:
#             print(f"❌ Error verbalizing image: {e}")
#             return f"Figure from page {image_data.get('page_number', 'unknown')} - {image_data.get('content', 'No description available')}"
    
#     def _verbalize_with_azure_openai(self, prompt: str, content_type: str) -> str:
#         """Generate verbalization using Azure OpenAI API"""
#         try:
#             response = self.client.chat.completions.create(
#                 model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use the deployment name
#                 messages=[
#                     {"role": "system", "content": "You are an expert document analyst specializing in technical content verbalization for Tetratech projects."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 max_tokens=600,
#                 temperature=0.3
#             )
#             return response.choices[0].message.content.strip()
#         except Exception as e:
#             print(f"❌ Azure OpenAI API error: {e}")
#             return f"Error generating {content_type} description with Azure OpenAI"
    
#     def _verbalize_image_with_azure_openai(self, prompt: str, image_base64: str) -> str:
#         """Generate image verbalization using Azure OpenAI Vision API"""
#         try:
#             response = self.client.chat.completions.create(
#                 model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use the deployment name
#                 messages=[
#                     {
#                         "role": "user",
#                         "content": [
#                             {"type": "text", "text": prompt},
#                             {
#                                 "type": "image_url",
#                                 "image_url": {
#                                     "url": f"data:image/png;base64,{image_base64}"
#                                 }
#                             }
#                         ]
#                     }
#                 ],
#                 max_tokens=600,
#                 temperature=0.3
#             )
#             return response.choices[0].message.content.strip()
#         except Exception as e:
#             print(f"❌ Azure OpenAI Vision API error: {e}")
#             return "Error generating image description with Azure OpenAI Vision"
    
#     def _generate_mock_table_verbalization(self, table_data: Dict) -> str:
#         """Generate mock table verbalization for testing"""
#         section_info = table_data.get('section_info', {})
#         section_content = section_info.get('section_content', 'Unknown Section')
        
#         mock_description = f"""This table from page {table_data.get('page_number', 'unknown')} contains structured data with {table_data.get('row_count', 'multiple')} rows and {table_data.get('column_count', 'several')} columns. The table appears in the {section_content[:50]} section and presents organized information relevant to Tetratech's project analysis. The data structure includes categorical and numerical information that supports decision-making processes for infrastructure and environmental projects. This tabular data aligns with Tetratech's Water Cycle & Management and Infrastructure & Resource Management domains, providing quantitative insights for project evaluation and resource allocation."""
        
#         return mock_description
    
#     def _generate_mock_image_verbalization(self, image_data: Dict) -> str:
#         """Generate mock image verbalization for testing"""
#         section_info = image_data.get('section_info', {})
#         section_content = section_info.get('section_content', 'Unknown Section')
#         original_content = image_data.get('content', '')
        
#         mock_description = f"""This figure from page {image_data.get('page_number', 'unknown')} presents visual information in the {section_content[:50]} section. The image contains technical diagrams, charts, or visual elements that support the document's narrative. Based on the extracted content '{original_content[:100]}', this visual element likely illustrates project components, system architecture, or data relationships. The figure aligns with Tetratech's technical domains, particularly Water Cycle & Management and Infrastructure & Resource Management, providing visual context for engineering and environmental consulting projects. The visual elements support understanding of complex technical concepts and project specifications."""
        
#         return mock_description
    
#     def get_model_info(self) -> Dict:
#         """Get information about the current Azure OpenAI model configuration"""
#         return {
#             "model_type": "azure_openai",
#             "client_initialized": self.client is not None,
#             "api_key_present": bool(AZURE_OPENAI_API_KEY),
#             "endpoint": AZURE_OPENAI_ENDPOINT,
#             "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
#             "status": "ready" if self.client else "mock_mode"
#         }
    
#     def test_verbalization(self) -> Dict:
#         """Test the verbalization functionality"""
#         test_table = {
#             "page_number": 1,
#             "row_count": 3,
#             "column_count": 4,
#             "content": "Project,Cost,Duration,Team\nPhase 1,$2M,6 months,10 people\nPhase 2,$3M,8 months,15 people",
#             "section_info": {"section_content": "Budget Overview"}
#         }
        
#         test_image = {
#             "page_number": 2,
#             "content": "Process flow diagram showing water treatment stages",
#             "section_info": {"section_content": "Technical Architecture"}
#         }
        
#         return {
#             "table_verbalization": self.verbalize_table(test_table),
#             "image_verbalization": self.verbalize_image(test_image),
#             "model_info": self.get_model_info()
#         }


import os
import base64
import asyncio
from typing import Dict, Optional
from .prompts import ImageAnalysisPrompts, TableAnalysisPrompts
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME
 
# Import Azure OpenAI
from openai import AsyncAzureOpenAI
 
class ContentVerbalizer:
    """Handle verbalization of tables and images using Azure OpenAI - SINGLETON PATTERN with ASYNC support"""
   
    _instance = None
    _client = None
    _initialized = False
   
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
   
    def __init__(self):
        """Initialize the verbalizer with Azure OpenAI - ONLY ONCE, SILENTLY REUSE"""
        if not ContentVerbalizer._initialized:
            self._initialize_azure_openai_client()
            ContentVerbalizer._initialized = True
        # NO print statements for subsequent initializations - silent reuse
   
    @property
    def client(self):
        """Get the shared Azure OpenAI client"""
        return ContentVerbalizer._client
   
    def _initialize_azure_openai_client(self):
        """Initialize the Azure OpenAI client - ONLY ONCE (now async client)"""
        try:
            if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
                ContentVerbalizer._client = AsyncAzureOpenAI(
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION,
                    azure_endpoint=AZURE_OPENAI_ENDPOINT
                )
                print("✅ Async Azure OpenAI client initialized")
                print(f"   Endpoint: {AZURE_OPENAI_ENDPOINT}")
                print(f"   Deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")
            else:
                print("❌ Azure OpenAI credentials not found")
                print("⚠️  Using mock responses for testing")
               
        except Exception as e:
            print(f"❌ Error initializing Azure OpenAI client: {e}")
            ContentVerbalizer._client = None
   
    async def verbalize_table(self, table_data: Dict) -> str:
        """
        Generate natural language description of table data (ASYNC)
       
        Args:
            table_data: Dictionary containing table information
           
        Returns:
            str: Natural language description of the table
        """
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
           
            # Generate verbalization (ASYNC)
            if self.client:
                return await self._verbalize_with_azure_openai(prompt, content_type="table")
            else:
                # Mock response for testing
                return self._generate_mock_table_verbalization(table_data)
               
        except Exception as e:
            print(f"❌ Error verbalizing table: {e}")
            return f"Table from page {table_data.get('page_number', 'unknown')} with {table_data.get('row_count', 'unknown')} rows and {table_data.get('column_count', 'unknown')} columns."
   
    async def verbalize_image(self, image_data: Dict) -> str:
        """
        Generate natural language description of image data (ASYNC)
       
        Args:
            image_data: Dictionary containing image information
           
        Returns:
            str: Natural language description of the image
        """
        try:
            # Get the prompt
            prompt = ImageAnalysisPrompts.get_rfp_image_analysis_prompt()
           
            # For images, we need to handle base64 data if available
            image_base64 = image_data.get('image_base64')
            image_path = image_data.get('image_path')
           
            if self.client and image_base64:
                return await self._verbalize_image_with_azure_openai(prompt, image_base64)
            else:
                # Mock response for testing or fallback to text content
                return self._generate_mock_image_verbalization(image_data)
               
        except Exception as e:
            print(f"❌ Error verbalizing image: {e}")
            return f"Figure from page {image_data.get('page_number', 'unknown')} - {image_data.get('content', 'No description available')}"
   
    async def _verbalize_with_azure_openai(self, prompt: str, content_type: str) -> str:
        """Generate verbalization using Azure OpenAI API (ASYNC)"""
        try:
            response = await self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use the deployment name
                messages=[
                    {"role": "system", "content": "You are an expert document analyst specializing in technical content verbalization for Tetratech projects."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Azure OpenAI API error: {e}")
            return f"Error generating {content_type} description with Azure OpenAI"
   
    async def _verbalize_image_with_azure_openai(self, prompt: str, image_base64: str) -> str:
        """Generate image verbalization using Azure OpenAI Vision API (ASYNC)"""
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
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Azure OpenAI Vision API error: {e}")
            return "Error generating image description with Azure OpenAI Vision"
   
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
        """Get information about the current Azure OpenAI model configuration"""
        return {
            "model_type": "async_azure_openai",
            "client_initialized": self.client is not None,
            "api_key_present": bool(AZURE_OPENAI_API_KEY),
            "endpoint": AZURE_OPENAI_ENDPOINT,
            "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
            "status": "ready" if self.client else "mock_mode"
        }
   
    async def test_verbalization(self) -> Dict:
        """Test the verbalization functionality (ASYNC)"""
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
       
        # Run both verbalizations concurrently
        table_verbalization, image_verbalization = await asyncio.gather(
            self.verbalize_table(test_table),
            self.verbalize_image(test_image)
        )
       
        return {
            "table_verbalization": table_verbalization,
            "image_verbalization": image_verbalization,
            "model_info": self.get_model_info()
        }
 