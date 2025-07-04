from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from config import AZURE_DOC_INTELLIGENCE_ENDPOINT, AZURE_DOC_INTELLIGENCE_KEY

class AzureDocumentProcessor:
    def __init__(self):
        self.client = DocumentIntelligenceClient(
            endpoint=AZURE_DOC_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(AZURE_DOC_INTELLIGENCE_KEY)
        )
    
    def analyze_document(self, file_bytes: bytes) -> dict:
        """Analyze document using prebuilt-layout model"""
        poller = self.client.begin_analyze_document(
            "prebuilt-layout",
            file_bytes,
            content_type="application/pdf"
        )
        return poller.result()