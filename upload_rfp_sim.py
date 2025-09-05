# # from processors.extraction.text_extractor import TextExtractor
# # from processors.azure_processor import AzureDocumentProcessor
# # from processors.file_handler import FileHandler
# # from config import AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT

# # def get_file_bytes(file_path: str) -> bytes:
# #     with open(file_path, "rb") as f:
# #         return FileHandler.process_file(f)

# # from openai import AzureOpenAI

# # # Initialize the Azure OpenAI client
# # client = AzureOpenAI(
# #     api_key=AZURE_OPENAI_API_KEY,
# #     api_version=AZURE_OPENAI_API_VERSION,  # Adjust if your deployment uses another version
# #     azure_endpoint=AZURE_OPENAI_ENDPOINT
# # )

# # # Your model deployment name (check Azure portal)
# # DEPLOYMENT_NAME = AZURE_OPENAI_DEPLOYMENT_NAME

# # def find_section(input_text: str, custom_prompt: str) -> str:
# #     """
# #     Summarizes input_text based on a custom_prompt using Azure GPT-4o.
# #     """
# #     response = client.chat.completions.create(
# #         model=DEPLOYMENT_NAME,
# #         messages=[
# #             {"role": "system", "content": "You are a helpful assistant that finds the section."},
# #             {"role": "user", "content": f"{custom_prompt}\n\nText:\n{input_text}"}
# #         ],
# #         temperature=0.5,
# #         max_tokens=500
# #     )
# #     return response.choices[0].message.content.strip()



# # async def extract_rfi_metadata_from_file(file_path: str, file_name: str) -> tuple[dict, list]:
# #     """
# #     Extract RFI metadata from a file using the enhanced RFI extractor.
# #     """
# #     # Import inside function to avoid circular import
# #     from llm_metadata.rfi_extractor import RFIExtractor

# #     file_bytes = get_file_bytes(file_path)

# #     # Get Document Intelligence result
# #     azure_processor = AzureDocumentProcessor()
# #     result, client, operation_id = azure_processor.analyze_document(file_bytes, file_name)  # This returns the DI result object
# #     #print(result)
# #     text_extractor = TextExtractor()
# #     text_elements = text_extractor.extract_text(result)
# #     #print(text_elements)
# #     rfi_extractor = RFIExtractor()
# #     metadata = await rfi_extractor.extract_metadata_only(text_elements, azure_di_result=result)
# #     return metadata, text_elements


# # def search_query(user_question, query, scope_of_work, required_activities):
# #     from azure.core.credentials import AzureKeyCredential
# #     from azure.search.documents import SearchClient
# #     from config import AZURE_AI_SEARCH_ENDPOINT,AZURE_AI_SEARCH_KEY,AZURE_AI_SEARCH_RFI_INDEX_NAME,AZURE_AI_SEARCH_RFP_INDEX_NAME,AZURE_EMBEDDING_MODEL,AZURE_EMBEDDING_ENDPOINT,AZURE_EMBEDDING_API_KEY
# #     from azure.search.documents.models import VectorizableTextQuery, QueryType, QueryCaptionType, QueryAnswerType
# #     endpoint = AZURE_AI_SEARCH_ENDPOINT
# #     index_name = AZURE_AI_SEARCH_RFI_INDEX_NAME
# #     credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)

# #     search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

# #     client_b = SearchClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, index_name=AZURE_AI_SEARCH_RFP_INDEX_NAME, credential=credential)

# #     vector_query_1 = VectorizableTextQuery(
# #         text=scope_of_work,
# #         k_nearest_neighbors=50,
# #         fields="scope_of_work_vectorized",  
# #         exhaustive=True,  
# #         weight=2
# #     )
 
# #     vector_query_2 = VectorizableTextQuery(
# #             text=required_activities,
# #             k_nearest_neighbors=50,
# #             fields="required_activities_vectorized",  
# #             exhaustive=True,  
# #             weight=0.5
# #         )

# #     field_name = "project_id"
 
# #     response_a = search_client.search(
# #         search_text=query,
# #         vector_queries=[vector_query_1, vector_query_2],  
# #         search_fields=["client", "region","industry"],  # Boost these fields
# #         query_type=QueryType.SEMANTIC,
# #         semantic_configuration_name='my-semantic-config',
# #         query_language="en",
# #         query_caption=QueryCaptionType.EXTRACTIVE,
# #         vector_filter_mode="postFilter",
# #         scoring_profile="weightedProfile",            
# #         top=45,
# #         select="project_id",            
# #         include_total_count=False
# #     )

