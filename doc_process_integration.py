import time
import asyncio
import logging
from collections import defaultdict

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery, QueryType, QueryCaptionType
#from src.app_dao.pdf_dao import PDFStatusDAO,PDFFileStatusSchema
from upload_rfp_sim3 import (process_multiple_files_parallel_enhanced,
                             get_openai_client,
                             query_azure_table_async, COMPONENT_SEARCH_FIELDS)
from config import (AZURE_OPENAI_DEPLOYMENT_NAME, #src.document_process.
                    AZURE_STORAGE_CONNECTION_STRING, 
                    AZURE_AI_SEARCH_KEY,
                    AZURE_AI_SEARCH_ENDPOINT,
                    AZURE_AI_SEARCH_RFI_INDEX_NAME,
                    AZURE_AI_SEARCH_RFP_INDEX_NAME
                    )


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


connection_string = AZURE_STORAGE_CONNECTION_STRING
table_name = "ComponentData"
RFI_TOP_K=10
RFP_TOP_K=20

# COMPONENT_NAME_MAP = {
#     "ELE": "Electrical",
#     "FND": "Foundations",
#     "AUX": "Auxiliary",
#     "CNT": "Control",
#     "EQP": "Equipment",
#     "TEL": "Telecom",
#     "PRT": "Protection",
#     "STE": "Site Preparation",
#     "STR": "Structures",
#     "MET": "Metering",
#     "LN":  "Lines (Transmission Lines)",
# }

discipline_system_map = {
    "electrical_arrangements" : ["electrical", "equipment", "auxiliary", "line"],
    "civil" : ["site_preparation", "access_roads", "drainage","undergrounds","environment"],
    "structure" : ["foundations", "sub_station_structures", "buildings", "firewalls_and_barriers","line_structures"],
    "PCMTT" : ["protection_and_control","metering","telecom_and_teleprotection"]
}

