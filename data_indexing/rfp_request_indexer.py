# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents.indexes import SearchIndexClient
# from azure.search.documents.indexes.models import (
#     SearchIndex, SimpleField, SearchableField, SearchField, SearchFieldDataType, SemanticSearch, SemanticField, ComplexField,
#     VectorSearch, HnswAlgorithmConfiguration, SemanticPrioritizedFields,
#     ScoringProfile, TextWeights, SemanticConfiguration, VectorSearchProfile, AzureOpenAIVectorizer, AzureOpenAIVectorizerParameters
# )
# from config import (
#     AZURE_EMBEDDING_MODEL_NAME, AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_KEY,
#     AZURE_EMBEDDING_MODEL, AZURE_EMBEDDING_ENDPOINT, AZURE_EMBEDDING_API_KEY, AZURE_AI_SEARCH_RFI_INDEX_NAME
# )

# from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
# from opentelemetry import trace

# # Configure the logger
# logger = configure_logger()

# # Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
# tracer = trace.get_tracer(__name__)

# class RFPRequestIndexManager:
#     @tracer.start_as_current_span("RFPRequestIndexManager_init_fn")
#     def __init__(self):
#         #print("Azure embedding model:", AZURE_EMBEDDING_MODEL_NAME)
#         #print("Azure embedding:", AZURE_EMBEDDING_API_KEY)
#         self.credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
#         self.index_client = SearchIndexClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, credential=self.credential)
#         self.index_name = AZURE_AI_SEARCH_RFI_INDEX_NAME

#     @tracer.start_as_current_span("build_index_schema_fn")
#     def build_index_schema(self):
#         fields = [
#             SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, retrievable=True),
#             SimpleField(name="project_id", type=SearchFieldDataType.String, filterable=True, facetable=True, retrievable=True),
#             SearchField(
#                 name="scope_of_work_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="required_activities_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="pricing_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="disconnect_switches_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="transformer_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="transformer_foundations_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="equipment_support_foundations_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="HVAC_and_FAS_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="HADs_arrangements_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="control_design_packages_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="SCADA_infrastructure_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="bus_systems_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="circuit_breakers_and_disconnects_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="station_lan_networks_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="scada_and_transport_infrastructure_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="transformer_protection_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="breaker_protection_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="grading_and_roads_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="drainage_and_water_management_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="steel_and_station_structures_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="transformer_and_equipment_structures_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="new_metering_installations_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="existing_metering_retain_or_update_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="line_relocations_and_bypasses_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),
#             SearchField(
#                 name="line_rerouting_and_extensions_vectorized", 
#                 type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
#                 searchable=True, 
#                 vector_search_dimensions=3072, 
#                 vector_search_profile_name="myHnswProfile"
#             ),

#             SearchableField(name="project_name", type=SearchFieldDataType.String),
#             SearchableField(name="file_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="content_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="created_at", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="client", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="region", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="industry", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="field_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="voltage_class", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="contract_types", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="prepared_date", type=SearchFieldDataType.String, filterable=True, sortable=True),
#             SearchableField(name="pricing", type=SearchFieldDataType.String, filterable=True, facetable=True),
#             SearchableField(name="ComponentName", type=SearchFieldDataType.String, retrievable=True,filterable=True),
#             SearchableField(name="scope_of_work", type=SearchFieldDataType.String, retrievable=True,filterable=True),
#             SearchableField(name="required_activities", type=SearchFieldDataType.String, retrievable=True,filterable=True),
#             SearchableField(name="disconnect_switches", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="transformer", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="transformer_foundations", type=SearchFieldDataType.String, retrievable=True,filterable=True,facetable=True),
#             SearchableField(name="equipment_support_foundations", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="HVAC_and_FAS", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="HADs_arrangements", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="control_design_packages", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="SCADA_infrastructure", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="bus_systems", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="circuit_breakers_and_disconnects", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="station_lan_networks", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="scada_and_transport_infrastructure", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="transformer_protection", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="breaker_protection", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="grading_and_roads", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="drainage_and_water_management", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="steel_and_station_structures", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="transformer_and_equipment_structures", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="new_metering_installations", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="existing_metering_retain_or_update", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="line_relocations_and_bypasses", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#             SearchableField(name="line_rerouting_and_extensions", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
#         ]

#         openai_params = AzureOpenAIVectorizerParameters(
#             resource_url="https://ttdevopscaedevaif-rfprfi.openai.azure.com/",
#             deployment_name=AZURE_EMBEDDING_MODEL,
#             model_name=AZURE_EMBEDDING_MODEL_NAME,
#             api_key=AZURE_EMBEDDING_API_KEY
#         )

