import os
import sys
from io import BytesIO
from storage.storage_factory import get_storage_instance
from main import DocumentProcessorMain
from config import USE_BLOB_STORAGE

from application_logging.custom_logging_to_app_insights import configure_logger, log_step, log_exception
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class MockUploadedFile:
    """Mock Streamlit UploadedFile for terminal usage"""
    def __init__(self, name: str, file_bytes: bytes):
        self.name = name
        self._bytes = file_bytes
    
    def read(self) -> bytes:
        return self._bytes

def main():
    with tracer.start_as_current_span("main_fn") as span:

        # Log step - store in App insights - traces table
        log_step(
                logger,
                "RFP processing started",
                level="info",
                step="main step",
            )
        
        print("🔵 RFP Document Processor (Terminal Mode)")
        print(f"📂 Storage Mode: {'Azure Blob' if USE_BLOB_STORAGE else 'Local'}")
        print("=" * 60)
        
        if not USE_BLOB_STORAGE:
            print("❌ Error: USE_BLOB_STORAGE is False")
            print("💡 Set USE_BLOB_STORAGE=True in config.py or environment variable")
            return
        
        # Initialize storage
        try:
            storage = get_storage_instance()
        except Exception as e:

            # Log exception - store in App insights - exceptions table
            # log_exception(logger,
            #     e,
            #     extra_message="Check your AZURE_STORAGE_CONNECTION_STRING in .env file"
            # )

            print(f"❌ Failed to initialize blob storage: {e}")
            print("💡 Check your AZURE_STORAGE_CONNECTION_STRING in .env file")
            return
        
        # List available documents
        print("📋 Listing documents in tetratech-input container...")
        try:
            documents = storage.list_input_documents()
        except Exception as e:
            print(f"❌ Failed to list documents: {e}")
            return
        
        if not documents:
            print("⚠️ No PDF documents found in tetratech-input-rfp container")
            print("💡 Upload some PDF files to the container first")
            return
        
        # Display document menu
        print(f"\n📁 Found {len(documents)} documents:")
        for i, doc in enumerate(documents, 1):
            print(f"[{i}] {doc}")
        
        # Get user selection
        while True:
            try:
                choice = input(f"\nSelect document to process (1-{len(documents)}): ").strip()
                if not choice:
                    print("👋 Exiting...")
                    return
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(documents):
                    selected_doc = documents[choice_num - 1]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(documents)}")
            except ValueError:
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                return
        
        print(f"\n🚀 Processing: {selected_doc}")
        print("-" * 60)
        
        # Read document from blob
        try:
            document_bytes = storage.read_document_bytes(selected_doc)
            print(f"📄 Read {len(document_bytes)} bytes from blob")
        except Exception as e:
            print(f"❌ Failed to read document: {e}")
            return
        
        # Create mock uploaded file for existing pipeline
        mock_file = MockUploadedFile(selected_doc, document_bytes)
        
        # Process document using existing pipeline
        processor = DocumentProcessorMain()  
        def progress_callback(message):
            print(f"   {message}")
        
        try:
            result = processor.process_document(mock_file, progress_callback)
            
            print("\n✅ Processing completed successfully!")
            print(f"📊 Results summary:")
            print(f"   📝 Text chunks: {result['stats']['text_count']}")
            print(f"   📋 Tables: {result['stats']['table_count']}")
            print(f"   🖼️ Images: {result['stats']['image_count']}")
            print(f"   🎯 Document type: {result.get('document_type', 'Unknown')}")
            
            if result.get('document_metadata'):
                metadata = result['document_metadata']
                print(f"   🏢 Client: {metadata.get('client_name', 'N/A')}")
                print(f"   📝 Project: {metadata.get('project_title', 'N/A')}")
            
            
            
        except Exception as e:
            print(f"\n❌ Processing failed: {e}")
            return

if __name__ == "__main__":
    main()