# #     values = set()
# #     for doc in response_a:
# #         if field_name in doc:
# #             values.add(doc[field_name])
# #         # print(doc)

# #     if not values:
# #         print(f"No values found for field '{field_name}' in index A results.")
# #     else:
# #         import json
# #         safe_values = [v.replace("'", "''") for v in values]  
# #         # values_list = ",".join(f"'{v}'" for v in safe_values)
# #         values_list = f"'{','.join(safe_values)}'"
# #         # print(values_list)
# #         filter_expr = f"search.in({field_name} , {values_list},  ',')"
# #         # print(filter_expr)
    
# #         vector_query_3 = VectorizableTextQuery(
# #             text=query,
# #             k_nearest_neighbors=50,
# #             fields="content_vector",  
# #             query_rewrites="generative|count-5" ,  
# #             exhaustive=True,
# #         )
    
# #         # 2. Query Index B using the filter to get top 15 chunks
# #         response_b = client_b.search(
# #             search_text=user_question,
# #             filter=filter_expr,
# #             search_fields=["content", "section_name","domain"],
# #             query_type=QueryType.SEMANTIC,
# #             semantic_configuration_name='my-semantic-config',
# #             query_language="en",
# #             query_caption=QueryCaptionType.EXTRACTIVE,
# #             vector_queries=[vector_query_3],
# #             vector_filter_mode="postFilter",
# #             top=15,
# #             # select=["chunk_id", "domain", "content_type", "content",'file_name',"section_name"]
# #             select=["domain", "content","section_name"]
# #         )
    
# #         # print(response_b)
# #         # print(f"Top 15 chunks from index B where {field_name} matches values from A:")
# #         chunk_texts = []
# #         for doc in response_b:
# #             # print(doc)
# #             content = doc.get('content', '')
# #             if content:
# #                 chunk_texts.append(content)
        
# #         return chunk_texts

# # # # Print results
# # # def print_results(results):
# # #     for result in results:
# # #         print(f"File: {result['file_name']}")
# # #         print(f"Section: {result['section_name']}")
# # #         print(f"Chunk ID: {result['chunk_id']}")
# # #         print(f"Score: {result['@search.score']}")
# # #         print(f"Content: {result['content']}")
# # #         print(f"Section No: {result['section_no']}")
# # #         print("-" * 40)
 
 
# # from azure.identity import DefaultAzureCredential
# # from openai import AzureOpenAI
# # import os
 
# # # Replace these with your Azure OpenAI details
# # AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# # AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# # AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
# # AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
 
 
# # client_openai = AzureOpenAI(
# #     api_key=AZURE_OPENAI_API_KEY,
# #     api_version=AZURE_OPENAI_API_VERSION,  
# #     azure_endpoint=AZURE_OPENAI_ENDPOINT
# # )

# # def final_response(user_qn, detailed_rfp_request, context_chunks):
# #     combined_text = "\n\n".join(context_chunks)
    
# #     if combined_text.strip(): #engineering proposal writer
# #         prompt = f""" ROLE: You are a precise, expert-level assistant specializing in answering the user question {user_qn} 
        
# #         and summarizing the results from the contexts {detailed_rfp_request} and {combined_text}.
    
# #         CONTEXT: You’ll receive several extracted chunks of technical documents. These may contain overlapping information, 
        
# #         but your goal is to deliver a cohesive summary.
        
# #         OBJECTIVE: Generate a **concise, actionable, and insightful summary** of the provided content.
        
# #         AUDIENCE: A technical manager who needs key insights quickly.
        
# #         STYLE & TONE: Use professional language. Present the information in **bullet-point format**, prioritized by importance.
        
# #         LENGTH CONSTRAINT: Limit the summary to **5–7 bullets**, each no more than 30 words.


        
# #         OUTPUT FORMAT:
# #         - **Summary (5–7 bullets)**: highlight the core insights, grouped logically.
# #         - **Recommendations (optional)**: if actionable items emerge, list 2–3 clearly.
# #         - **Knowledge Gaps (optional)**: mention any missing or ambiguous information.
        
# #         INPUT:
# #         {user_qn}
# #         {combined_text}
# #         {detailed_rfp_request}
        
# #         """
# #         response = client_openai.chat.completions.create(
# #             model=AZURE_OPENAI_DEPLOYMENT_NAME,
# #             messages=[
# #                 {"role": "system", "content": "You are a helpful assistant that summarizes technical documents."},
# #                 {"role": "user", "content": prompt}
# #             ],
# #             temperature=0.3,
# #             max_tokens=1000  
# #         )
   
