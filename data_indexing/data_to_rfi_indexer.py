# import os
# import json
# from typing import List, Dict, Any
# from dotenv import load_dotenv
# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
# from openai import AzureOpenAI

# from config import (
#     AZURE_AI_SEARCH_ENDPOINT,
#     AZURE_AI_SEARCH_KEY,
#     AZURE_AI_SEARCH_RFI_INDEX_NAME,
#     AZURE_EMBEDDING_MODEL,
#     AZURE_EMBEDDING_API_KEY,
#     AZURE_EMBEDDING_ENDPOINT
# )

# class AzureSearchRFPRequestUploader:
#     def __init__(self):
#         load_dotenv()

#         # Initialize Azure clients
#         self.search_client = SearchClient(
#             endpoint=AZURE_AI_SEARCH_ENDPOINT,
#             index_name=AZURE_AI_SEARCH_RFI_INDEX_NAME,
#             credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY)
#         )

#         self.openai_client = AzureOpenAI(
#             api_key=AZURE_EMBEDDING_API_KEY,
#             api_version="2023-05-15",
#             azure_endpoint=AZURE_EMBEDDING_ENDPOINT
#         )

#     def get_embedding(self, text: str, model: str = None) -> List[float]:
#         """Generate embeddings for the given text."""
#         if model is None:
#             model = AZURE_EMBEDDING_MODEL
#         try:
#             response = self.openai_client.embeddings.create(input=text, model=model)
#             return response.data[0].embedding
#         except Exception as e:
#             print(f"Error generating embedding: {e}")
#             return [0.0] * 3072  # Default vector size for the model

#     # def transform_chunk_to_document(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
#     #     """Transform chunk data to match the Azure Search index schema."""
        
#     #     # Create the document structure based on your index schema
#     #     document = {
#     #         "chunk_id": chunk.get("chunk_id"),
#     #         "project_id": chunk.get("project_id"),
#     #         "project_name": chunk.get("project_name"),
#     #         "client": chunk.get("client"),
#     #         "region": chunk.get("region"),
#     #         "industry": chunk.get("industry"),
#     #         "prepared_date": chunk.get("prepared_date"),
#     #         "station_discipline": chunk.get("station_discipline"),
#     #         "scope_of_work": chunk.get("scope_of_work"),  # This is the text field
#     #         "required_activities": chunk.get("required_activities")
#     #     }

#     #     # Generate embedding for scope_of_work and assign to scope_of_work_vectorized
#     #     scope_of_work_text = chunk.get("scope_of_work", "")
#     #     required_activities_text= chunk.get("required_activities")
#     #     if scope_of_work_text:
#     #         print(f"Generating embedding for scope of work: {scope_of_work_text[:100]}...")
#     #         document["scope_of_work_vectorized"] = self.get_embedding(scope_of_work_text)
#     #     else:
#     #         print(f"Warning: No scope_of_work found for chunk {chunk.get('chunk_id', 'Unknown')}")
#     #         document["scope_of_work_vectorized"] = [0.0] * 3072  # Default zero vector
#     #     if required_activities_text:
#     #         print(f"Generating embedding for required activities: {required_activities_text[:100]}...")
#     #         document["required_activities_vectorized"] = self.get_embedding(required_activities_text)
#     #     else:
#     #         print(f"Warning: No scope_of_work found for chunk {chunk.get('chunk_id', 'Unknown')}")
#     #         document["required_activities_vectorized"] = [0.0] * 3072  # Default zero vector
#     #     return document

#     def transform_chunk_to_document(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
#         """Transform chunk data to match the Azure Search index schema."""
 
#             # Helper function to determine a valid date
#         def get_prepared_date(chunk: Dict[str, Any]) -> str:
#             date_str = chunk.get("prepared_date", "").strip().lower()
#             invalid_values = {"", "none", "null", "na", "n/a","Not mentioned in document"}
 
#             if date_str in invalid_values:
#                 # Extract year from project_idS
#                 project_id = chunk.get("project_id", "")
#                 # Example project_id: "705-25318708.00"
#                 # Extract the part after the first dash
#                 try:
#                     part_after_dash = project_id.split("-")[1]
#                     # Extract the first two digits to get the year part
#                     year_prefix = part_after_dash[:2]
 
#                     # Convert to int and form year as 20xx
#                     year = int(year_prefix)
#                     if year < 66:  # Assuming 2000-2049 range
#                         year += 2000
#                     else:
#                         year += 1900  # For safety if needed

