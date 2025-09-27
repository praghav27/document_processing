from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField, SearchFieldDataType, SemanticSearch, SemanticField, ComplexField,
    VectorSearch, HnswAlgorithmConfiguration, SemanticPrioritizedFields,
    ScoringProfile, TextWeights, SemanticConfiguration, VectorSearchProfile, AzureOpenAIVectorizer, AzureOpenAIVectorizerParameters,
    ScoringFunction, ScoringFunctionAggregation,FreshnessScoringFunction,
    ScoringFunctionInterpolation, FreshnessScoringParameters
)
from config import (
    AZURE_EMBEDDING_MODEL_NAME, AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_RFP_INDEX_NAME, AZURE_EMBEDDING_MODEL, AZURE_EMBEDDING_ENDPOINT,
    AZURE_EMBEDDING_API_KEY, AZURE_OPENAI_API_VERSION
)
 
from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace
 
#Configure the logger
logger = configure_logger()
 
#Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)
 
class RFPResponseIndexManager:
    @tracer.start_as_current_span("RFPResponseIndexManager_init_fn")
    def __init__(self):
        # print("Azure embedding model:", AZURE_EMBEDDING_MODEL_NAME)
        # print("Azure embedding:", AZURE_EMBEDDING_API_KEY)
        self.credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
        self.index_client = SearchIndexClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, credential=self.credential)
        self.index_name = AZURE_AI_SEARCH_RFP_INDEX_NAME
 
    @tracer.start_as_current_span("build_index_schema_fn")
    def build_index_schema(self):
        fields = [
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, retrievable=True),
            SimpleField(name="project_id", type=SearchFieldDataType.String, filterable=True, facetable=True, retrievable=True),
            SimpleField(name="file_name", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="section_name", type=SearchFieldDataType.String, facetable=True),
            SimpleField(name="section_no", type=SearchFieldDataType.String, retrievable=True),
            SearchableField(name="domain", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="content_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="author", type=SearchFieldDataType.String, retrievable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="verbalized_content", type=SearchFieldDataType.String),
            SearchableField(name="rfp_id", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="myHnswProfile"
            ),
            ComplexField(name="metadata", fields=[
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, retrievable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, retrievable=True),
                SimpleField(name="word_count", type=SearchFieldDataType.Int32, retrievable=True),
                SimpleField(name="char_count", type=SearchFieldDataType.Int32, retrievable=True),
                ComplexField(name="llm_extracted_metadata", fields=[
                    SearchableField(name="project_title", type=SearchFieldDataType.String),
                    SimpleField(name="client_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SimpleField(name="vendor_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SimpleField(name="submission_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SimpleField(name="domain_category", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SimpleField(name="service_category", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SimpleField(name="revenue_range", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="region", type=SearchFieldDataType.String, filterable=True, facetable=True),
                    SimpleField(name="project_value", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="compliance_standard", type=SearchFieldDataType.String, retrievable=True),
                    SimpleField(name="equipments_used", type=SearchFieldDataType.String, retrievable=True)
                ]),
                ComplexField(name="table_info", fields=[
                    SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
                    SimpleField(name="row_count", type=SearchFieldDataType.Int32, retrievable=True),
                    SimpleField(name="column_count", type=SearchFieldDataType.Int32, retrievable=True),
                    SearchableField(name="csv_path", type=SearchFieldDataType.String),
                    ComplexField(name="section_info", fields=[
                        SearchableField(name="section_role", type=SearchFieldDataType.String),
                        SearchableField(name="section_content", type=SearchFieldDataType.String),
                        SimpleField(name="section_page", type=SearchFieldDataType.Int32),
                        SimpleField(name="section_paragraph_index", type=SearchFieldDataType.Double),
                        SimpleField(name="distance_from_section", type=SearchFieldDataType.Double)
                    ])
                ]),
                ComplexField(name="image_info", fields=[
                    SimpleField(name="page_number", type=SearchFieldDataType.Int32, retrievable=True),
                    SearchableField(name="image_type", type=SearchFieldDataType.String),
                    SearchableField(name="image_path", type=SearchFieldDataType.String, retrievable=True),
                    SimpleField(name="width", type=SearchFieldDataType.Int32, retrievable=True),
                    SimpleField(name="height", type=SearchFieldDataType.Int32, retrievable=True),
                    ComplexField(name="section_info", fields=[
                        SearchableField(name="section_role", type=SearchFieldDataType.String),
                        SearchableField(name="section_content", type=SearchFieldDataType.String),
                        SimpleField(name="section_page", type=SearchFieldDataType.Int32),
                        SimpleField(name="section_paragraph_index", type=SearchFieldDataType.Double),
                        SimpleField(name="distance_from_section", type=SearchFieldDataType.Double)
                    ])
                ])
            ])
        ]
 
        openai_params = AzureOpenAIVectorizerParameters(
            resource_url="https://ttdevopscaedevaif-rfprfi.openai.azure.com/",
            deployment_name=AZURE_EMBEDDING_MODEL,
            model_name=AZURE_EMBEDDING_MODEL_NAME,
            api_key=AZURE_EMBEDDING_API_KEY
        )
 
        openai_vectorizer = AzureOpenAIVectorizer(
            vectorizer_name="myVectorizer",
            parameters=openai_params
        )
 
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="myHnsw",
                    kind="hnsw",
                    parameters={"m": 4, "efConstruction": 400}
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw",
                    vectorizer_name="myVectorizer"
                )
            ],
            vectorizers=[openai_vectorizer]
        )
 
        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="metadata/llm_extracted_metadata/project_title"),
                keywords_fields=[SemanticField(field_name="metadata/llm_extracted_metadata/client_name")],
                content_fields=[SemanticField(field_name="content"), SemanticField(field_name="section_name")],
            )
        )
 
        scoring_profiles = [
            ScoringProfile(
                name="recencyProfile",
                functions=[
                    FreshnessScoringFunction(
                        field_name="metadata/llm_extracted_metadata/submission_date",
                        boost=2.0,  # Adjust boost as needed
                        interpolation=ScoringFunctionInterpolation.LINEAR,
                        parameters=FreshnessScoringParameters(
                            boosting_duration="P1095D"  # Boost for documents within the last 365 days
                        )
                    )
                ],
                function_aggregation=ScoringFunctionAggregation.MAXIMUM
            )
        ]
 
        semantic_search = SemanticSearch(
            configurations=[semantic_config]
        )
 
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            scoring_profiles=scoring_profiles,
            semantic_search=semantic_search
        )
        return index
 
    # @tracer.start_as_current_span("recreate_index_fn")
    # def recreate_index(self):
    #     try:
    #         self.index_client.delete_index(self.index_name)
    #         #print(f"Deleted existing index '{self.index_name}'.")
    #         log_custom_event(
    #              logger,
    #              f"Deleted existing index '{self.index_name}'.",
    #              level="info",
    #             )
    #     except Exception as e:
    #         #print(f"Index '{self.index_name}' does not exist or could not be deleted: {e}")
    #         print()
 
    #     index = self.build_index_schema()
    #     self.index_client.create_index(index)
    #     #print(f"✅ Index '{self.index_name}' created successfully.")
    #     log_custom_event(
    #              logger,
    #              f"Index '{self.index_name}' created successfully.",
    #              level="info",
    #             )
   
    @tracer.start_as_current_span("recreate_response_index_fn")
    def recreate_index(self):
        try:
            # Check if index already exists
            self.index_client.get_index(self.index_name)
            print(f"ℹ️ Index '{self.index_name}' already exists. Skipping creation.")
        except Exception as e:
            # Index does not exist → create it
            index = self.build_index_schema()
            self.index_client.create_index(index)
            print(f"✅ Index '{self.index_name}' created successfully.")
 
# Usage:
manager = RFPResponseIndexManager()
manager.recreate_index()