# #         summary = response.choices[0].message.content
# #         print("\n🔍 Summary of the retrieved chunks:\n")
# #         print(summary)
# #     else:
# #         print("No content found to summarize.")     
 
 
 

# # async def main():
# #     # Initialize the Azure OpenAI client
# #     client = AzureOpenAI(
# #         api_key=AZURE_OPENAI_API_KEY,
# #         api_version=AZURE_OPENAI_API_VERSION,  # Adjust if your deployment uses another version
# #         azure_endpoint=AZURE_OPENAI_ENDPOINT
# #     )

# #     # Your model deployment name (check Azure portal)
# #     DEPLOYMENT_NAME = AZURE_OPENAI_DEPLOYMENT_NAME
# # #what is the scope of work of this document?
# #     input_qn = """
# #                 What is the risks involved in Cabling and Wiring?
# #                 """
# #     #file_path = r"C:\Users\jhagan.a\Documents\Tetratech\RPFRFIs\five_splitted\705-22295407.00-B&M_HONI RFP-Chatham SS-Chatham_Lakeshore App AI Elect Install Works 1\705-22295407.00-B&M_HONI RFP-Chatham SS-Chatham_Lakeshore App AI Elect Install Works.pdf"
# #     file_path = r"C:\Users\jhagan.a\Documents\Tetratech\RPFRFIs\five_splitted\705-22295407.00-B&M_HONI RFP-Chatham SS-Chatham_Lakeshore App AI Elect Install Works 1\705-22295407.00-B&M_HONI RFP-Chatham SS-Chatham_Lakeshore Instruct for Const.pdf"
# #     file_name = "705-22295407.00-B&M_HONI RFP-Chatham SS-Chatham_Lakeshore Instruct for Const"
# #     custom_prompt = """You are an expert section identifier for the question input provided. 
# #     The solution should be present in only one of the below sections :

# #     Section list
# #     [Introduction, Scope of work, Required Activities, Risk and Assumptions, Checklist, References]

# #     Instructions : 
    
    
# #     **If no clear information is found, use "Not mentioned clearly" **
    
# #     The output should be only one from the section list or "not mentioned clearly"
# #     """


# #     import asyncio

# #     section_name = find_section(input_qn, custom_prompt)

# #     # print(section_name)

# #     metadata, text_elements = await extract_rfi_metadata_from_file(file_path, file_name)
# #     # print(metadata)

# #     exclude_keys = {"scope_of_work", "required_activities"}
 
# #     # Convert JSON key-value pairs into a sentence excluding chosen keys
# #     metadata_str = "; ".join([f"{k} is {v}" for k, v in metadata.items() if k not in exclude_keys])

# #     scope_of_work = metadata['scope_of_work']
# #     required_activities = metadata['required_activities']
    
# #     # Combine with base string
# #     final_sentence = f"{section_name} Metadata -> {metadata_str}."

# #     # print(final_sentence)

# #     index_response = search_query(input_qn, final_sentence, scope_of_work, required_activities)

# #     # print(index_response)

# #     all_text = "\n\n".join([f"[{elem.get('role', 'unknown')}] {elem['content']}" for elem in text_elements])

# #     print("\n\nFinal Response:\n")
# #     final_response(input_qn, all_text, index_response)

# # if __name__ == "__main__":
# #     import asyncio
# #     asyncio.run(main())





# """
# Tetra Tech RFP/RFI Processing Pipeline
# --------------------------------------
# Enhanced version with full parallel processing for Azure Document Intelligence and metadata extraction.
# """

# # =========================
# # 📦 IMPORTS
# # =========================
# import os
# import asyncio
# import concurrent.futures
# from typing import Tuple, List, Dict, Any
# from openai import AzureOpenAI
# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
# from azure.search.documents.models import VectorizableTextQuery, QueryType, QueryCaptionType

# # Project imports (keep as provided)
# from processors.extraction.text_extractor import TextExtractor
# from processors.azure_processor import AzureDocumentProcessor
# from processors.file_handler import FileHandler
# import time
# from config import (
#     AZURE_OPENAI_DEPLOYMENT_NAME,
#     AZURE_OPENAI_API_KEY,
#     AZURE_OPENAI_API_VERSION,
#     AZURE_OPENAI_ENDPOINT,
#     AZURE_AI_SEARCH_ENDPOINT,
#     AZURE_AI_SEARCH_KEY,
#     AZURE_AI_SEARCH_RFI_INDEX_NAME,
#     AZURE_AI_SEARCH_RFP_INDEX_NAME,
# )
# from llm_metadata.rfi_extractor import RFIExtractor


