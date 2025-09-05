from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeOutputOption
from azure.core.credentials import AzureKeyCredential
from config import AZURE_DOC_INTELLIGENCE_ENDPOINT, AZURE_DOC_INTELLIGENCE_KEY

from application_logging.custom_logging_to_app_insights import configure_logger, log_step, log_exception
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class AzureDocumentProcessor:
    def __init__(self):
        with tracer.start_as_current_span("AzureDocumentProcessor_init_fn") as span:
            self.client = DocumentIntelligenceClient(
                endpoint=AZURE_DOC_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(AZURE_DOC_INTELLIGENCE_KEY)
            )
    
    def analyze_document(self, file_bytes: bytes, filename: str = None) -> tuple:
        with tracer.start_as_current_span("analyze_document_fn") as span:
            """Analyze document using prebuilt-layout model with figures output"""
            
            # Determine content type based on file extension
            content_type = self._get_content_type(filename)
            
            try:
                # Use the layout model with figures output for comprehensive extraction
                print(f"🔍 Analyzing document with figures extraction enabled...")

                log_step(
                    logger,
                    "Analyzing document with figures extraction enabled...",
                    level="info",
                    step="main step",
                )
                
                poller = self.client.begin_analyze_document(
                    "prebuilt-layout",
                    file_bytes,
                    content_type=content_type,
                    output=[AnalyzeOutputOption.FIGURES]  # Enable figures extraction
                )
                
                result = poller.result()
                print(poller.details)  # Debug: Print poller details


                print(f"📋 All poller attributes: {[attr for attr in dir(poller) if not attr.startswith('_')]}")
                # Debug: Print result attributes to understand the structure
                print(f"📋 Poller attributes: {dir(poller)}")

                print(f"📋 All result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                # Debug: Print result attributes to understand the structure
                print(f"📋 Result attributes: {dir(result)}")
                print(f"poller details: {poller.details}")

                
                operation_id = poller.details["operation_id"]
                print(f"Operation id : {operation_id}")
                
                # # Get operation details properly
                # operation_id = None
                # if hasattr(poller, '_polling_method') and hasattr(poller._polling_method, '_operation_location_header'):
                #     operation_location = poller._polling_method._operation_location_header
                #     if operation_location:
                #         # Extract operation ID from the location URL
                #         operation_id = operation_location.split('/')[-1].split('?')[0]
                
                # # Alternative method to get operation ID
                # if not operation_id and hasattr(result, 'model_id'):
                #     # For newer versions, the operation ID might be in different places
                #     try:
                #         operation_id = getattr(poller, 'operation_id', None)
                #     except:
                #         pass
                
                # print(f"📋 Operation ID: {operation_id}")
                
                # Log what was found for debugging
                self._log_analysis_results(result)
                
                return result, self.client, operation_id
                
            except Exception as e:
                print(f"Error during Azure Document Intelligence analysis: {e}")
                raise e
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename"""
        if not filename:
            return "application/pdf"  # Default
        
        extension = filename.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'doc': 'application/msword',
            'xls': 'application/vnd.ms-excel'
        }
        
        return content_types.get(extension, 'application/pdf')
    
    def _log_analysis_results(self, result):
        """Log analysis results for debugging"""
        print(f"📊 Azure DI Analysis Results:")
        
        if hasattr(result, 'content'):
            print(f"   - Content length: {len(result.content)} characters")
        
        if hasattr(result, 'paragraphs'):
            print(f"   - Paragraphs found: {len(result.paragraphs) if result.paragraphs else 0}")
        
        if hasattr(result, 'tables'):
            print(f"   - Tables found: {len(result.tables) if result.tables else 0}")
        
        if hasattr(result, 'figures'):
            figures_count = len(result.figures) if result.figures else 0
            print(f"   - Figures found: {figures_count}")
            
            # Check which figures have IDs (extractable images)
            if result.figures:
                figures_with_ids = sum(1 for fig in result.figures if fig.id)
                print(f"   - Figures with extractable images: {figures_with_ids}")
                
                # Log figure details
                for i, figure in enumerate(result.figures):
                    page_num = getattr(figure.bounding_regions[0], 'page_number', 'Unknown') if figure.bounding_regions else 'Unknown'
                    has_id = "✅" if figure.id else "❌"
                    print(f"     Figure {i+1}: Page {page_num}, ID: {has_id}")
        
        if hasattr(result, 'pages'):
            print(f"   - Pages analyzed: {len(result.pages) if result.pages else 0}")
        
        print("---")