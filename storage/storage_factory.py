from config import USE_BLOB_STORAGE
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def get_storage_instance():
    with tracer.start_as_current_span("get_storage_instance_fn") as span:
        """Factory function to return appropriate storage instance based on configuration"""
        if USE_BLOB_STORAGE:
            from .azure_blob_storage import AzureBlobStorage
            return AzureBlobStorage()
        else:
            from .local_storage import LocalStorage
            return LocalStorage()