# # =========================
# # 🔌 OPENAI CLIENT
# # =========================
# def get_openai_client():
#     return AzureOpenAI(
#         api_key=AZURE_OPENAI_API_KEY,
#         api_version=AZURE_OPENAI_API_VERSION,
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     )


# # =========================
# # 📂 FILE HANDLING
# # =========================
# def get_file_bytes(file_path: str) -> bytes:
#     with open(file_path, "rb") as f:
#         return FileHandler.process_file(f)


# # =========================
# # 📍 SECTION IDENTIFIER
# # =========================
# def find_section(client, model: str, input_text: str, custom_prompt: str) -> str:
#     response = client.chat.completions.create(
#         model=model,
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant that finds the section."},
#             {"role": "user", "content": f"{custom_prompt}\n\nText:\n{input_text}"},
#         ],
#         temperature=0.5,
#         max_tokens=500,
#     )
#     return response.choices[0].message.content.strip()


# # =========================
# # 🚀 PARALLEL AZURE DOCUMENT PROCESSING
# # =========================
# async def process_document_async(file_path: str, file_name: str) -> Tuple[Any, str, str]:
#     """
#     Process a single document through Azure Document Intelligence asynchronously.
    
#     Args:
#         file_path (str): Path to the file
#         file_name (str): Name of the file
    
#     Returns:
#         Tuple[Any, str, str]: (azure_result, file_path, file_name)
#     """
#     try:
#         file_bytes = get_file_bytes(file_path)
        
#         # Run Azure Document Intelligence in thread pool to avoid blocking
#         loop = asyncio.get_event_loop()
        
#         def process_doc():
#             azure_processor = AzureDocumentProcessor()
#             result, client, operation_id = azure_processor.analyze_document(file_bytes, file_name)
#             return result
        
#         # Use ThreadPoolExecutor for CPU-bound/IO-bound operations
#         with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
#             azure_result = await loop.run_in_executor(executor, process_doc)
        
#         print(f"✅ Document processing completed for: {file_name}")
#         return azure_result, file_path, file_name
    
#     except Exception as e:
#         print(f"❌ Error processing {file_name}: {str(e)}")
#         return None, file_path, file_name


# async def extract_text_and_metadata_async(azure_result: Any, file_path: str, file_name: str) -> Tuple[Dict, List, str]:
#     """
#     Extract text and metadata from processed Azure result asynchronously.
    
#     Args:
#         azure_result: Result from Azure Document Intelligence
#         file_path (str): Original file path
#         file_name (str): Original file name
    
#     Returns:
#         Tuple[Dict, List, str]: (metadata, text_elements, file_name)
#     """
#     try:
#         if azure_result is None:
#             print(f"⚠️ Skipping text extraction for {file_name} due to processing error")
#             return {}, [], file_name
        
#         # Run text extraction and metadata extraction in parallel
#         loop = asyncio.get_event_loop()
        
#         def extract_text():
#             text_extractor = TextExtractor()
#             return text_extractor.extract_text(azure_result)
        
#         # Extract text in thread pool
#         with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
#             text_elements = await loop.run_in_executor(executor, extract_text)
        
#         # Extract metadata (this is already async)
#         rfi_extractor = RFIExtractor()
#         metadata = await rfi_extractor.extract_metadata_only(text_elements, azure_di_result=azure_result)
        
#         print(f"✅ Text and metadata extraction completed for: {file_name}")
#         return metadata, text_elements, file_name
    
#     except Exception as e:
#         print(f"❌ Error extracting data from {file_name}: {str(e)}")
#         return {}, [], file_name


# # =========================
# # 📂 ENHANCED PARALLEL RFI METADATA EXTRACTION
# # =========================
# async def extract_rfi_metadata_from_file_parallel(file_path: str, file_name: str) -> Tuple[Dict, List]:
#     """
#     Extract RFI metadata from a single file with full parallel processing.
    
#     Args:
#         file_path (str): Path to the file
#         file_name (str): Name of the file
    
#     Returns:
#         Tuple[Dict, List]: (metadata, text_elements)
#     """
#     # Step 1: Process document through Azure Document Intelligence
#     azure_result, _, _ = await process_document_async(file_path, file_name)
    
#     # Step 2: Extract text and metadata in parallel
#     metadata, text_elements, _ = await extract_text_and_metadata_async(azure_result, file_path, file_name)
    
#     return metadata, text_elements


# # =========================
# # 🔍 AZURE COGNITIVE SEARCH
# # =========================
# def search_query(user_question, query, scope_of_work, required_activities):
#     credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)