#                     # Return date as YYYY-01-01
#                     return f"{year}-01-01"
#                 except Exception as e:
#                     print(f"⚠️ Warning: Failed to parse year from project_id '{project_id}': {e}")
#                     return None  # or some fallback date
#             else:
#                 # Assume the date is valid and return as is
#                 return chunk.get("prepared_date")
 
#         # Use the helper to get a proper prepared_date value
#         prepared_date_value = get_prepared_date(chunk)

#         # Create the document structure based on your index schema
#         document = {
#             "chunk_id": chunk.get("chunk_id"),
#             "project_id": chunk.get("project_id"),
#             "project_name": chunk.get("project_name"),
#             "client": chunk.get("client"),
#             "region": chunk.get("region"),
#             "industry": chunk.get("industry"),
#             "prepared_date": prepared_date_value,
#             "station_discipline": chunk.get("station_discipline"),
#             "scope_of_work": chunk.get("scope_of_work"),  # This is the text field
#             "required_activities": chunk.get("required_activities")
#         }
 
#         # Generate embedding for scope_of_work and assign to scope_of_work_vectorized
#         scope_of_work_text = chunk.get("scope_of_work", "")
#         if scope_of_work_text:
#             print(f"Generating embedding for scope of work: {scope_of_work_text[:100]}...")
#             document["scope_of_work_vectorized"] = self.get_embedding(scope_of_work_text)
#         else:
#             print(f"Warning: No scope_of_work found for chunk {chunk.get('chunk_id', 'Unknown')}")
#             document["scope_of_work_vectorized"] = [0.0] * 3072  # Default zero vector
 
#         return document

#     def generate_documents_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """Generate documents with embeddings for all chunks."""
#         documents = []

#         for i, chunk in enumerate(chunks):
#             print(f"Processing chunk {i + 1}/{len(chunks)}: {chunk.get('chunk_id', 'Unknown')}")
#             document = self.transform_chunk_to_document(chunk)
#             documents.append(document)

#         return documents

#     def upload_documents_in_batches(self, documents: List[Dict[str, Any]], batch_size: int = 50):
#         """Upload documents to Azure Search in batches."""
#         total_docs = len(documents)
#         successful_uploads = 0
#         failed_uploads = 0

#         for i in range(0, total_docs, batch_size):
#             batch = documents[i:i + batch_size]
#             batch_num = (i // batch_size) + 1
#             total_batches = (total_docs + batch_size - 1) // batch_size

#             print(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} documents)...")
#             try:
#                 result = self.search_client.upload_documents(documents=batch)
#                 batch_successful = sum(1 for r in result if r.succeeded)
#                 batch_failed = len(batch) - batch_successful

#                 for r in result:
#                     if not r.succeeded:
#                         print(f"Failed to upload document {r.key}: {r.error_message}")

#                 successful_uploads += batch_successful
#                 failed_uploads += batch_failed
#                 print(f"Batch {batch_num} completed: {batch_successful} successful, {batch_failed} failed")

#             except Exception as e:
#                 print(f"Error uploading batch {batch_num}: {e}")
#                 failed_uploads += len(batch)

#         print(f"\n✅ Upload completed!")
#         print(f"📊 Total documents: {total_docs}")
#         print(f"✅ Successful uploads: {successful_uploads}")
#         print(f"❌ Failed uploads: {failed_uploads}")

#         return successful_uploads, failed_uploads

#     def upload_chunks_from_dict(self, chunk_data: Dict[str, Any]):
#         """Upload chunks from dictionary data."""
#         chunks = chunk_data.get("chunks", [])
#         if not chunks:
#             print("❌ No chunks found in the input data")
#             return

#         print(f"📄 Found {len(chunks)} chunks to process")
#         print("🔄 Generating embeddings and transforming documents...")
#         documents = self.generate_documents_for_chunks(chunks)
#         print("🔄 Uploading documents to Azure AI Search...")
#         self.upload_documents_in_batches(documents)

#     def load_and_upload_chunks(self, json_file_path: str):
#         """Load JSON file and upload chunks to Azure Search."""
#         try:
#             with open(json_file_path, 'r', encoding='utf-8') as file:
#                 data = json.load(file)
#             print(f"✅ Loaded JSON data from {json_file_path}")
#         except FileNotFoundError:
#             print(f"❌ File not found: {json_file_path}")
#             return
#         except json.JSONDecodeError as e:
#             print(f"❌ Invalid JSON format: {e}")
#             return