class RFPDocProcess:
    client = get_openai_client()
    model = AZURE_OPENAI_DEPLOYMENT_NAME

    @staticmethod
    async def get_file_details(file_list: list = []):
        loop = asyncio.get_running_loop()
 
        logger.info(" Phase 1: Starting ENHANCED PARALLEL document processing...")
        processing_start = loop.time()
 
        enhanced_chunks = await process_multiple_files_parallel_enhanced(file_list=file_list)
 
        processing_time = loop.time() - processing_start
        logger.info(f" Enhanced document processing completed in: {processing_time:.2f} seconds")
 
        return enhanced_chunks

    # @staticmethod
    # def map_component_keys(components: dict) -> dict:
    #     """Replace component short keys with descriptive names"""
    #     mapped = {}
    #     for key, value in components.items():
    #         readable_key = COMPONENT_NAME_MAP.get(key, key)  # default to original if not found
    #         mapped[readable_key] = value
    #     return mapped
    
    def get_discipline_key_by_value(value: str) -> str:
        """
        Return the discipline key from discipline_system_map given a value in its value list.
        If not found, returns None.
        """
        for key, values in discipline_system_map.items():
            if value in values:
                return key
        return None


    @staticmethod
    async def save_chunks_to_table_by_file(enhanced_chunks: list[dict]):
        """Process chunks and return file-wise component to chunk ID mapping"""
        if not enhanced_chunks:
            logger.info("No chunks to process")
            return {}

        logger.info(f"Phase 2: Processing {len(enhanced_chunks)} chunks for Azure Search...")
        
        # Group chunks by file
        file_chunks = defaultdict(list)
        for chunk in enhanced_chunks:
            file_name = chunk.get('file_name', 'Unknown')
            file_chunks[file_name].append(chunk)
        
        # Store results by file
        file_wise_results = {}
        consolidated_project_ids = set()
        # Process each file's chunks
        for file_name, chunks in file_chunks.items():
            logger.info(f"\n=== Processing File: {file_name} ===")
            logger.info(f"   Number of chunks: {len(chunks)}")
            
            file_component_mapping = {}
            
            # Process each chunk in this file
            for chunk_idx, chunk in enumerate(chunks):
                logger.info(f"\n Processing Chunk {chunk_idx + 1}/{len(chunks)} from {file_name}...")
                logger.info(f"   Project: {chunk.get('project_name', 'Unknown')}")
                

                # Extract base filters from current chunk
                base_filters = {
                    "Client": chunk.get("client", ""),
                    "Industry": chunk.get("industry", ""),
                    "Region": chunk.get("region", ""),
                    "FieldType": chunk.get("field_type", ""),
                    "VoltageClass": chunk.get("voltage_class", ""),
                    "ContractTypes": chunk.get("contract_types", ""),
                }
                
                # Run queries for each component in this chunk
                async def query_for_component(component_name: str):
                    comp_filters = base_filters.copy()
                    comp_filters["ComponentName"] = component_name
                    chunk_ids = await query_azure_table_async(connection_string, table_name, comp_filters)
                    return {component_name: chunk_ids}
                
                # Get components for this chunk
                component_names = list(chunk.get("components", {}).keys())
                if not component_names:
                    logger.info(f"    No components found in chunk {chunk_idx + 1}, skipping...")
                    continue
                    
                logger.info(f"    Found components: {component_names}")
                
                # Run parallel queries for all components in this chunk
                tasks = [query_for_component(comp) for comp in component_names]
                results = await asyncio.gather(*tasks)
                
                # Merge component results for this chunk
                chunk_component_mapping = {}
                for result in results:
                    chunk_component_mapping.update(result)
                
                logger.info(f"    Component to ChunkId mapping for chunk {chunk_idx + 1}:")
                for comp, chunk_ids in chunk_component_mapping.items():
                    logger.info(f"      {comp}: {len(chunk_ids)} chunk IDs")
                    
                    # Add to file-level mapping (combine chunk IDs if component appears multiple times)
                    if comp in file_component_mapping:
                        file_component_mapping[comp].extend(chunk_ids)
                    else:
                        file_component_mapping[comp] = chunk_ids.copy()
            
            # Remove duplicates from file-level component mapping
            for comp in file_component_mapping:
                file_component_mapping[comp] = list(set(file_component_mapping[comp]))
            
            file_wise_results[file_name] = file_component_mapping
            
            logger.info(f"\n=== File Summary for {file_name} ===")
            for comp, chunk_ids in file_component_mapping.items():
                logger.info(f"   {comp}: {len(chunk_ids)} unique chunk IDs")
        
        return file_wise_results

    @staticmethod
    async def search_rfi_index_by_file(
        file_list: list = []
    ):
        # Step 1: Extract file details
        enhanced_chunks = await RFPDocProcess.get_file_details(
            file_list=file_list
        )

        logger.info(f"Enhanced_Chunks: {len(enhanced_chunks)} total chunks")
        
        # Step 2: Save chunks to table & get file-wise mapping of component -> chunk IDs
        file_wise_component_mapping = await RFPDocProcess.save_chunks_to_table_by_file(
            enhanced_chunks=enhanced_chunks
        )
        logger.info(f"File-wise Component Chunk Mapping: {file_wise_component_mapping}")

        logger.info("\nStarting async Azure Search (file-wise component-aware with field-specific vector queries)...")

        credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)

        # Create a mapping of component name to actual chunk data (grouped by file)
        file_component_data = defaultdict(lambda: defaultdict(list))
        for chunk in enhanced_chunks:
            file_name = chunk.get('file_name', 'Unknown')
            components = chunk.get("components", {})
            for comp_name, comp_data in components.items():
                file_component_data[file_name][comp_name].append(comp_data)

        file_metadata = {}
        required_activities_data = {}
        for chunk in enhanced_chunks:
            file_name = chunk.get('file_name', 'Unknown')
            if file_name not in file_metadata:  # only take first chunk's metadata for file
                file_metadata[file_name] = {
                    "project_name": chunk.get("project_name", "N/A"),
                    "client": chunk.get("client", "N/A"),
                    "industry": chunk.get("industry", "N/A"),
                    "region": chunk.get("region", "N/A"),
                    "field_type": chunk.get("field_type", "N/A"),
                    "voltage_class": chunk.get("voltage_class", "N/A"),
                    "contract_types": chunk.get("contract_types", "N/A"),
                    "pricing": chunk.get("pricing", "N/A"),
                }
                required_activities_data[file_name] = chunk.get("components", "N/A")

        async def search_component_for_file(file_name: str, comp_name: str, chunk_ids: list):
            allowed_fields = COMPONENT_SEARCH_FIELDS.get(comp_name, [])
            if not allowed_fields or not chunk_ids:
                logger.info(f"Skipping {file_name} -> {comp_name}: no allowed fields or chunk IDs")
                return set()

            comp_data_list = file_component_data[file_name][comp_name]
            if not comp_data_list:
                logger.info(f"No component data found for {file_name} -> {comp_name}")
                return set()

            def run_request_search():
                try:
                    client = SearchClient(
                        endpoint=AZURE_AI_SEARCH_ENDPOINT,
                        index_name=AZURE_AI_SEARCH_RFI_INDEX_NAME,
                        credential=credential,
                    )
                    filter_expr = f"search.in(chunk_id, '{','.join(chunk_ids)}', ',')"
                
                    vector_queries = []
                    for field in allowed_fields:
                        if (field=="pricing"):
                            weight=0.5
                        else:
                            weight=1.0
                        field_texts = [
                            comp_data.get(field, "")
                            for comp_data in comp_data_list
                            if comp_data.get(field, "")
                            and comp_data.get(field, "").strip()
                            and comp_data.get(field) != "not mentioned in document"
                        ]

                        if field_texts:
                            combined_field_text = " ".join(field_texts)
                            vector_query = VectorizableTextQuery(
                                text=combined_field_text,
                                k_nearest_neighbors=30,
                                fields=f"{field}_vectorized",
                                exhaustive=True,
                                weight=weight
                            )
                            vector_queries.append(vector_query)
                            logger.info(f"Created vector query for {file_name} -> {comp_name}.{field}: {combined_field_text[:100]}...")
                        else:
                            logger.info(f"No valid text found for {file_name} -> {comp_name}.{field}")

                    if not vector_queries:
                        logger.info(f"No vector queries created for {file_name} -> {comp_name}")
                        return []

                    response = client.search(
                        search_text="",
                        vector_queries=vector_queries,
                        filter=filter_expr,
                        query_type=QueryType.SEMANTIC,
                        semantic_configuration_name="my-semantic-config",
                        query_caption=QueryCaptionType.EXTRACTIVE,
                        vector_filter_mode="postFilter",
                        top=RFI_TOP_K,
                        select=["chunk_id", "project_id"]
                    )

                    logger.info(f"RFI_SEARCH:{response}")
                    return [doc for doc in response]

                except Exception as e:
                    logger.error(f"Error during search for {file_name} -> {comp_name}: {e}")
                    return []

            loop = asyncio.get_event_loop()
            request_results = await loop.run_in_executor(None, run_request_search)

            logger.info(f"Search results for {file_name} -> {comp_name}: {len(request_results)} results")
            
            project_ids = {doc["project_id"] for doc in request_results if "project_id" in doc}
            logger.info(f"Search results for {file_name} -> {comp_name} -> Project IDs: {project_ids}")

            return project_ids

        # Step 3: Run searches for all files and components
        file_wise_results = {}
        consolidated_project_ids = set()

        for file_name, component_mapping in file_wise_component_mapping.items():
            logger.info(f"\n=== Starting search for file: {file_name} ===")
            try:
            # Create tasks for all components in this file
                tasks = [
                    search_component_for_file(file_name, comp, ids) 
                    for comp, ids in component_mapping.items()
                ]
                
                # Run searches concurrently for all components in this file
                component_results = await asyncio.gather(*tasks)
                
                # Combine results for this file
                file_project_ids = set().union(*component_results) if component_results else set()
                
                # Add to consolidated
                consolidated_project_ids.update(file_project_ids)

                file_wise_results[file_name] = {
                    'knowledge_base_filters': list(file_project_ids),
                    'client_requirements': RFPDocProcess.map_component_keys(required_activities_data.get(file_name, {})),
                    'rfi_document_metadata': file_metadata.get(file_name, {})
                }

          

                # Save status in DB

                logger.info(f"=== File {file_name} Summary ===")
                logger.info(f"   Total unique project IDs: {len(file_project_ids)}")
                logger.info(f"   Project IDs: {file_project_ids}")
                for comp, proj_ids in zip(component_mapping.keys(), component_results):
                    logger.info(f"   {comp}: {len(proj_ids)} project IDs -> {proj_ids}")

            except Exception as e:
                logger.error(f"Error processing file {file_name}: {e}")

        logger.info(f"Filewise Results:{file_wise_results}")
        # Final return with consolidated key
        return file_wise_results
            

    @staticmethod
    async def search_rfp_index(input_qn:str = "",knowledge_base_filters:list[str]=[]):
        try:
            client = SearchClient(
                endpoint=AZURE_AI_SEARCH_ENDPOINT,
                index_name=AZURE_AI_SEARCH_RFP_INDEX_NAME,
                credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY),
            )

            # Build filter expression
            filter_expr = f"search.in(project_id, '{','.join(knowledge_base_filters)}', ',')"

            # Build vector query
            vector_queries = [
                VectorizableTextQuery(
                    text=input_qn,
                    k_nearest_neighbors=30,
                    fields="content_vector",
                    exhaustive=True
                )
            ]

            # Execute search
            response = client.search(
                search_text=input_qn,  
                filter=filter_expr,
                vector_queries=vector_queries,
                search_fields=["content", "section_name", "domain"],
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                # query_language="en",
                query_caption=QueryCaptionType.EXTRACTIVE,
                top=RFP_TOP_K,
                select=["domain", "content", "section_name"]
            )

            results = [doc for doc in response]

            logger.info(f"RFP_INDEX:{results}")
            return results

        except Exception as e:
            logger.error(f"Error in RFP Search: {e}")
            return []
        


async def main():
    file_list = [r"C:\Users\jhagan.a\Downloads\705-22295407.00-B&M_HONI RFP-Chatham SS.docx"]

    file_wise_results = await RFPDocProcess.search_rfi_index_by_file(file_list=file_list)

    logger.info("FINAL FILE-WISE RESULTS")

    logger.info(f"Filewise Results:{file_wise_results}")

    logger.info("CALLING RFP INDEX")
    response = await RFPDocProcess.search_rfp_index(input_qn="What is the scope of the project",knowledge_base_filters=["705-22295407.00"])
    logger.info(f"RFP INDEX Results:{response}")

if __name__ == "__main__":
    asyncio.run(main())