#     client_a = SearchClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, index_name=AZURE_AI_SEARCH_RFI_INDEX_NAME, credential=credential)
#     client_b = SearchClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, index_name=AZURE_AI_SEARCH_RFP_INDEX_NAME, credential=credential)

#     # Step 1: RFI index
#     vector_query_1 = VectorizableTextQuery(text=scope_of_work, k_nearest_neighbors=50, fields="scope_of_work_vectorized", exhaustive=True, weight=2)
#     vector_query_2 = VectorizableTextQuery(text=required_activities, k_nearest_neighbors=50, fields="required_activities_vectorized", exhaustive=True, weight=0.5)

#     response_a = client_a.search(
#         search_text=query,
#         vector_queries=[vector_query_1, vector_query_2],
#         search_fields=["client", "region", "industry"],
#         query_type=QueryType.SEMANTIC,
#         semantic_configuration_name="my-semantic-config",
#         query_language="en",
#         query_caption=QueryCaptionType.EXTRACTIVE,
#         vector_filter_mode="postFilter",
#         scoring_profile="weightedProfile",
#         top=45,
#         select="project_id",
#     )

#     values = {doc["project_id"] for doc in response_a if "project_id" in doc}
#     if not values:
#         return []

#     filter_expr = f"search.in(project_id, '{','.join(values)}', ',')"

#     # Step 2: RFP index
#     vector_query_3 = VectorizableTextQuery(text=query, k_nearest_neighbors=50, fields="content_vector", query_rewrites="generative|count-5", exhaustive=True)

#     response_b = client_b.search(
#         search_text=user_question,
#         filter=filter_expr,
#         search_fields=["content", "section_name", "domain"],
#         query_type=QueryType.SEMANTIC,
#         semantic_configuration_name="my-semantic-config",
#         query_language="en",
#         query_caption=QueryCaptionType.EXTRACTIVE,
#         vector_queries=[vector_query_3],
#         vector_filter_mode="postFilter",
#         top=15,
#         select=["domain", "content", "section_name"],
#     )

#     return [doc.get("content", "") for doc in response_b if doc.get("content")]


# # =========================
# # 📝 FINAL RESPONSE (LLM)
# # =========================
# def final_response(client, model: str, user_qn: str, detailed_rfp_request: str, context_chunks: list[str]) -> str:
#     combined_text = "\n\n".join(context_chunks)
#     if not combined_text.strip():
#         return "No content found to summarize."
    
#     print("The user question is:", user_qn)

#     prompt = f"""
#     ROLE: You are a precise assistant answering: {user_qn}.
#     CONTEXT: Extracted chunks + RFP request.
#     OBJECTIVE: Concise, actionable insights.

#     FORMAT:
#     - Give a detailed explanation of the answer.
#     - Recommendations (optional).
#     - Knowledge gaps (optional).

#     INPUT:
#     {user_qn}
#     {combined_text}
#     {detailed_rfp_request}

#     TASK:

#     1. Fully addresses the requirements stated in the uploaded documents \
#     and answer for the specific question.
#     2. Leverage the style, structure, and content patterns from previous \
#         RFP responses when appropriate.
#     3. Adhere to any sectional structure or formatting commonly expected in \
#         architectural/engineering proposals (e.g., Executive Summary, Project Understanding, \
#         Approach and Methodology, Team Qualifications, Past Experience, etc.)
#     """

#     response = client.chat.completions.create(
#         model=model,
#         messages=[ 
#             {"role": "system", 
#             "content": "You are a Proposal Engineer specializing in analyzing and summarizing RFP (Request for Proposal) documents. You create concise, structured summaries to support senior technical managers in decision-making."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.3,
#         max_tokens=1000,
#     )

#     return response.choices[0].message.content.strip()


# # =========================
# # 🚀 FULLY PARALLEL MULTI-FILE PIPELINE
# # =========================
# async def process_multiple_files_parallel(file_list: List[str]) -> Tuple[Dict, List]:
#     """
#     Process multiple PDF files with FULL parallel processing.
#     - Azure Document Intelligence processes all files in parallel
#     - Text extraction and metadata extraction happen in parallel
#     - Maximum concurrency for optimal performance
    
#     Args:
#         file_list (List[str]): List of file paths to process.
    
#     Returns:
#         Tuple[Dict, List]: (merged_metadata, merged_text_elements)
#     """
#     print(f"🚀 Starting parallel processing of {len(file_list)} files...")
    