#         self.upload_chunks_from_dict(data)

#     def upload_direct_data(self, data: Dict[str, Any]):
#         """Upload data directly from a dictionary (useful for the provided JSON data)."""
#         print("🔄 Processing provided data...")
#         self.upload_chunks_from_dict(data)

#     def test_single_document_upload(self, chunk: Dict[str, Any]):
#         """Test uploading a single document - useful for debugging."""
#         print("🔄 Testing single document upload...")
#         document = self.transform_chunk_to_document(chunk)
        
#         print(f"Document structure:")
#         for key, value in document.items():
#             if key == "scope_of_work_vectorized":
#                 print(f"  {key}: [vector of length {len(value)}]")
#             else:
#                 print(f"  {key}: {value}")
        
#         try:
#             result = self.search_client.upload_documents(documents=[document])
#             if result[0].succeeded:
#                 print(f"✅ Successfully uploaded document: {result[0].key}")
#             else:
#                 print(f"❌ Failed to upload document: {result[0].error_message}")
#         except Exception as e:
#             print(f"❌ Error during upload: {e}")


# if __name__ == "__main__":
#     uploader = AzureSearchRFPRequestUploader()
    
#     # Your provided JSON data
#     data = {
#         "filename": "705-25318708.00-RFP-Waubaushene TS-EN-ST-TEL-TIP",
#         "total_chunks": 1,
#         "processing_method": "enhanced_chunking_with_verbalization_and_llm_metadata",
#         "chunk_types": {
#             "text": 1,
#             "table": 0,
#             "image": 0
#         },
#         "created_at": "",
#         "chunks": [
#             {
#                 "chunk_id": "f7127442",
#                 "project_id": "705-25318708.00",
#                 "project_name": "TECHNICAL INFORMATION PACKAGE (TIP)",
#                 "client": "Hydro One Networks Inc.",
#                 "region": "Toronto, ON, Canada",
#                 "industry": "Telecommunications",
#                 "prepared_date": "none",
#                 "station_discipline": "Telecom",
#                 "scope_of_work": "The scope includes designing and implementing a new DESN LAN, decommissioning the existing LAN, reconfiguring routers for SCADA connectivity, installing inter-building fibre and metallic cables, relocating Rogers fibre cable, and ensuring compliance with Hydro One standards.",
#                 "required_activities": "Tasks include reviewing scope documents, collaborating with stakeholders, preparing design packages, updating drawings, ordering materials, configuring routers and switches, testing LAN systems, and submitting QA/QC forms."
#             }
#         ]
#     }
    
#     # Test single document first (recommended for debugging)
#     print("=== Testing Single Document Upload ===")
#     uploader.test_single_document_upload(data["chunks"][0])
    
#     # Upload all data
#     print("\n=== Uploading All Data ===")
#     uploader.upload_direct_data(data)
    
#     # Alternative: Load from a JSON file
#     # json_file_path = "path/to/your/json/file.json"
#     # uploader.load_and_upload_chunks(json_file_path)


import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
 
from config import (
    AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_RFI_INDEX_NAME,
    AZURE_EMBEDDING_MODEL,
    AZURE_EMBEDDING_API_KEY,
    AZURE_EMBEDDING_ENDPOINT
)
 
