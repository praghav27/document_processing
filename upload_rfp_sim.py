



"""
Tetra Tech RFP/RFI Processing Pipeline - Enhanced Component Format
----------------------------------------------------------------
Enhanced version with full parallel processing and component-specific fields output.
"""

# =========================
# 📦 IMPORTS
# =========================
import os
import asyncio
import concurrent.futures
import json
import uuid
from datetime import datetime
from typing import Tuple, List, Dict, Any
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery, QueryType, QueryCaptionType

# Project imports (keep as provided)
from processors.extraction.text_extractor import TextExtractor
from processors.azure_processor import AzureDocumentProcessor
from processors.file_handler import FileHandler
import time
from config import (
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_RFI_INDEX_NAME,
    AZURE_AI_SEARCH_RFP_INDEX_NAME,
)
from llm_metadata.rfi_extractor import RFIExtractor


# =========================
# 🔌 OPENAI CLIENT
# =========================
def get_openai_client():
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


# =========================
# 📂 FILE HANDLING
# =========================
def get_file_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return FileHandler.process_file(f)


# =========================
# 📍 SECTION IDENTIFIER
# =========================
def find_section(client, model: str, input_text: str, custom_prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that finds the section."},
            {"role": "user", "content": f"{custom_prompt}\n\nText:\n{input_text}"},
        ],
        temperature=0.5,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


# =========================
# 🚀 PARALLEL AZURE DOCUMENT PROCESSING
# =========================
async def process_document_async(file_path: str, file_name: str) -> Tuple[Any, str, str]:
    """
    Process a single document through Azure Document Intelligence asynchronously.
    
    Args:
        file_path (str): Path to the file
        file_name (str): Name of the file
    
    Returns:
        Tuple[Any, str, str]: (azure_result, file_path, file_name)
    """
    try:
        file_bytes = get_file_bytes(file_path)
        
        # Run Azure Document Intelligence in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        def process_doc():
            azure_processor = AzureDocumentProcessor()
            result, client, operation_id = azure_processor.analyze_document(file_bytes, file_name)
            return result
        
        # Use ThreadPoolExecutor for CPU-bound/IO-bound operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            azure_result = await loop.run_in_executor(executor, process_doc)
        
        print(f"✅ Document processing completed for: {file_name}")
        return azure_result, file_path, file_name
    
    except Exception as e:
        print(f"❌ Error processing {file_name}: {str(e)}")
        return None, file_path, file_name


async def extract_text_and_metadata_async(azure_result: Any, file_path: str, file_name: str) -> Tuple[Dict, List, str]:
    """
    Extract text and metadata from processed Azure result asynchronously.
    
    Args:
        azure_result: Result from Azure Document Intelligence
        file_path (str): Original file path
        file_name (str): Original file name
    
    Returns:
        Tuple[Dict, List, str]: (metadata, text_elements, file_name)
    """
    try:
        if azure_result is None:
            print(f"⚠️ Skipping text extraction for {file_name} due to processing error")
            return {}, [], file_name
        
        # Run text extraction and metadata extraction in parallel
        loop = asyncio.get_event_loop()
        
        def extract_text():
            text_extractor = TextExtractor()
            return text_extractor.extract_text(azure_result)
        
        # Extract text in thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            text_elements = await loop.run_in_executor(executor, extract_text)
        
        # Extract metadata (this is already async)
        rfi_extractor = RFIExtractor()
        metadata = await rfi_extractor.extract_metadata_only(text_elements, azure_di_result=azure_result)
        
        print(f"✅ Text and metadata extraction completed for: {file_name}")
        return metadata, text_elements, file_name
    
    except Exception as e:
        print(f"❌ Error extracting data from {file_name}: {str(e)}")
        return {}, [], file_name


# =========================
# 📂 ENHANCED PARALLEL RFI METADATA EXTRACTION WITH CHUNK CREATION
# =========================
async def extract_rfi_chunk_from_file_parallel(file_path: str, file_name: str, project_id: str = None) -> Dict:
    """
    Extract RFI metadata from a single file and create a complete chunk with enhanced component format.
    
    Args:
        file_path (str): Path to the file
        file_name (str): Name of the file
        project_id (str): Optional project ID
    
    Returns:
        Dict: Complete chunk with enhanced component format
    """
    # Step 1: Process document through Azure Document Intelligence
    azure_result, _, _ = await process_document_async(file_path, file_name)
    
    # Step 2: Extract text and metadata in parallel
    metadata, text_elements, _ = await extract_text_and_metadata_async(azure_result, file_path, file_name)
    
    # Step 3: Create enhanced chunk structure
    chunk = create_enhanced_chunk(metadata, text_elements, file_name, project_id)
    
    return chunk