#     # Phase 1: Process all documents through Azure Document Intelligence in parallel
#     print("📄 Phase 1: Processing documents through Azure Document Intelligence...")
#     document_tasks = [
#         process_document_async(file_path, os.path.basename(file_path))
#         for file_path in file_list
#     ]
    
#     document_results = await asyncio.gather(*document_tasks, return_exceptions=True)
    
#     # Filter successful results
#     successful_results = [
#         (result, path, name) for result, path, name in document_results
#         if not isinstance(result, Exception) and result is not None
#     ]
    
#     print(f"✅ Document processing completed: {len(successful_results)}/{len(file_list)} successful")
    
#     # Phase 2: Extract text and metadata in parallel
#     print("🔍 Phase 2: Extracting text and metadata in parallel...")
#     extraction_tasks = [
#         extract_text_and_metadata_async(azure_result, file_path, file_name)
#         for azure_result, file_path, file_name in successful_results
#     ]
    
#     extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
    
#     # Phase 3: Merge results
#     print("🔄 Phase 3: Merging results...")
#     merged_metadata = {}
#     merged_text_elements = []
    
#     successful_extractions = 0
#     for result in extraction_results:
#         if isinstance(result, Exception):
#             print(f"⚠️ Extraction error: {result}")
#             continue
            
#         metadata, text_elements, file_name = result
#         successful_extractions += 1
        
#         # Merge metadata dictionaries
#         for k, v in metadata.items():
#             if k in merged_metadata:
#                 # If duplicate key, append values
#                 if isinstance(merged_metadata[k], list):
#                     if isinstance(v, list):
#                         merged_metadata[k].extend(v)
#                     else:
#                         merged_metadata[k].append(v)
#                 else:
#                     if isinstance(v, list):
#                         merged_metadata[k] = [merged_metadata[k]] + v
#                     else:
#                         merged_metadata[k] = [merged_metadata[k], v]
#             else:
#                 merged_metadata[k] = v

#         # Merge text elements
#         merged_text_elements.extend(text_elements)
#         print(f"✅ Merged data from: {file_name}")
    
#     print(f"🎉 Parallel processing completed: {successful_extractions}/{len(file_list)} files processed successfully")
#     return merged_metadata, merged_text_elements


# # =========================
# # 🚀 MAIN PIPELINE
# # =========================
# async def main():
#     in_time = time.time()
#     client = get_openai_client()
#     model = AZURE_OPENAI_DEPLOYMENT_NAME

#     input_qn = "what is tower type b2 and what is owner means in nalcor energy?"
    
#     file_list = [
#         r"C:/Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/705-25795001.00-NL Hydro RFP-LIL Eng Study-Purchasing T&C.pdf",
#         r"C:/Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/705-25795001.00-NL Hydro RFP-LIL Eng Study-Line Design Criteria.pdf"
#     ]

#     # Extract metadata with FULL parallel processing
#     print("🔥 Starting PARALLEL processing pipeline...")
#     metadata, text_elements = await process_multiple_files_parallel(file_list)
    
#     scope_of_work = metadata.get("scope_of_work", "")
#     required_activities = metadata.get("required_activities", "")

#     # Exclude some keys
#     exclude_keys = {"scope_of_work", "required_activities"}
#     metadata_str = "; ".join([f"{k} is {v}" for k, v in metadata.items() if k not in exclude_keys])

#     # Section detection
#     custom_prompt = """
#     You are an expert section identifier.
#     Sections: [Introduction, Scope of work, Required Activities, Risk and Assumptions, Checklist, References]
#     Output only one section or 'Not mentioned clearly'.
#     """
#     section_name = find_section(client, model, input_qn, custom_prompt)
#     final_sentence = f"{section_name} Metadata -> {metadata_str}."

#     # Azure Search
#     index_response = search_query(input_qn, final_sentence, scope_of_work, required_activities)
#     all_text = "\n\n".join([f"[{el.get('role','unknown')}] {el['content']}" for el in text_elements])

#     # Summarization
#     summary = final_response(client, model, input_qn, all_text, index_response)
#     print("\n🔍 Final Summary:\n", summary)
    
#     out_time = time.time()
#     print(f"⏱️ Total time taken: {out_time-in_time:.2f} seconds")


# if __name__ == "__main__":
#     asyncio.run(main())





import os
import asyncio
import concurrent.futures
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



def get_openai_client():
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_file_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return FileHandler.process_file(f)



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



