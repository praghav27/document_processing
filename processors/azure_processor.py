

import threading
import time
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeOutputOption
from azure.core.credentials import AzureKeyCredential
from config import AZURE_DOC_INTELLIGENCE_ENDPOINT, AZURE_DOC_INTELLIGENCE_KEY

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class AzureDocumentProcessor:
    @tracer.start_as_current_span("AzureDocumentProcessor_init_fn")
    def __init__(self):
        # Use thread-local storage for thread safety in parallel processing
        self._local = threading.local()
        
        # ADD: Rate limiting and retry configuration
        self.max_retries = 3
        self.retry_delay = 5.0  # 5 seconds between retries
        self.request_timeout = 300  # 5 minutes timeout
        
        # ADD: Request tracking to prevent overwhelming Azure
        self._request_lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum 1 second between requests
    
    @property
    def client(self):
        """Thread-safe client creation for parallel processing with connection pooling"""
        if not hasattr(self._local, 'client') or self._local.client is None:
            try:
                self._local.client = DocumentIntelligenceClient(
                    endpoint=AZURE_DOC_INTELLIGENCE_ENDPOINT,
                    credential=AzureKeyCredential(AZURE_DOC_INTELLIGENCE_KEY)
                )
                #print(f"✅ Created new Azure DI client for thread: {threading.current_thread().name}")
                log_custom_event(
                                logger,
                                f"Created new Azure DI client for thread: {threading.current_thread().name}",
                                level="info",
                                )
            except Exception as e:
                #print(f"❌ Failed to create Azure DI client: {e}")
                self._local.client = None
                raise
        return self._local.client
    
    def _wait_for_rate_limit(self):
        """Ensure minimum interval between requests to Azure DI"""
        with self._request_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
                #print(f"⏳ Rate limiting: Waiting {sleep_time:.2f}s before next Azure DI request")
                log_custom_event(
                                logger,
                                f"Rate limiting: Waiting {sleep_time:.2f}s before next Azure DI request",
                                level="info",
                )
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    @tracer.start_as_current_span("analyze_document_fn")
    def analyze_document(self, file_bytes: bytes, filename: str = None) -> tuple:
            """Analyze document using prebuilt-layout model with figures output - Thread Safe with Retry Logic"""
            
            # Determine content type based on file extension
            content_type = self._get_content_type(filename)
            
            for attempt in range(self.max_retries):
                try:
                    # Apply rate limiting
                    self._wait_for_rate_limit()
                    
                    # Use the layout model with figures output for comprehensive extraction
                    #print(f"🔍 Analyzing document with figures extraction (attempt {attempt + 1}/{self.max_retries})...")

                    log_custom_event(
                        logger,
                        f"Analyzing document with figures extraction (attempt {attempt + 1}/{self.max_retries})...",
                        level="info"
                    )
                    
                    # Use thread-safe client property with timeout
                    client = self.client
                    if client is None:
                        raise Exception("Failed to create Azure Document Intelligence client")
                    
                    poller = client.begin_analyze_document(
                        "prebuilt-layout",
                        file_bytes,
                        content_type=content_type,
                        output=[AnalyzeOutputOption.FIGURES]  # Enable figures extraction
                    )
                    
                    # ADD: Wait for result with timeout handling
                    #print(f"⏳ Waiting for analysis to complete (timeout: {self.request_timeout}s)...")
                    result = poller.result()
                    
                    if not result:
                        raise Exception("Azure Document Intelligence returned empty result")
                    
                    #print(f"📋 All poller attributes: {[attr for attr in dir(poller) if not attr.startswith('_')]}")
                    
                    operation_id = poller.details["operation_id"]
                    #print(f"Operation id : {operation_id}")
                    log_custom_event(
                                    logger,
                                    f"Document intelligence operation id : {operation_id}",
                                    level="info",
                                    )
                    
                    # Log what was found for debugging
                    self._log_analysis_results(result)
                    
                    #print(f"✅ Successfully analyzed {filename} on attempt {attempt + 1}")
                    log_custom_event(
                                    logger,
                                    f"Successfully analyzed {filename} on attempt {attempt + 1}",
                                    level="info",
                                    )
                    
                    # Return thread-safe client instance
                    return result, self.client, operation_id
                    
                except Exception as e:
                    #print(f"❌ Error during Azure Document Intelligence analysis (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        #print(f"🔄 Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                        
                        # Reset client on retry to handle connection issues
                        try:
                            self._local.client = None  # Force client recreation
                        except:
                            pass
                        continue
                    else:
                        #print(f"❌ Failed to analyze {filename} after {self.max_retries} attempts")
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
        #print(f"📊 Azure DI Analysis Results:")
        
        if hasattr(result, 'content'):
            #print(f"   - Content length: {len(result.content)} characters")
            log_custom_event(
                            logger,
                            f"Content length: {len(result.content)} characters",
                            level="info",
                            )
        
        if hasattr(result, 'paragraphs'):
            #print(f"   - Paragraphs found: {len(result.paragraphs) if result.paragraphs else 0}")
            log_custom_event(
                            logger,
                            f"Paragraphs found: {len(result.paragraphs) if result.paragraphs else 0}",
                            level="info",
                            )
        
        if hasattr(result, 'tables'):
            #print(f"   - Tables found: {len(result.tables) if result.tables else 0}")
            log_custom_event(
                            logger,
                            f"Tables found: {len(result.tables) if result.tables else 0}",
                            level="info",
                            )
        
        if hasattr(result, 'figures'):
            figures_count = len(result.figures) if result.figures else 0
            #print(f"   - Figures found: {figures_count}")
            log_custom_event(
                            logger,
                            f"Figures found: {figures_count}",
                            level="info",
                            )
            
            # Check which figures have IDs (extractable images)
            if result.figures:
                figures_with_ids = sum(1 for fig in result.figures if fig.id)
                #print(f"   - Figures with extractable images: {figures_with_ids}")
                
                # Log figure details
                for i, figure in enumerate(result.figures):
                    page_num = getattr(figure.bounding_regions[0], 'page_number', 'Unknown') if figure.bounding_regions else 'Unknown'
                    has_id = "✅" if figure.id else "❌"
                    #print(f"     Figure {i+1}: Page {page_num}, ID: {has_id}")
        
        if hasattr(result, 'pages'):
            #print(f"   - Pages analyzed: {len(result.pages) if result.pages else 0}")
            log_custom_event(
                            logger,
                            f"Pages analyzed: {len(result.pages) if result.pages else 0}",
                            level="info",
                            )
        
        #print("---")