def create_enhanced_chunk(metadata: Dict, text_elements: List, file_name: str, project_id: str = None) -> Dict:
    """
    Create enhanced chunk structure with component-specific fields.
    
    Args:
        metadata (Dict): Extracted metadata with enhanced component format
        text_elements (List): Extracted text elements
        file_name (str): Name of the file
        project_id (str): Optional project ID
    
    Returns:
        Dict: Enhanced chunk with component-specific fields
    """
    # Generate unique chunk ID
    chunk_id = str(uuid.uuid4())[:8]
    
    # Use project_id or generate from file name
    if not project_id:
        project_id = f"proj_{file_name.replace('.', '_').replace(' ', '_')}"
    
    # Create enhanced chunk structure
    chunk = {
        "chunk_id": chunk_id,
        "project_id": project_id,
        "file_name": file_name,
        "content_type": "document",
        "created_at": datetime.now().isoformat(),
        
        # Basic metadata fields
        "project_name": metadata.get("project_name", ""),
        "client": metadata.get("client", ""),
        "industry": metadata.get("industry", ""),
        "region": metadata.get("region", ""),
        "prepared_date": metadata.get("prepared_date", ""),
        
        # Enhanced components with specific fields
        "components": metadata.get("components", {}),
        
        # Additional chunk information
        "text_elements_count": len(text_elements),
        "total_content_length": sum(len(elem.get('content', '')) for elem in text_elements),
        "processing_timestamp": datetime.now().isoformat()
    }
    
    return chunk


# =========================
# 🔍 ASYNC AZURE COGNITIVE SEARCH (UPDATED FOR COMPONENT FORMAT)
# =========================
async def search_query_async_enhanced(user_question, chunk_data):
    """
    Perform Azure Cognitive Search asynchronously with enhanced component-based queries.
    """
    print("🔍 Starting async Azure Search with enhanced component format...")
    
    # Extract search parameters from chunk data
    components = chunk_data.get("components", {})
    
    # Combine all scope_of_work and required_activities from all components
    all_scope_of_work = []
    all_required_activities = []
    
    for comp_code, comp_data in components.items():
        scope = comp_data.get("scope_of_work", "")
        activities = comp_data.get("required_activities", "")
        
        if scope and scope != "not mentioned in document":
            all_scope_of_work.append(scope)
        if activities and activities != "not mentioned in document":
            all_required_activities.append(activities)
    
    # Combine scope and activities
    combined_scope = " ".join(all_scope_of_work)
    combined_activities = " ".join(all_required_activities)
    
    # Create metadata string for search
    metadata_parts = []
    for key in ["client", "region", "industry", "project_name"]:
        value = chunk_data.get(key, "")
        if value:
            metadata_parts.append(f"{key} is {value}")
    
    query = "; ".join(metadata_parts)
    
    async def search_rfi_index():
        """Search RFI index asynchronously"""
        loop = asyncio.get_event_loop()
        
        def rfi_search():
            credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
            client_a = SearchClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, index_name=AZURE_AI_SEARCH_RFI_INDEX_NAME, credential=credential)
            
            vector_query_1 = VectorizableTextQuery(text=combined_scope, k_nearest_neighbors=50, fields="scope_of_work_vectorized", exhaustive=True, weight=2)
            vector_query_2 = VectorizableTextQuery(text=combined_activities, k_nearest_neighbors=50, fields="required_activities_vectorized", exhaustive=True, weight=0.5)

            response_a = client_a.search(
                search_text=query,
                vector_queries=[vector_query_1, vector_query_2],
                search_fields=["client", "region", "industry"],
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                query_language="en",
                query_caption=QueryCaptionType.EXTRACTIVE,
                vector_filter_mode="postFilter",
                scoring_profile="weightedProfile",
                top=45,
                select="project_id",
            )
            
            return {doc["project_id"] for doc in response_a if "project_id" in doc}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            return await loop.run_in_executor(executor, rfi_search)
    
    async def search_rfp_index(project_ids):
        """Search RFP index asynchronously"""
        if not project_ids:
            return []
            
        loop = asyncio.get_event_loop()
        filter_expr = f"search.in(project_id, '{','.join(project_ids)}', ',')"
        
        def rfp_search():
            credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
            client_b = SearchClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, index_name=AZURE_AI_SEARCH_RFP_INDEX_NAME, credential=credential)
            
            vector_query_3 = VectorizableTextQuery(text=query, k_nearest_neighbors=50, fields="content_vector", query_rewrites="generative|count-5", exhaustive=True)

            response_b = client_b.search(
                search_text=user_question,
                filter=filter_expr,
                search_fields=["content", "section_name", "domain"],
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                query_language="en",
                query_caption=QueryCaptionType.EXTRACTIVE,
                vector_queries=[vector_query_3],
                vector_filter_mode="postFilter",
                top=15,
                select=["domain", "content", "section_name"],
            )
            
            return [doc.get("content", "") for doc in response_b if doc.get("content")]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            return await loop.run_in_executor(executor, rfp_search)
    
    # Step 1: Search RFI index
    project_ids = await search_rfi_index()
    print(f"✅ RFI search completed: {len(project_ids)} project IDs found")
    
    # Step 2: Search RFP index with project IDs
    results = await search_rfp_index(project_ids)
    print(f"✅ RFP search completed: {len(results)} content chunks found")
    
    return results