async def extract_rfi_metadata_from_file_parallel(file_path: str, file_name: str) -> Tuple[Dict, List]:
    """
    Extract RFI metadata from a single file with full parallel processing.
    
    Args:
        file_path (str): Path to the file
        file_name (str): Name of the file
    
    Returns:
        Tuple[Dict, List]: (metadata, text_elements)
    """
    # Step 1: Process document through Azure Document Intelligence
    azure_result, _, _ = await process_document_async(file_path, file_name)
    
    # Step 2: Extract text and metadata in parallel
    metadata, text_elements, _ = await extract_text_and_metadata_async(azure_result, file_path, file_name)
    
    return metadata, text_elements



async def search_query_async(user_question, query, scope_of_work, required_activities):
    """
    Perform Azure Cognitive Search asynchronously with parallel RFI and RFP queries.
    """
    print("🔍 Starting async Azure Search...")
    
    async def search_rfi_index():
        """Search RFI index asynchronously"""
        loop = asyncio.get_event_loop()
        
        def rfi_search():
            credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
            client_a = SearchClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, index_name=AZURE_AI_SEARCH_RFI_INDEX_NAME, credential=credential)
            
            vector_query_1 = VectorizableTextQuery(text=scope_of_work, k_nearest_neighbors=50, fields="scope_of_work_vectorized", exhaustive=True, weight=2)
            vector_query_2 = VectorizableTextQuery(text=required_activities, k_nearest_neighbors=50, fields="required_activities_vectorized", exhaustive=True, weight=0.5)

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



