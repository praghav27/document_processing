import os
from config import SUPPORTED_EXTENSIONS

# from application_logging.custom_logging_to_app_insights import configure_logger, log_step, log_exception
from opentelemetry import trace

# Configure the logger
# logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class FileHandler:
    @staticmethod
    def validate_file(filename: str) -> bool:
        with tracer.start_as_current_span("validate_file_fn") as span:
            """Check if file extension is supported"""
            ext = os.path.splitext(filename)[1].lower()
            return ext in SUPPORTED_EXTENSIONS
    
    @staticmethod
    def process_file(uploaded_file) -> bytes:
        with tracer.start_as_current_span("process_file_fn") as span:
            """Convert uploaded file to bytes for Azure processing"""
            return uploaded_file.read()
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        with tracer.start_as_current_span("get_file_extension_fn") as span:
            """Get file extension"""
            return os.path.splitext(filename)[1].lower()