# =========================
# 📝 ASYNC FINAL RESPONSE (LLM) - ENHANCED FOR COMPONENTS
# =========================
async def final_response_async_enhanced(client, model: str, user_qn: str, chunk_data: Dict, context_chunks: list[str]) -> str:
    """
    Generate final response asynchronously using OpenAI API with enhanced component data.
    """
    print("🤖 Starting async final response generation with enhanced component format...")
    
    combined_text = "\n\n".join(context_chunks)
    if not combined_text.strip():
        return "No content found to summarize."
    
    print("The user question is:", user_qn)
    
    # Prepare component information for the prompt
    components_info = ""
    components = chunk_data.get("components", {})
    if components:
        components_info = "\n\nIDENTIFIED COMPONENTS:\n"
        for comp_code, comp_data in components.items():
            components_info += f"\n{comp_code} Component:\n"
            for field_name, field_value in comp_data.items():
                if field_value and field_value != "not mentioned in document":
                    components_info += f"- {field_name}: {field_value}\n"

    # Create detailed document context
    document_context = f"""
DOCUMENT METADATA:
- Project Name: {chunk_data.get('project_name', 'N/A')}
- Client: {chunk_data.get('client', 'N/A')}
- Industry: {chunk_data.get('industry', 'N/A')}
- Region: {chunk_data.get('region', 'N/A')}
- Prepared Date: {chunk_data.get('prepared_date', 'N/A')}
{components_info}
"""

    prompt = f"""
    ROLE: You are a precise assistant answering: {user_qn}.
    CONTEXT: Enhanced RFI document with component-specific analysis + retrieved RFP content.
    OBJECTIVE: Provide comprehensive, component-aware insights.

    FORMAT:
    - Give a detailed explanation addressing the question with component-specific details where relevant.
    - Include component-specific recommendations when applicable.
    - Highlight any component-related knowledge gaps.

    DOCUMENT CONTEXT:
    {document_context}

    INPUT QUESTION:
    {user_qn}

    RETRIEVED RFP CONTENT:
    {combined_text}

    TASK:
    1. Fully address the requirements stated in the uploaded documents with component-aware analysis.
    2. Leverage component-specific information when answering the question.
    3. Reference specific components (ELE, FND, AUX, CNT, EQP, TEL, PRT, STE, STR, MET, LN) when relevant.
    4. Provide structured insights that align with engineering/architectural proposal standards.
    5. Include component-specific technical details when addressing scope, activities, or requirements.
    """

    # Run OpenAI API call in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    
    def call_openai():
        response = client.chat.completions.create(
            model=model,
            messages=[ 
                {"role": "system", 
                "content": "You are an expert Proposal Engineer specializing in component-based RFI analysis. You understand electrical (ELE), foundations (FND), auxiliary (AUX), control (CNT), equipment (EQP), telecom (TEL), protection (PRT), site preparation (STE), structures (STR), metering (MET), and lines (LN) components in engineering projects."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, call_openai)
    
    print("✅ Enhanced final response generated successfully!")
    return result


# =========================
# 🚀 FULLY PARALLEL MULTI-FILE PIPELINE WITH ENHANCED CHUNKS
# =========================
async def process_multiple_files_parallel_enhanced(file_list: List[str]) -> List[Dict]:
    """
    Process multiple PDF files with FULL parallel processing and return individual enhanced chunks.
    
    Args:
        file_list (List[str]): List of file paths to process.
    
    Returns:
        List[Dict]: List of enhanced chunks (one per file)
    """
    print(f"🚀 Starting enhanced parallel processing of {len(file_list)} files...")
    
    # Process all files in parallel and create individual chunks
    chunk_tasks = [
        extract_rfi_chunk_from_file_parallel(file_path, os.path.basename(file_path)) 
        for file_path in file_list
    ]
    
    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
    
    # Filter successful results
    successful_chunks = [
        chunk for chunk in chunk_results
        if not isinstance(chunk, Exception) and chunk
    ]
    
    print(f"✅ Enhanced chunk processing completed: {len(successful_chunks)}/{len(file_list)} successful")
    
    return successful_chunks


# =========================
# 🚀 MAIN PIPELINE - ENHANCED COMPONENT FORMAT
# =========================
async def main():
    in_time = time.time()
    client = get_openai_client()
    model = AZURE_OPENAI_DEPLOYMENT_NAME

    input_qn = "what are the bell circuits in the SCADA systems ?"
    
    file_list = [
         r"C:/Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/t2.docx"
        # r"C:Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/sample_2.pdf",
        # r"C:Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/sample_3.pdf",
    ]

    # Phase 1: Extract enhanced chunks with component-specific fields
    print("🔥 Phase 1: Starting ENHANCED PARALLEL document processing...")
    processing_start = time.time()
    enhanced_chunks = await process_multiple_files_parallel_enhanced(file_list)
    processing_time = time.time() - processing_start
    print(f"⏱️ Enhanced document processing completed in: {processing_time:.2f} seconds")
    
    # Display enhanced chunks
    print("\n" + "=" * 100)
    print("ENHANCED CHUNKS WITH COMPONENT-SPECIFIC FIELDS")
    print("=" * 100)
    for i, chunk in enumerate(enhanced_chunks, 1):
        print(f"\nCHUNK {i}:")
        print(json.dumps(chunk, indent=2, ensure_ascii=False))
        print("\n" + "-" * 100)
    
    # Phase 2: Process the first chunk for search and response (or combine multiple chunks if needed)
    if enhanced_chunks:
        primary_chunk = enhanced_chunks[0]  # Use first chunk for demonstration
        
        # Phase 3: Section detection
        print("🔍 Phase 3: Starting section detection...")
        custom_prompt = """
        You are an expert section identifier.
        Sections: [Introduction, Scope of work, Required Activities, Risk and Assumptions, Checklist, References]
        Output only one section or 'Not mentioned clearly'.
        """
        
        async def get_section_info():
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return await loop.run_in_executor(
                    executor, 
                    find_section, client, model, input_qn, custom_prompt
                )
        
        section_name = await get_section_info()
        print(f"✅ Section detected: {section_name}")
        
        # Phase 4: Run Enhanced Azure Search
        print("🚀 Phase 4: Running Enhanced Azure Search...")
        search_start = time.time()
        index_response = await search_query_async_enhanced(input_qn, primary_chunk)
        search_time = time.time() - search_start
        print(f"⏱️ Enhanced Azure search completed in: {search_time:.2f} seconds")
        
        # Phase 5: Generate enhanced final response
        print("📝 Phase 5: Generating enhanced final response...")
        response_start = time.time()
        summary = await final_response_async_enhanced(client, model, input_qn, primary_chunk, index_response)
        response_time = time.time() - response_start
        print(f"⏱️ Enhanced final response generated in: {response_time:.2f} seconds")
        
        print("\n🔍 ENHANCED FINAL SUMMARY:\n", summary)
    
    # Phase 6: Save enhanced chunks to JSON file
    output_file = "enhanced_rfi_chunks.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_chunks, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Enhanced chunks saved to: {output_file}")
    
    out_time = time.time()
    total_time = out_time - in_time
    print(f"\n⏱️ ENHANCED PERFORMANCE BREAKDOWN:")
    print(f"📄 Enhanced Document Processing: {processing_time:.2f}s")
    if enhanced_chunks:
        print(f"🔍 Enhanced Azure Search: {search_time:.2f}s") 
        print(f"🤖 Enhanced Final Response: {response_time:.2f}s")
    print(f"🎯 Total Enhanced Pipeline Time: {total_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())