async def final_response_async(client, model: str, user_qn: str, detailed_rfp_request: str, context_chunks: list[str]) -> str:
    """
    Generate final response asynchronously using OpenAI API.
    """
    print("🤖 Starting async final response generation...")
    
    combined_text = "\n\n".join(context_chunks)
    if not combined_text.strip():
        return "No content found to summarize."
    
    print("The user question is:", user_qn)

    prompt = f"""
    ROLE: You are a precise assistant answering: {user_qn}.
    CONTEXT: Extracted chunks + RFP request.
    OBJECTIVE: Concise, actionable insights.

    FORMAT:
    - Give a detailed explanation of the answer.
    - Recommendations (optional).
    - Knowledge gaps (optional).

    INPUT:
    {user_qn}
    {combined_text}
    {detailed_rfp_request}

    TASK:

    1. Fully addresses the requirements stated in the uploaded documents \
    and answer for the specific question.
    2. Leverage the style, structure, and content patterns from previous \
        RFP responses when appropriate.
    3. Adhere to any sectional structure or formatting commonly expected in \
        architectural/engineering proposals (e.g., Executive Summary, Project Understanding, \
        Approach and Methodology, Team Qualifications, Past Experience, etc.)
    """

    # Run OpenAI API call in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    
    def call_openai():
        response = client.chat.completions.create(
            model=model,
            messages=[ 
                {"role": "system", 
                "content": "You are a Proposal Engineer specializing in analyzing and summarizing RFP (Request for Proposal) documents. You create concise, structured summaries to support senior technical managers in decision-making."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, call_openai)
    
    print("✅ Final response generated successfully!")
    return result



async def process_multiple_files_parallel(file_list: List[str]) -> Tuple[Dict, List]:
    """
    Process multiple PDF files with FULL parallel processing.
    - Azure Document Intelligence processes all files in parallel
    - Text extraction and metadata extraction happen in parallel
    - Maximum concurrency for optimal performance
    
    Args:
        file_list (List[str]): List of file paths to process.
    
    Returns:
        Tuple[Dict, List]: (merged_metadata, merged_text_elements)
    """
    print(f"🚀 Starting parallel processing of {len(file_list)} files...")
    
    # Phase 1: Process all documents through Azure Document Intelligence in parallel
    print("📄 Phase 1: Processing documents through Azure Document Intelligence...")
    document_tasks = [
        process_document_async(file_path, os.path.basename(file_path))
        for file_path in file_list
    ]
    
    document_results = await asyncio.gather(*document_tasks, return_exceptions=True)
    
    # Filter successful results
    successful_results = [
        (result, path, name) for result, path, name in document_results
        if not isinstance(result, Exception) and result is not None
    ]
    
    print(f"✅ Document processing completed: {len(successful_results)}/{len(file_list)} successful")
    
    # Phase 2: Extract text and metadata in parallel
    print("🔍 Phase 2: Extracting text and metadata in parallel...")
    extraction_tasks = [
        extract_text_and_metadata_async(azure_result, file_path, file_name)
        for azure_result, file_path, file_name in successful_results
    ]
    
    extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
    
    # Phase 3: Merge results
    print("🔄 Phase 3: Merging results...")
    merged_metadata = {}
    merged_text_elements = []
    
    successful_extractions = 0
    for result in extraction_results:
        if isinstance(result, Exception):
            print(f"⚠️ Extraction error: {result}")
            continue
            
        metadata, text_elements, file_name = result
        successful_extractions += 1
        
        # Merge metadata dictionaries
        for k, v in metadata.items():
            if k in merged_metadata:
                # If duplicate key, append values
                if isinstance(merged_metadata[k], list):
                    if isinstance(v, list):
                        merged_metadata[k].extend(v)
                    else:
                        merged_metadata[k].append(v)
                else:
                    if isinstance(v, list):
                        merged_metadata[k] = [merged_metadata[k]] + v
                    else:
                        merged_metadata[k] = [merged_metadata[k], v]
            else:
                merged_metadata[k] = v

        # Merge text elements
        merged_text_elements.extend(text_elements)
        print(f"✅ Merged data from: {file_name}")
    
    print(f"🎉 Parallel processing completed: {successful_extractions}/{len(file_list)} files processed successfully")
    return merged_metadata, merged_text_elements


async def main():
    in_time = time.time()
    client = get_openai_client()
    model = AZURE_OPENAI_DEPLOYMENT_NAME

    input_qn = "what are the applicable codes and standards for outdoor lighting ?"
    
    file_list = [
        r"c:\Users\Raghav.purohit\Downloads\Mohawk_Tetra Tech_CEATI Proposal V1.docx"
        # r"C:/Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/sample_1.pdf",
        # r"C:Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/sample_2.pdf",
        # r"C:Users/Sarthak.hardas/Downloads/Tetratech Five splitted document/sample_3.pdf"
    ]

    # Phase 1: Extract metadata with FULL parallel processing
    print("🔥 Phase 1: Starting PARALLEL document processing...")
    processing_start = time.time()
    metadata, text_elements = await process_multiple_files_parallel(file_list)
    processing_time = time.time() - processing_start
    print(f"⏱️ Document processing completed in: {processing_time:.2f} seconds")
    
    # Phase 2: Prepare search parameters
    scope_of_work = metadata.get("scope_of_work", "")
    required_activities = metadata.get("required_activities", "")

    # Exclude some keys
    exclude_keys = {"scope_of_work", "required_activities"}
    metadata_str = "; ".join([f"{k} is {v}" for k, v in metadata.items() if k not in exclude_keys])

    # Phase 3: Section detection (can be parallelized with search if needed)
    print("🔍 Phase 3: Starting section detection...")
    custom_prompt = """
    You are an expert section identifier.
    Sections: [Introduction, Scope of work, Required Activities, Risk and Assumptions, Checklist, References]
    Output only one section or 'Not mentioned clearly'.
    """
    
    # Run section detection and search preparation in parallel
    async def get_section_info():
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor, 
                find_section, client, model, input_qn, custom_prompt
            )
    
    section_task = asyncio.create_task(get_section_info())
    
    # Phase 4: Prepare text data
    all_text = "\n\n".join([f"[{el.get('role','unknown')}] {el['content']}" for el in text_elements])
    
    # Wait for section detection
    section_name = await section_task
    final_sentence = f"{section_name} Metadata -> {metadata_str}."
    print(f"✅ Section detected: {section_name}")

    # Phase 5: Run Azure Search and Final Response in parallel
    print("🚀 Phase 5: Running Azure Search and preparing final response in parallel...")
    search_start = time.time()
    
    # Start both operations simultaneously
    search_task = asyncio.create_task(
        search_query_async(input_qn, final_sentence, scope_of_work, required_activities)
    )
    
    # Azure search completes first, then we can start final response
    index_response = await search_task
    search_time = time.time() - search_start
    print(f"⏱️ Azure search completed in: {search_time:.2f} seconds")
    
    # Phase 6: Generate final response
    print("📝 Phase 6: Generating final response...")
    response_start = time.time()
    summary = await final_response_async(client, model, input_qn, all_text, index_response)
    response_time = time.time() - response_start
    print(f"⏱️ Final response generated in: {response_time:.2f} seconds")
    
    print("\n🔍 Final Summary:\n", summary)
    
    out_time = time.time()
    total_time = out_time - in_time
    print(f"\n⏱️ PERFORMANCE BREAKDOWN:")
    print(f"📄 Document Processing: {processing_time:.2f}s")
    print(f"🔍 Azure Search: {search_time:.2f}s") 
    print(f"🤖 Final Response: {response_time:.2f}s")
    print(f"🎯 Total Pipeline Time: {total_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())