#         openai_vectorizer = AzureOpenAIVectorizer(
#             vectorizer_name="myVectorizer",
#             parameters=openai_params
#         )

#         vector_search = VectorSearch(
#             algorithms=[
#                 HnswAlgorithmConfiguration(
#                     name="myHnsw",
#                     kind="hnsw",
#                     parameters={"m": 4, "efConstruction": 400}
#                 )
#             ],
#             profiles=[
#                 VectorSearchProfile(
#                     name="myHnswProfile",
#                     algorithm_configuration_name="myHnsw",
#                     vectorizer_name="myVectorizer"
#                 )
#             ],
#             vectorizers=[openai_vectorizer]
#         )

#         semantic_config = SemanticConfiguration(
#             name="my-semantic-config",
#             prioritized_fields=SemanticPrioritizedFields(
#                 title_field=SemanticField(field_name="client"),
#                 keywords_fields=[SemanticField(field_name="region")],
#                 content_fields=[SemanticField(field_name="scope_of_work"), SemanticField(field_name="industry")],
#             )
#         )

#         scoring_profiles = [
#             ScoringProfile(
#                 name="weightedProfile",
#                 text_weights=TextWeights(weights={
#                     "client": 3.0,
#                     "region": 2.0,
#                     "industry": 1.0
#                 })
#             )
#         ]

#         semantic_search = SemanticSearch(
#             configurations=[semantic_config]
#         )

#         index = SearchIndex(
#             name=self.index_name,
#             fields=fields,
#             vector_search=vector_search,
#             scoring_profiles=scoring_profiles,
#             semantic_search=semantic_search
#         )
#         return index

#     @tracer.start_as_current_span("recreate_index_fn")
#     def recreate_index(self):
#         try:
#             self.index_client.delete_index(self.index_name)
#             #print(f"Deleted existing index '{self.index_name}'.")
#             log_custom_event(
#                  logger,
#                  f"Deleted existing index '{self.index_name}'.",
#                  level="info",
#                 )
#         except Exception as e:
#             #print(f"Index '{self.index_name}' does not exist or could not be deleted: {e}")
#             print()

#         index = self.build_index_schema()
#         self.index_client.create_index(index)
#         #print(f"✅ Index '{self.index_name}' created successfully.")
#         log_custom_event(
#                  logger,
#                  f"Index '{self.index_name}' created successfully.",
#                  level="info",
#                 )

# # Usage:
# manager = RFPRequestIndexManager()
# manager.recreate_index()





            # SearchField(
            #     name="cable_containments_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="buswork_and_insulators_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="electrical_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="power_transformers_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="switching_equipment_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="equipment_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="security_CCTV_and_Access_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="lighting_and_controls_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="auxiliary_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="phase_conductors_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="insulators_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="line_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="clearing_and_demolition_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="earthquakes_and_grading_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="site_preparation_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="base_course_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="pavement_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="access_roads_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="inlets_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="storm_pipes_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="drainage_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="trenches_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="manholes_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="undergrounds_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="oil_containments_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="vegetation_management_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="environment_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="concrete_foundations_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="steel_screw_piles_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="foundations_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="gantry_structures_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="platforms_and_racks_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="substation_structures_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="frame_and_floors_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="walls_and_openings_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="buildings_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="transformer_firewalls_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="impact_barriers_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="firewalls_and_barriers_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="monopoles_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="manholes_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="dead_end_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="line_structures_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="protection_relays_and_schemes_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="control_and_interlocking_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="protection_and_control_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="panels_and_cabinets_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="meters_and_recorders_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="metering_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="switching_routing_and_transport_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="teleprotection_terminals_and_cabinets_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),
            # SearchField(
            #     name="telecom_and_teleprotection_others_vectorized", 
            #     type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            #     searchable=True, 
            #     vector_search_dimensions=3072, 
            #     vector_search_profile_name="myHnswProfile"
            # ),





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
    AZURE_EMBEDDING_MODEL, AZURE_EMBEDDING_ENDPOINT, AZURE_EMBEDDING_API_KEY, AZURE_AI_SEARCH_RFI_INDEX_NAME
)

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace

# Configure the logger
logger = configure_logger()

# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)

