from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizableTextQuery
from config import (
    AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_INDEX_NAME
)

# Initialize SearchClient
credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
search_client = SearchClient(
    endpoint=AZURE_AI_SEARCH_ENDPOINT,
    index_name=AZURE_AI_SEARCH_INDEX_NAME,
    credential=credential
)
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType


# Define your natural language query
query_text = "what is the civic plan for this project?"

# Create a vectorizable text query (auto-embedding by Azure)
vector_query = VectorizableTextQuery(
    text=query_text,
    k_nearest_neighbors=50,
    fields="content_vector",  # Must match your index
    query_rewrites="generative|count-5" ,    # or "generative" if your index supports it
    exhaustive=True,  # Use exhaustive search for better accuracy
)

# Execute the search
results = search_client.search(
    search_text=query_text,
    vector_queries=[vector_query],
    filter="file_name eq 'chester'",
    select=["file_name", "content"],
    semantic_configuration_name='my-semantic-config',
    query_type=QueryType.SEMANTIC,
    query_rewrites="generative|count-3",
    query_language="en",
    query_caption=QueryCaptionType.EXTRACTIVE,
    query_answer=QueryAnswerType.EXTRACTIVE,
    top=3,
    include_total_count=False
)

# Print results
def print_results(results):
    for result in results:
        print(f"File: {result['file_name']}")
        print(f"Score: {result['@search.score']}")
        print(f"Content: {result['content']}")
        print("-" * 40)

print_results(results)