class AzureSearchRFPRequestUploader:
    def __init__(self):
        load_dotenv()
 
        # Initialize Azure clients
        self.search_client = SearchClient(
            endpoint=AZURE_AI_SEARCH_ENDPOINT,
            index_name=AZURE_AI_SEARCH_RFI_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY)
        )
 
        self.openai_client = AzureOpenAI(
            api_key=AZURE_EMBEDDING_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=AZURE_EMBEDDING_ENDPOINT
        )
 
    def get_embedding(self, text: str, model: str = None) -> List[float]:
        """Generate embeddings for the given text."""
        if model is None:
            model = AZURE_EMBEDDING_MODEL
        try:
            response = self.openai_client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * 3072  # Default vector size for the model
 
    # def transform_chunk_to_document(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
    #     """Transform chunk data to match the Azure Search index schema."""
       
    #     # Create the document structure based on your index schema
    #     document = {
    #         "chunk_id": chunk.get("chunk_id"),
    #         "project_id": chunk.get("project_id"),
    #         "project_name": chunk.get("project_name"),
    #         "client": chunk.get("client"),
    #         "region": chunk.get("region"),
    #         "industry": chunk.get("industry"),
    #         "prepared_date": chunk.get("prepared_date"),
    #         "station_discipline": chunk.get("station_discipline"),
    #         "scope_of_work": chunk.get("scope_of_work"),  # This is the text field
    #         "required_activities": chunk.get("required_activities")
    #     }
 
    #     # Generate embedding for scope_of_work and assign to scope_of_work_vectorized
    #     scope_of_work_text = chunk.get("scope_of_work", "")
    #     required_activities_text= chunk.get("required_activities")
    #     if scope_of_work_text:
    #         print(f"Generating embedding for scope of work: {scope_of_work_text[:100]}...")
    #         document["scope_of_work_vectorized"] = self.get_embedding(scope_of_work_text)
    #     else:
    #         print(f"Warning: No scope_of_work found for chunk {chunk.get('chunk_id', 'Unknown')}")
    #         document["scope_of_work_vectorized"] = [0.0] * 3072  # Default zero vector
    #     if required_activities_text:
    #         print(f"Generating embedding for required activities: {required_activities_text[:100]}...")
    #         document["required_activities_vectorized"] = self.get_embedding(required_activities_text)
    #     else:
    #         print(f"Warning: No scope_of_work found for chunk {chunk.get('chunk_id', 'Unknown')}")
    #         document["required_activities_vectorized"] = [0.0] * 3072  # Default zero vector
    #     return document
 
    def transform_chunk_to_document(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Transform chunk data to match the Azure Search index schema."""
 
            # Helper function to determine a valid date
        def get_prepared_date(chunk: Dict[str, Any]) -> str:
            date_str = chunk.get("prepared_date", "").strip().lower()
            invalid_values = {"", "none", "null", "na", "n/a"}
 
            if date_str in invalid_values:
                # Extract year from project_idS
                project_id = chunk.get("project_id", "")
                # Example project_id: "705-25318708.00"
                # Extract the part after the first dash
                try:
                    part_after_dash = project_id.split("-")[1]
                    # Extract the first two digits to get the year part
                    year_prefix = part_after_dash[:2]
 
                    # Convert to int and form year as 20xx
                    year = int(year_prefix)
                    if year < 66:  # Assuming 2000-2049 range
                        year += 2000
                    else:
                        year += 1900  # For safety if needed
 
                    # Return date as YYYY-01-01
                    return f"{year}-01-01"
                except Exception as e:
                    print(f"⚠️ Warning: Failed to parse year from project_id '{project_id}': {e}")
                    return None  # or some fallback date
            else:
                # Assume the date is valid and return as is
                return chunk.get("prepared_date")
 
        # Use the helper to get a proper prepared_date value
        prepared_date_value = get_prepared_date(chunk)
 
        # Create the document structure based on your index schema
        document = {
            "chunk_id": chunk.get("chunk_id"),
            "project_id": chunk.get("project_id"),
            "project_name": chunk.get("project_name"),
            "client": chunk.get("client"),
            "region": chunk.get("region"),
            "industry": chunk.get("industry"),
            # "prepared_date": prepared_date_value,
            "prepared_date": chunk.get("prepared_date"),
            "station_discipline": chunk.get("station_discipline"),
            "scope_of_work": chunk.get("scope_of_work"),  # This is the text field
            "required_activities": chunk.get("required_activities")
        }
 
        # Generate embedding for scope_of_work and assign to scope_of_work_vectorized
        scope_of_work_text = chunk.get("scope_of_work", "")
        if scope_of_work_text:
            print(f"Generating embedding for scope of work: {scope_of_work_text[:100]}...")
            document["scope_of_work_vectorized"] = self.get_embedding(scope_of_work_text)
        else:
            print(f"Warning: No scope_of_work found for chunk {chunk.get('chunk_id', 'Unknown')}")
            document["scope_of_work_vectorized"] = [0.0] * 3072  # Default zero vector
 
        return document
 
    def generate_documents_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate documents with embeddings for all chunks."""
        documents = []
 
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i + 1}/{len(chunks)}: {chunk.get('chunk_id', 'Unknown')}")
            document = self.transform_chunk_to_document(chunk)
            documents.append(document)
 
        return documents
 
    def upload_documents_in_batches(self, documents: List[Dict[str, Any]], batch_size: int = 50):
        """Upload documents to Azure Search in batches."""
        total_docs = len(documents)
        successful_uploads = 0
        failed_uploads = 0
 
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_docs + batch_size - 1) // batch_size
 
            print(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} documents)...")
            try:
                result = self.search_client.upload_documents(documents=batch)
                batch_successful = sum(1 for r in result if r.succeeded)
                batch_failed = len(batch) - batch_successful
 
                for r in result:
                    if not r.succeeded:
                        print(f"Failed to upload document {r.key}: {r.error_message}")
 
                successful_uploads += batch_successful
                failed_uploads += batch_failed
                print(f"Batch {batch_num} completed: {batch_successful} successful, {batch_failed} failed")
 
            except Exception as e:
                print(f"Error uploading batch {batch_num}: {e}")
                failed_uploads += len(batch)
 
        print(f"\n✅ Upload completed!")
        print(f"📊 Total documents: {total_docs}")
        print(f"✅ Successful uploads: {successful_uploads}")
        print(f"❌ Failed uploads: {failed_uploads}")
 
        return successful_uploads, failed_uploads
 
    def upload_chunks_from_dict(self, chunk_data: Dict[str, Any]):
        """Upload chunks from dictionary data."""
        chunks = chunk_data.get("chunks", [])
        if not chunks:
            print("❌ No chunks found in the input data")
            return
 
        print(f"📄 Found {len(chunks)} chunks to process")
        print("🔄 Generating embeddings and transforming documents...")
        documents = self.generate_documents_for_chunks(chunks)
        print("🔄 Uploading documents to Azure AI Search...")
        self.upload_documents_in_batches(documents)
 
    def load_and_upload_chunks(self, json_file_path: str):
        """Load JSON file and upload chunks to Azure Search."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            print(f"✅ Loaded JSON data from {json_file_path}")
        except FileNotFoundError:
            print(f"❌ File not found: {json_file_path}")
            return
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {e}")
            return
 
        self.upload_chunks_from_dict(data)
 
    def upload_direct_data(self, data: Dict[str, Any]):
        """Upload data directly from a dictionary (useful for the provided JSON data)."""
        print("🔄 Processing provided data...")
        self.upload_chunks_from_dict(data)
 
    def test_single_document_upload(self, chunk: Dict[str, Any]):
        """Test uploading a single document - useful for debugging."""
        print("🔄 Testing single document upload...")
        document = self.transform_chunk_to_document(chunk)
       
        print(f"Document structure:")
        for key, value in document.items():
            if key == "scope_of_work_vectorized":
                print(f"  {key}: [vector of length {len(value)}]")
            else:
                print(f"  {key}: {value}")
       
        try:
            result = self.search_client.upload_documents(documents=[document])
            if result[0].succeeded:
                print(f"✅ Successfully uploaded document: {result[0].key}")
            else:
                print(f"❌ Failed to upload document: {result[0].error_message}")
        except Exception as e:
            print(f"❌ Error during upload: {e}")
 
 
if __name__ == "__main__":
    uploader = AzureSearchRFPRequestUploader()
   
    # Your provided JSON data
    data = {
        "filename": "705-25318708.00-RFP-Waubaushene TS-EN-ST-TEL-TIP",
        "total_chunks": 1,
        "processing_method": "enhanced_chunking_with_verbalization_and_llm_metadata",
        "chunk_types": {
            "text": 1,
            "table": 0,
            "image": 0
        },
        "created_at": "",
        "chunks": [
            {
                "chunk_id": "f7127442",
                "project_id": "705-25318708.00",
                "project_name": "TECHNICAL INFORMATION PACKAGE (TIP)",
                "client": "Hydro One Networks Inc.",
                "region": "Toronto, ON, Canada",
                "industry": "Telecommunications",
                "prepared_date": "none",
                "station_discipline": "Telecom",
                "scope_of_work": "The scope includes designing and implementing a new DESN LAN, decommissioning the existing LAN, reconfiguring routers for SCADA connectivity, installing inter-building fibre and metallic cables, relocating Rogers fibre cable, and ensuring compliance with Hydro One standards.",
                "required_activities": "Tasks include reviewing scope documents, collaborating with stakeholders, preparing design packages, updating drawings, ordering materials, configuring routers and switches, testing LAN systems, and submitting QA/QC forms."
            }
        ]
    }
   
    # Test single document first (recommended for debugging)
    print("=== Testing Single Document Upload ===")
    uploader.test_single_document_upload(data["chunks"][0])
   
    # Upload all data
    print("\n=== Uploading All Data ===")
    uploader.upload_direct_data(data)
   
    # Alternative: Load from a JSON file
    # json_file_path = "path/to/your/json/file.json"
    # uploader.load_and_upload_chunks(json_file_path)
 