class RFPRequestIndexManager:
    @tracer.start_as_current_span("RFPRequestIndexManager_init_fn")
    def __init__(self):
        #print("Azure embedding model:", AZURE_EMBEDDING_MODEL_NAME)
        #print("Azure embedding:", AZURE_EMBEDDING_API_KEY)
        self.credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
        self.index_client = SearchIndexClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, credential=self.credential)
        self.index_name = AZURE_AI_SEARCH_RFI_INDEX_NAME

    @tracer.start_as_current_span("build_index_schema_fn")
    def build_index_schema(self):
        fields = [
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, retrievable=True,filterable=True, facetable=True),
            SimpleField(name="project_id", type=SearchFieldDataType.String, filterable=True, facetable=True, retrievable=True),
            SearchField(
                name="scope_of_work_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="required_activities_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="pricing_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="electrical_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="equipment_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),

            SearchField(
                name="auxiliary_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="line_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="site_preparation_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="access_roads_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="drainage_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="undergrounds_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="environment_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="foundations_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="substation_structures_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="buildings_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="firewalls_and_barriers_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="line_structures_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="protection_and_control_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="metering_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(
                name="telecom_and_teleprotection_description_vectorized", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=3072, 
                vector_search_profile_name="myHnswProfile"
            ),


            SearchableField(name="project_name", type=SearchFieldDataType.String),
            SearchableField(name="file_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="content_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, facetable=True),
            SearchableField(name="client", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="region", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="location", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="state", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="country", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="industry", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="field_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="voltage", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="contract_types", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="Discipline", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="prepared_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True,facetable=True),
            SearchableField(name="pricing", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="SystemName", type=SearchFieldDataType.String, retrievable=True,filterable=True),
            SearchableField(name="scope_of_work", type=SearchFieldDataType.String, retrievable=True,filterable=True),
            SearchableField(name="required_activities", type=SearchFieldDataType.String, retrievable=True,filterable=True),
            SearchableField(name="cables_and_accessories", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="buswork_and_insulators", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="electrical_others", type=SearchFieldDataType.String, retrievable=True,filterable=True,facetable=True),
            SearchableField(name="electrical_description", type=SearchFieldDataType.String, retrievable=True,filterable=True,facetable=True),
            SearchableField(name="power_transformers", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="switching_equipment", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="equipment_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="equipment_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="station_service_and_main_lv_panel", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="lighting_and_controls", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="auxiliary_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="auxiliary_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="phase_conductors", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="insulators", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="line_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="line_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="clearing_and_demolition", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="fencing_and_Gates", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="site_preparation_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="site_preparation_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="subgrade", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            # SearchableField(name="base_course", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="pavement", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="access_roads_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="access_roads_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="culverts", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="storm_pipes", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="drainage_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="drainage_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="ductbanks", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="conduits", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="undergrounds_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="undergrounds_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="oil_containments", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="dust_and_noise", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="environment_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="environment_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="concrete_foundations", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="steel_screw_piles", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="foundations_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="foundations_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="equipment_and_support_structures", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="bus_support_structures", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="substation_structures_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="substation_structures_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="frame_and_floors", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="walls_and_openings", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="buildings_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="buildings_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="transformer_firewalls", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="blast_and_arc_barriers", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="firewalls_and_barriers_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="firewalls_and_barriers_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="monopoles", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="lattice_towers", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="line_structures_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="line_structures_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="protection_relays_and_schemes", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="scada_RTU_and_Automation", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="protection_and_control_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="protection_and_control_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="metering_cts_and_vts", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="meters_and_recorders", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="metering_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="metering_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="switching_routing_and_transport", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="radio_and_wan_access", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="telecom_and_teleprotection_others", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),
            SearchableField(name="telecom_and_teleprotection_description", type=SearchFieldDataType.String, retrievable=True,filterable=True, facetable=True),

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
                title_field=SemanticField(field_name="client"),
                keywords_fields=[SemanticField(field_name="region")],
                content_fields=[SemanticField(field_name="scope_of_work"), SemanticField(field_name="industry")],
            )
        )

        scoring_profiles = [
            ScoringProfile(
                name="recencyProfile",
                functions=[
                    FreshnessScoringFunction(
                        field_name="prepared_date",
                        boost=2.0,  # Adjust boost as needed
                        interpolation=ScoringFunctionInterpolation.LINEAR,
                        parameters=FreshnessScoringParameters(
                            boosting_duration="P365D"  # Boost for documents within the last 365 days
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

    @tracer.start_as_current_span("recreate_request_index_fn")
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
manager = RFPRequestIndexManager()
manager.recreate_index()
