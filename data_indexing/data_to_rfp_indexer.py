import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from config import (AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_RFP_INDEX_NAME,
    AZURE_EMBEDDING_MODEL,
    AZURE_EMBEDDING_API_KEY,
    AZURE_EMBEDDING_ENDPOINT
)

class AzureSearchRFPResponseUploader:
    def __init__(self):
        load_dotenv()

        # Initialize Azure clients
        self.search_client = SearchClient(
            endpoint=AZURE_AI_SEARCH_ENDPOINT,
            index_name=AZURE_AI_SEARCH_RFP_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY)
        )

        self.openai_client = AzureOpenAI(
            api_key=AZURE_EMBEDDING_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=AZURE_EMBEDDING_ENDPOINT
        )

    def get_embedding(self, text: str, model: str = None) -> List[float]:
        if model is None:
            model = AZURE_EMBEDDING_MODEL
        try:
            response = self.openai_client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * 3072  # Return a zero vector if embedding fails

    def transform_chunk_to_document(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        metadata = chunk.get("metadata", {})
        llm_metadata = metadata.get("llm_extracted_metadata", {})
        table_info = metadata.get("table_info")
        image_info = metadata.get("image_info")

        document = {
            "chunk_id": chunk.get("chunk_id"),
            "project_id": chunk.get("project_id"),  # NEW FIELD
            "file_name": chunk.get("file_name"),
            "section_name": chunk.get("section_name"),
            "section_no": chunk.get("section_no"),
            "domain": chunk.get("domain"),
            "content_type": chunk.get("content_type"),
            "author": chunk.get("author"),
            "content": chunk.get("content"),
            "verbalized_content": chunk.get("verbalized_content"),
            'rfp_id': chunk.get('rfp_id'),  # Ensure rfp_id is included
            "metadata": {
                "created_at": metadata.get("created_at"),
                "chunk_index": metadata.get("chunk_index"),
                "word_count": metadata.get("word_count"),
                "char_count": metadata.get("char_count"),
                "llm_extracted_metadata": llm_metadata
            }
        }

        if table_info:
            document["metadata"]["table_info"] = {
                **table_info,
                "section_info": table_info.get("section_info", {})
            }

        if image_info:
            document["metadata"]["image_info"] = {
                **image_info,
                "section_info": image_info.get("section_info", {})
            }

        return document

    # def generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     documents = []

    #     for i, chunk in enumerate(chunks):
    #         print(f"Processing chunk {i + 1}/{len(chunks)}: {chunk.get('chunk_id', 'Unknown')}")
    #         document = self.transform_chunk_to_document(chunk)
    #         content_text = chunk.get("verbalized_content") or chunk.get("content", "")

    #         if content_text:
    #             document["content_vector"] = self.get_embedding(content_text)
    #         else:
    #             print(f"Warning: No content found for chunk {chunk.get('chunk_id', 'Unknown')}")
    #             document["content_vector"] = [0.0] * 3072  # Default zero vector for empty content

    #         documents.append(document)

    #     return documents

    def generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        documents = []

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i + 1}/{len(chunks)}: {chunk.get('chunk_id', 'Unknown')}")
            document = self.transform_chunk_to_document(chunk)

            # Prefer 'verbalized_content' if it's non-empty, otherwise fallback to 'content'
            verbalized_content = chunk.get("verbalized_content", "")
            content = chunk.get("content", "")
            
            content_text = verbalized_content.strip() if verbalized_content and verbalized_content.strip() else content.strip()

            if content_text:
                document["content_vector"] = self.get_embedding(content_text)
            else:
                print(f"Warning: No content found for chunk {chunk.get('chunk_id', 'Unknown')}")
                document["content_vector"] = [0.0] * 3072  # Default zero vector for empty content

            documents.append(document)

        return documents


    def upload_documents_in_batches(self, documents: List[Dict[str, Any]], batch_size: int = 50):
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
        chunks = chunk_data.get("chunks", [])
        if not chunks:
            print("❌ No chunks found in the input data")
            return

        print(f"📄 Found {len(chunks)} chunks to process")
        print("🔄 Generating embeddings and transforming documents...")
        documents = self.generate_embeddings_for_chunks(chunks)
        print("🔄 Uploading documents to Azure AI Search...")
        self.upload_documents_in_batches(documents)

    def load_and_upload_chunks(self, json_file_path: str):
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

# if __name__ == "__main__":
#     uploader = AzureSearchRFPUploader()
#     json_file_path = "C:\\Users\\Harshal.chaudhari\\venvs\\Tetra_Tech_ZIP\\Tetra_Tech_RFP_New\\document_processing_modular_code\\extracted_content\\text\\sample-2page-chester technology-project cost_text_chunks.json"  # Update with your actual file path
#     uploader.load_and_upload_chunks(json_file_path)