import json
import time
from typing import Dict, Optional, Any
from openai import AzureOpenAI
from config import (
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, 
    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME,
    LLM_CONFIG
)

class AzureOpenAIClient:
    """Azure OpenAI client for LLM-based document processing"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
        self.deployment_name = AZURE_OPENAI_DEPLOYMENT_NAME
        self.config = LLM_CONFIG
    
    def get_completion(self, prompt: str, system_message: Optional[str] = None) -> str:
        """Get text completion from Azure OpenAI"""
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        return self._call_api(messages, response_format="text")
    
    def get_structured_completion(self, prompt: str, system_message: str, response_format: str = "json") -> Dict:
        """Get structured completion (JSON) from Azure OpenAI"""
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self._call_api(messages, response_format="json")
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response}")
            return {"error": "Failed to parse JSON response", "raw_response": response}
    
    def analyze_with_retry(self, content: str, analysis_type: str, system_message: str) -> Dict:
        """Analyze content with retry mechanism"""
        for attempt in range(self.config["retry_attempts"]):
            try:
                return self.get_structured_completion(content, system_message)
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {analysis_type}: {e}")
                if attempt < self.config["retry_attempts"] - 1:
                    time.sleep(self.config["retry_delay"] * (attempt + 1))
                else:
                    print(f"All retry attempts failed for {analysis_type}")
                    return {"error": f"Failed after {self.config['retry_attempts']} attempts", "details": str(e)}
    
    def _call_api(self, messages: list, response_format: str = "text") -> str:
        """Make API call to Azure OpenAI with error handling"""
        try:
            kwargs = {
                "model": self.deployment_name,
                "messages": messages,
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_tokens"],
                "timeout": self.config["timeout"]
            }
            
            # Add response format for structured outputs
            if response_format == "json":
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Azure OpenAI API call failed: {e}")
            raise e
    
    def test_connection(self) -> bool:
        """Test Azure OpenAI connection"""
        try:
            test_response = self.get_completion("Test connection. Respond with 'OK'.")
            return "OK" in test_response.upper()
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count (1 token ≈ 0.75 words)"""
        words = len(text.split())
        return int(words / 0.75)
    
    def chunk_text_for_analysis(self, text: str, max_tokens: int = 3000) -> list:
        """Split large text into smaller chunks for analysis"""
        estimated_tokens = self.estimate_tokens(text)
        
        if estimated_tokens <= max_tokens:
            return [text]
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if self.estimate_tokens(test_chunk) > max_tokens and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk = test_chunk
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks