import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Union, Optional, Set
from azure.data.tables import TableServiceClient, TableEntity
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AzureTableMetadataHandler:
    """Enhanced handler for Azure Table Storage with metadata management for RFP/RFI documents and component data"""
    
    def __init__(self):
        """Initialize the Azure Table Storage handler"""
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not found")
        
        self.table_service_client = TableServiceClient.from_connection_string(self.connection_string)
        
        # Cache for RFP GUIDs to associate RFIs
        self._rfp_guid_cache = {}
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.max_retry_delay = 8.0  # seconds
    
    def _create_table_if_not_exists(self, table_name: str):
        """Create table if it doesn't exist"""
        table_client = self.table_service_client.get_table_client(table_name=table_name)
        try:
            print("creating the table - new table : ", table_name)
            table_client.create_table()  # Will succeed if table doesn't exist
            print(f"✅ Created new table: {table_name}")
        except Exception as e:
            if "TableAlreadyExists" in str(e):
                pass  # Ignore - table is already there
            else:
                print(f"❌ Failed to create table {table_name}: {e}")
                raise
        return table_client

    
    def _generate_rfp_guid(self, project_id: str) -> str:
        """Generate or retrieve consistent GUID for RFP project"""
        if project_id in self._rfp_guid_cache:
            return self._rfp_guid_cache[project_id]
        
        # Generate new GUID and cache it
        rfp_guid = str(uuid.uuid4())
        self._rfp_guid_cache[project_id] = rfp_guid
        return rfp_guid
    
    def _get_rfp_guid_for_rfi(self, project_id: str, table_name: str) -> Optional[str]:
        """Get the RFP GUID for associating an RFI document"""
        # First check cache
        if project_id in self._rfp_guid_cache:
            return self._rfp_guid_cache[project_id]
        
        # Query the table for existing RFP with same project_id
        try:
            table_client = self.table_service_client.get_table_client(table_name=table_name)
            filter_query = f"ProjectId eq '{project_id}' and DocumentType eq 'RFP'"
            entities = list(table_client.query_entities(filter_query))
            
            if entities:
                rfp_guid = entities[0].get('RFP_GUID')
                if rfp_guid:
                    self._rfp_guid_cache[project_id] = rfp_guid
                    return rfp_guid
        except Exception as e:
            print(f"Error querying for RFP GUID: {e}")
        
        # If no RFP found, create a new GUID (this RFI might come before its RFP)
        return self._generate_rfp_guid(project_id)
    
    def _sanitize_for_azure(self, value: Any) -> Any:
        """Sanitize individual values for Azure Table Storage"""
        if value is None:
            return ""
        elif isinstance(value, str):
            # Azure Table Storage has 64KB limit per property
            return value[:32000] if len(value) > 32000 else value
        elif isinstance(value, (list, dict)):
            return json.dumps(value, default=str)
        else:
            return str(value)
    
    def store_file_metadata(self, metadata: Dict[str, Any], table_name: str = "FileMetadata") -> Optional[str]:
        """
        Store file metadata with 6 key columns and rest as JSON metadata
        
        Args:
            metadata: Dictionary containing file metadata
            table_name: Name of the Azure table (default: "FileMetadata")
            
        Returns:
            Optional[str]: Entity key if successful, None if failed
        """
        try:
            # Create table client
            table_client = self._create_table_if_not_exists(table_name)
            
            # Define the 6 important columns to extract
            key_columns = {
                'project_name': metadata.get('project_name', ''),
                'client': metadata.get('client', ''),
                'region': metadata.get('region', ''),
                'industry': metadata.get('industry', ''),
                'document_type': metadata.get('document_type', ''),
                'project_id': metadata.get('project_id', '')
            }
            
            # Extract remaining fields for metadata JSON
            remaining_fields = {k: v for k, v in metadata.items() if k not in key_columns.keys()}
            
            # Create entity
            entity = TableEntity()
            
            # Set partition and row keys
            entity['PartitionKey'] = str(key_columns['project_id']) if key_columns['project_id'] else f"unknown_{datetime.utcnow().strftime('%Y%m%d')}"
            entity['RowKey'] = f"{str(uuid.uuid4())[:8]}_{datetime.utcnow().isoformat().replace(':', '_').replace('-', '_')}"
            
            # Add the 6 key columns
            entity['ProjectName'] = self._sanitize_for_azure(key_columns['project_name'])
            entity['Client'] = self._sanitize_for_azure(key_columns['client'])
            entity['Region'] = self._sanitize_for_azure(key_columns['region'])
            entity['Industry'] = self._sanitize_for_azure(key_columns['industry'])
            entity['DocumentType'] = self._sanitize_for_azure(key_columns['document_type'])
            entity['ProjectId'] = self._sanitize_for_azure(key_columns['project_id'])
            
            # Handle GUID assignment based on document type
            if key_columns['document_type'].upper() == 'RFP':
                # For RFP, generate new GUID
                rfp_guid = self._generate_rfp_guid(key_columns['project_id'])
                entity['RFP_GUID'] = rfp_guid
            elif key_columns['document_type'].upper() == 'RFI':
                # For RFI, associate with existing RFP or create new GUID
                rfp_guid = self._get_rfp_guid_for_rfi(key_columns['project_id'], table_name)
                entity['RFP_GUID'] = rfp_guid
            else:
                # For other document types, create unique GUID
                entity['RFP_GUID'] = str(uuid.uuid4())
            
            # Add metadata as JSON string
            entity['Metadata'] = json.dumps(remaining_fields, default=str, ensure_ascii=False)
            
            # Add system fields
            entity['CreatedAt'] = datetime.utcnow().isoformat()
            entity['UpdatedAt'] = datetime.utcnow().isoformat()
            
            # Store to Azure
            table_client.create_entity(entity=entity)
            entity_key = f"{entity['PartitionKey']}_{entity['RowKey']}"
            
            print(f"✅ Successfully stored metadata for {key_columns['document_type']} - {key_columns['project_name']}")
            print(f"   Entity Key: {entity_key}")
            print(f"   RFP GUID: {entity['RFP_GUID']}")
            
            return entity_key
            
        except Exception as e:
            print(f"❌ Error storing metadata: {str(e)}")
            return None
    
    def store_component_data(self, data: Dict[str, Any], table_name: str = "ComponentDataV2") -> List[str]:
        """
        Store component data by creating separate records for each component
        
        Args:
            data: Dictionary containing component data with structure shown in example
            table_name: Name of the Azure table (default: "ComponentData")
            
        Returns:
            List[str]: List of entity keys if successful, empty list if failed
        """
        try:
            # Create table client
            print("the table name is : ", table_name)
            table_client = self._create_table_if_not_exists(table_name)
            
            # Extract common fields - Updated to match new JSON structure
            common_fields = {
                'chunk_id': data.get('chunk_id', ''),
                'project_id': data.get('project_id', ''),
                'project_name': data.get('project_name', ''),
                'content_type': data.get('content_type', ''),
                'client': data.get('client', ''),
                'region': data.get('region', ''),
                'industry': data.get('industry', ''),
                'prepared_date': data.get('prepared_date', ''),
                'field_type': data.get('field_type', ''),
                'voltage': data.get('voltage', ''),
                'contract_types': data.get('contract_types', ''),
                'pricing': data.get('pricing', ''),
                'location': data.get('location', ''),
                'state': data.get('state', ''),
                'country': data.get('country', '')

            }
            
            # Get components data
            components = data.get('components', {})
            
            entity_keys = []
            
            # Process each component
            for component_name, component_data in components.items():
                # Create entity for this component
                entity = TableEntity()
                
                # Set partition and row keys
                entity['PartitionKey'] = str(common_fields['project_id']) if common_fields['project_id'] else f"unknown_{datetime.utcnow().strftime('%Y%m%d')}"
                
                # Create component-specific chunk_id and row key
                component_chunk_id = f"{common_fields['chunk_id']}_{component_name}"
                entity['RowKey'] = f"comp_{component_chunk_id}_{datetime.utcnow().isoformat().replace(':', '_').replace('-', '_')}"
                
                # Add component key columns - Updated fields
                entity['ChunkId'] = self._sanitize_for_azure(component_chunk_id)
                entity['ProjectId'] = self._sanitize_for_azure(common_fields['project_id'])
                entity['ProjectName'] = self._sanitize_for_azure(common_fields['project_name'])
                entity['ContentType'] = self._sanitize_for_azure(common_fields['content_type'])
                entity['Client'] = self._sanitize_for_azure(common_fields['client'])
                entity['Region'] = self._sanitize_for_azure(common_fields['region'])
                entity['Industry'] = self._sanitize_for_azure(common_fields['industry'])
                entity['PreparedDate'] = self._sanitize_for_azure(common_fields['prepared_date'])
                entity['FieldType'] = self._sanitize_for_azure(common_fields['field_type'])
                entity['Voltage'] = self._sanitize_for_azure(common_fields['voltage'])
                entity['ContractTypes'] = self._sanitize_for_azure(common_fields['contract_types'])
                entity['Pricing'] = self._sanitize_for_azure(common_fields['pricing'])
                entity['Location'] = self._sanitize_for_azure(common_fields['location'])
                entity['State'] = self._sanitize_for_azure(common_fields['state'])
                entity['Country'] = self._sanitize_for_azure(common_fields['country'])
                
                # Add component-specific fields
                entity['SystemName'] = self._sanitize_for_azure(component_name)
                entity['Discipline'] = self._sanitize_for_azure(data.get('discipline', ''))  # ADD THIS LINE
                entity['ScopeOfWork'] = self._sanitize_for_azure(component_data.get('scope_of_work', ''))
                entity['RequiredActivities'] = self._sanitize_for_azure(component_data.get('required_activities', ''))
                
                # Handle component-specific fields based on component type

                if component_name == 'electrical':
                    entity['cables_and_accessories'] = self._sanitize_for_azure(component_data.get('cables_and_accessories', ''))
                    entity['buswork_and_insulators'] = self._sanitize_for_azure(component_data.get('buswork_and_insulators', ''))
                    entity['electrical_others'] = self._sanitize_for_azure(component_data.get('electrical_others', ''))
                    entity['electrical_description'] = self._sanitize_for_azure(component_data.get('electrical_description', ''))

                elif component_name == 'equipment':
                    entity['power_transformers'] = self._sanitize_for_azure(component_data.get('power_transformers', ''))
                    entity['switching_equipment'] = self._sanitize_for_azure(component_data.get('switching_equipment', ''))
                    entity['equipment_others'] = self._sanitize_for_azure(component_data.get('equipment_others', ''))
                    entity['equipment_description'] = self._sanitize_for_azure(component_data.get('equipment_description', ''))

                elif component_name == 'auxiliary':
                    entity['station_service_and_main_lv_panel'] = self._sanitize_for_azure(component_data.get('station_service_and_main_lv_panel', ''))
                    entity['lighting_and_controls'] = self._sanitize_for_azure(component_data.get('lighting_and_controls', ''))
                    entity['auxiliary_others'] = self._sanitize_for_azure(component_data.get('auxiliary_others', ''))
                    entity['auxiliary_description'] = self._sanitize_for_azure(component_data.get('auxiliary_description', ''))

                elif component_name == 'line':
                    entity['phase_conductors'] = self._sanitize_for_azure(component_data.get('phase_conductors', ''))
                    entity['insulators'] = self._sanitize_for_azure(component_data.get('insulators', ''))
                    entity['line_others'] = self._sanitize_for_azure(component_data.get('line_others', ''))
                    entity['line_description'] = self._sanitize_for_azure(component_data.get('line_description', ''))

                elif component_name == 'site_preparation':
                    entity['clearing_and_demolition'] = self._sanitize_for_azure(component_data.get('clearing_and_demolition', ''))
                    entity['fencing_and_Gates'] = self._sanitize_for_azure(component_data.get('fencing_and_Gates', ''))
                    entity['site_preparation_others'] = self._sanitize_for_azure(component_data.get('site_preparation_others', ''))
                    entity['site_preparation_description'] = self._sanitize_for_azure(component_data.get('site_preparation_description', ''))

                elif component_name == 'access_roads':
                    entity['subgrade'] = self._sanitize_for_azure(component_data.get('subgrade', ''))
                    entity['pavement'] = self._sanitize_for_azure(component_data.get('pavement', ''))
                    entity['access_roads_others'] = self._sanitize_for_azure(component_data.get('access_roads_others', ''))
                    entity['access_roads_description'] = self._sanitize_for_azure(component_data.get('access_roads_description', ''))

                elif component_name == 'drainage':
                    entity['culverts'] = self._sanitize_for_azure(component_data.get('culverts', ''))
                    entity['storm_pipes'] = self._sanitize_for_azure(component_data.get('storm_pipes', ''))
                    entity['drainage_others'] = self._sanitize_for_azure(component_data.get('drainage_others', ''))
                    entity['drainage_description'] = self._sanitize_for_azure(component_data.get('drainage_description', ''))

                elif component_name == 'undergrounds':
                    entity['ductbanks'] = self._sanitize_for_azure(component_data.get('ductbanks', ''))
                    entity['conduits'] = self._sanitize_for_azure(component_data.get('conduits', ''))
                    entity['undergrounds_others'] = self._sanitize_for_azure(component_data.get('undergrounds_others', ''))
                    entity['undergrounds_description'] = self._sanitize_for_azure(component_data.get('undergrounds_description', ''))

                elif component_name == 'environment':
                    entity['oil_containments'] = self._sanitize_for_azure(component_data.get('oil_containments', ''))
                    entity['dust_and_noise'] = self._sanitize_for_azure(component_data.get('dust_and_noise', ''))
                    entity['environment_others'] = self._sanitize_for_azure(component_data.get('environment_others', ''))
                    entity['environment_description'] = self._sanitize_for_azure(component_data.get('environment_description', ''))

                elif component_name == 'foundations':
                    entity['concrete_foundations'] = self._sanitize_for_azure(component_data.get('concrete_foundations', ''))
                    entity['steel_screw_piles'] = self._sanitize_for_azure(component_data.get('steel_screw_piles', ''))
                    entity['foundations_others'] = self._sanitize_for_azure(component_data.get('foundations_others', ''))
                    entity['foundations_description'] = self._sanitize_for_azure(component_data.get('foundations_description', ''))

                elif component_name == 'substation_structures':
                    entity['equipment_and_support_structures'] = self._sanitize_for_azure(component_data.get('equipment_and_support_structures', ''))
                    entity['bus_support_structures'] = self._sanitize_for_azure(component_data.get('bus_support_structures', ''))
                    entity['substation_structures_others'] = self._sanitize_for_azure(component_data.get('substation_structures_others', ''))
                    entity['substation_structures_description'] = self._sanitize_for_azure(component_data.get('substation_structures_description', ''))

                elif component_name == 'buildings':
                    entity['frame_and_floors'] = self._sanitize_for_azure(component_data.get('frame_and_floors', ''))
                    entity['walls_and_openings'] = self._sanitize_for_azure(component_data.get('walls_and_openings', ''))
                    entity['buildings_others'] = self._sanitize_for_azure(component_data.get('buildings_others', ''))
                    entity['buildings_description'] = self._sanitize_for_azure(component_data.get('buildings_description', ''))

                elif component_name == 'firewalls_and_barriers':
                    entity['transformer_firewalls'] = self._sanitize_for_azure(component_data.get('transformer_firewalls', ''))
                    entity['blast_and_arc_barriers'] = self._sanitize_for_azure(component_data.get('blast_and_arc_barriers', ''))
                    entity['firewalls_and_barriers_others'] = self._sanitize_for_azure(component_data.get('firewalls_and_barriers_others', ''))
                    entity['firewalls_and_barriers_description'] = self._sanitize_for_azure(component_data.get('firewalls_and_barriers_description', ''))

                elif component_name == 'line_structures':
                    entity['monopoles'] = self._sanitize_for_azure(component_data.get('monopoles', ''))
                    entity['lattice_towers'] = self._sanitize_for_azure(component_data.get('lattice_towers', ''))
                    entity['line_structures_others'] = self._sanitize_for_azure(component_data.get('line_structures_others', ''))
                    entity['line_structures_description'] = self._sanitize_for_azure(component_data.get('line_structures_description', ''))

                elif component_name == 'protection_and_control':
                    entity['protection_relays_and_schemes'] = self._sanitize_for_azure(component_data.get('protection_relays_and_schemes', ''))
                    entity['scada_RTU_and_Automation'] = self._sanitize_for_azure(component_data.get('scada_RTU_and_Automation', ''))
                    entity['protection_and_control_others'] = self._sanitize_for_azure(component_data.get('protection_and_control_others', ''))
                    entity['protection_and_control_description'] = self._sanitize_for_azure(component_data.get('protection_and_control_description', ''))

                elif component_name == 'metering':
                    entity['metering_cts_and_vts'] = self._sanitize_for_azure(component_data.get('metering_cts_and_vts', ''))
                    entity['meters_and_recorders'] = self._sanitize_for_azure(component_data.get('meters_and_recorders', ''))
                    entity['metering_others'] = self._sanitize_for_azure(component_data.get('metering_others', ''))
                    entity['metering_description'] = self._sanitize_for_azure(component_data.get('metering_description', ''))

                elif component_name == 'telecom_and_teleprotection':
                    entity['switching_routing_and_transport'] = self._sanitize_for_azure(component_data.get('switching_routing_and_transport', ''))
                    entity['radio_and_wan_access'] = self._sanitize_for_azure(component_data.get('radio_and_wan_access', ''))
                    entity['telecom_and_teleprotection_others'] = self._sanitize_for_azure(component_data.get('telecom_and_teleprotection_others', ''))
                    entity['telecom_and_teleprotection_description'] = self._sanitize_for_azure(component_data.get('telecom_and_teleprotection_description', ''))

                # Store additional component data as JSON if any other fields exist
                other_fields = {k: v for k, v in component_data.items() if k not in [
                    'scope_of_work', 'required_activities', 
                    'cables_and_accessories', 'buswork_and_insulators', 'electrical_others','electrical_description', 
                    'power_transformers', 'switching_equipment', 'equipment_others', 'equipment_description', 
                    'station_service_and_main_lv_panel', 'lighting_and_controls', 'auxiliary_others', 'auxiliary_description',
                    'phase_conductors', 'insulators', 'line_others','line_description', 
                    'clearing_and_demolition', 'fencing_and_Gates', 'site_preparation_others','site_preparation_description', 
                    'subgrade', 'pavement', 'access_roads_others','access_roads_description', 
                    'culverts', 'storm_pipes', 'drainage_others','drainage_description', 
                    'ductbanks', 'conduits', 'undergrounds_others', 'undergrounds_description',
                    'oil_containments', 'dust_and_noise', 'environment_others','environment_description', 
                    'concrete_foundations', 'steel_screw_piles', 'foundations_others','foundations_description', 
                    'equipment_and_support_structures', 'bus_support_structures', 'substation_structures_others', 'substation_structures_description', 
                    'frame_and_floors', 'walls_and_openings', 'buildings_others','buildings_description', 
                    'transformer_firewalls', 'blast_and_arc_barriers', 'firewalls_and_barriers_others', 'firewalls_and_barriers_description', 
                    'monopoles', 'lattice_towers', 'line_structures_others','line_structures_description',
                    'protection_relays_and_schemes', 'scada_RTU_and_Automation', 'protection_and_control_others', 'protection_and_control_description', 
                    'metering_cts_and_vts', 'meters_and_recorders', 'metering_others','metering_description', 
                    'switching_routing_and_transport', 'radio_and_wan_access', 'telecom_and_teleprotection_others','telecom_and_teleprotection_description'
                ]}
                
                if other_fields:
                    entity['AdditionalData'] = json.dumps(other_fields, default=str, ensure_ascii=False)
                
                # Generate unique GUID for this component record
                entity['RecordGUID'] = str(uuid.uuid4())
                
                # Add system timestamp
                entity['SystemCreatedAt'] = datetime.utcnow().isoformat()
                entity['SystemUpdatedAt'] = datetime.utcnow().isoformat()
                
                # Store to Azure with retry logic
                for attempt in range(self.max_retries):
                    try:
                        table_client.create_entity(entity=entity)
                        entity_key = f"{entity['PartitionKey']}_{entity['RowKey']}"
                        entity_keys.append(entity_key)
                        print(f"✅ Successfully stored component {component_name} for project {common_fields['project_name']}")
                        print(f"   Entity Key: {entity_key}")
                        print(f"   Component Chunk ID: {component_chunk_id}")
                        print(f"   Record GUID: {entity['RecordGUID']}")
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt < self.max_retries - 1:
                            retry_delay = min(self.retry_delay * (2 ** attempt), self.max_retry_delay)
                            print(f"⚠️ Failed to store component {component_name} (attempt {attempt + 1}), retrying in {retry_delay}s...")
                            import time
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"❌ Failed to store component {component_name} after {self.max_retries} attempts: {str(e)}")
                            # Continue with next component instead of failing completely
            
            return entity_keys
            
        except Exception as e:
            print(f"❌ Error storing component data: {str(e)}")
            return []
    
    def get_components_by_project(self, project_id: str, table_name: str = "ComponentData") -> Dict[str, Any]:
        """
        Get all components for a specific project
        
        Args:
            project_id: Project ID to search for
            table_name: Table name to query
            
        Returns:
            Dictionary with project info and components
        """
        try:
            table_client = self.table_service_client.get_table_client(table_name=table_name)
            
            # Query for all components with this project_id
            filter_query = f"ProjectId eq '{project_id}'"
            entities = list(table_client.query_entities(filter_query))
            
            result = {
                'project_id': project_id,
                'project_info': None,
                'components': {}
            }
            
            for entity in entities:
                component_name = entity.get('SystemName', '')
                
                if not result['project_info']:
                    result['project_info'] = {
                        'project_name': entity.get('ProjectName', ''),
                        'client': entity.get('Client', ''),
                        'industry': entity.get('Industry', ''),
                        'region': entity.get('Region', ''),
                        'prepared_date': entity.get('PreparedDate', ''),
                        'content_type': entity.get('ContentType', ''),
                        'field_type': entity.get('FieldType', ''),
                        'voltage': entity.get('Voltage', ''),
                        'contract_types': entity.get('ContractTypes', ''),
                        'pricing': entity.get('Pricing', ''),
                        'location': entity.get('Location', ''),
                        'state': entity.get('State', ''),
                        'country': entity.get('Country', '')

                    }
                
                component_info = {
                    'chunk_id': entity.get('ChunkId', ''),
                    'component_name': component_name,
                    'discipline': entity.get('Discipline', ''),
                    'scope_of_work': entity.get('ScopeOfWork', ''),
                    'required_activities': entity.get('RequiredActivities', ''),
                    'record_guid': entity.get('RecordGUID', ''),
                    'created_at': entity.get('SystemCreatedAt', '')
                }
                
                # Add component-specific fields
                if component_name == 'electrical':
                    component_info.update({
                        'cables_and_accessories': entity.get('cables_and_accessories', ''),
                        'buswork_and_insulators': entity.get('buswork_and_insulators', ''),
                        'electrical_others': entity.get('electrical_others', '')
                    })
                elif component_name == 'equipment':
                    component_info.update({
                        'power_transformers': entity.get('power_transformers', ''),
                        'switching_equipment': entity.get('switching_equipment', ''),
                        'equipment_others': entity.get('equipment_others', '')
                    })
                elif component_name == 'auxiliary':
                    component_info.update({
                        'station_service_and_main_lv_panel': entity.get('station_service_and_main_lv_panel', ''),
                        'lighting_and_controls': entity.get('lighting_and_controls', ''),
                        'auxiliary_others': entity.get('auxiliary_others', '')
                    })
                elif component_name == 'line':
                    component_info.update({
                        'phase_conductors': entity.get('phase_conductors', ''),
                        'insulators': entity.get('insulators', ''),
                        'line_others': entity.get('line_others', '')
                    })
                elif component_name == 'site_preparation':
                    component_info.update({
                        'clearing_and_demolition': entity.get('clearing_and_demolition', ''),
                        'fencing_and_Gates': entity.get('fencing_and_Gates', ''),
                        'site_preparation_others': entity.get('site_preparation_others', '')
                    })
                elif component_name == 'access_roads':
                    component_info.update({
                        'subgrade': entity.get('subgrade', ''),
                        'pavement': entity.get('pavement', ''),
                        'access_roads_others': entity.get('access_roads_others', '')
                    })
                elif component_name == 'drainage':
                    component_info.update({
                        'culverts': entity.get('culverts', ''),
                        'storm_pipes': entity.get('storm_pipes', ''),
                        'drainage_others': entity.get('drainage_others', '')
                    })
                elif component_name == 'undergrounds':
                    component_info.update({
                        'ductbanks': entity.get('ductbanks', ''),
                        'conduits': entity.get('conduits', ''),
                        'undergrounds_others': entity.get('undergrounds_others', '')
                    })
                elif component_name == 'environment':
                    component_info.update({
                        'oil_containments': entity.get('oil_containments', ''),
                        'dust_and_noise': entity.get('dust_and_noise', ''),
                        'environment_others': entity.get('environment_others', '')
                    })
                elif component_name == 'foundations':
                    component_info.update({
                        'concrete_foundations': entity.get('concrete_foundations', ''),
                        'steel_screw_piles': entity.get('steel_screw_piles', ''),
                        'foundations_others': entity.get('foundations_others', '')
                    })
                elif component_name == 'substation_structures':
                    component_info.update({
                        'equipment_and_support_structures': entity.get('equipment_and_support_structures', ''),
                        'bus_support_structures': entity.get('bus_support_structures', ''),
                        'substation_structures_others': entity.get('substation_structures_others', '')
                    })
                elif component_name == 'buildings':
                    component_info.update({
                        'frame_and_floors': entity.get('frame_and_floors', ''),
                        'walls_and_openings': entity.get('walls_and_openings', ''),
                        'buildings_others': entity.get('buildings_others', '')
                    })
                elif component_name == 'firewalls_and_barriers':
                    component_info.update({
                        'transformer_firewalls': entity.get('transformer_firewalls', ''),
                        'blast_and_arc_barriers': entity.get('blast_and_arc_barriers', ''),
                        'firewalls_and_barriers_others': entity.get('firewalls_and_barriers_others', '')
                    })
                elif component_name == 'line_structures':
                    component_info.update({
                        'monopoles': entity.get('monopoles', ''),
                        'lattice_towers': entity.get('lattice_towers', ''),
                        'line_structures_others': entity.get('line_structures_others', '')
                    })
                elif component_name == 'protection_and_control':
                    component_info.update({
                        'protection_relays_and_schemes': entity.get('protection_relays_and_schemes', ''),
                        'scada_RTU_and_Automation': entity.get('scada_RTU_and_Automation', ''),
                        'protection_and_control_others': entity.get('protection_and_control_others', '')
                    })
                elif component_name == 'metering':
                    component_info.update({
                        'metering_cts_and_vts': entity.get('metering_cts_and_vts', ''),
                        'meters_and_recorders': entity.get('meters_and_recorders', ''),
                        'metering_others': entity.get('metering_others', '')
                    })
                elif component_name == 'telecom_and_teleprotection':
                    component_info.update({
                        'switching_routing_and_transport': entity.get('switching_routing_and_transport', ''),
                        'radio_and_wan_access': entity.get('radio_and_wan_access', ''),
                        'telecom_and_teleprotection_others': entity.get('telecom_and_teleprotection_others', '')
                    })

                # Add additional data if exists
                if entity.get('AdditionalData'):
                    try:
                        additional_data = json.loads(entity['AdditionalData'])
                        component_info['additional_data'] = additional_data
                    except:
                        pass
                
                result['components'][component_name] = component_info
            
            return result
            
        except Exception as e:
            print(f"❌ Error querying component data: {str(e)}")
            return {}
    
    def get_rfp_with_associated_rfis(self, project_id: str, table_name: str = "FileMetadata") -> Dict[str, Any]:
        """
        Get RFP and all associated RFIs for a project
        
        Args:
            project_id: Project ID to search for
            table_name: Table name to query
            
        Returns:
            Dictionary with RFP and associated RFIs
        """
        try:
            table_client = self.table_service_client.get_table_client(table_name=table_name)
            
            # Query for all documents with this project_id
            filter_query = f"ProjectId eq '{project_id}'"
            entities = list(table_client.query_entities(filter_query))
            
            result = {
                'project_id': project_id,
                'rfp': None,
                'rfis': [],
                'other_documents': []
            }
            
            for entity in entities:
                doc_type = entity.get('DocumentType', '').upper()
                
                # Parse metadata back to dict
                metadata = {}
                if entity.get('Metadata'):
                    try:
                        metadata = json.loads(entity['Metadata'])
                    except:
                        pass
                
                doc_info = {
                    'document_type': entity.get('DocumentType', ''),
                    'project_name': entity.get('ProjectName', ''),
                    'client': entity.get('Client', ''),
                    'region': entity.get('Region', ''),
                    'industry': entity.get('Industry', ''),
                    'rfp_guid': entity.get('RFP_GUID', ''),
                    'created_at': entity.get('CreatedAt', ''),
                    'metadata': metadata,
                    'entity_key': f"{entity['PartitionKey']}_{entity['RowKey']}"
                }
                
                if doc_type == 'RFP':
                    result['rfp'] = doc_info
                elif doc_type == 'RFI':
                    result['rfis'].append(doc_info)
                else:
                    result['other_documents'].append(doc_info)
            
            return result
            
        except Exception as e:
            print(f"❌ Error querying project data: {str(e)}")
            return {}
    
    def get_all_rfps_with_rfi_counts(self, table_name: str = "FileMetadata") -> List[Dict[str, Any]]:
        """
        Get all RFPs with count of associated RFIs
        
        Args:
            table_name: Table name to query
            
        Returns:
            List of RFP information with RFI counts
        """
        try:
            table_client = self.table_service_client.get_table_client(table_name=table_name)
            
            # Get all entities
            entities = list(table_client.list_entities())
            
            # Group by RFP_GUID
            rfp_groups = {}
            
            for entity in entities:
                rfp_guid = entity.get('RFP_GUID', '')
                doc_type = entity.get('DocumentType', '').upper()
                
                if rfp_guid not in rfp_groups:
                    rfp_groups[rfp_guid] = {
                        'rfp_guid': rfp_guid,
                        'rfp_info': None,
                        'rfi_count': 0,
                        'total_documents': 0
                    }
                
                rfp_groups[rfp_guid]['total_documents'] += 1
                
                if doc_type == 'RFP':
                    rfp_groups[rfp_guid]['rfp_info'] = {
                        'project_id': entity.get('ProjectId', ''),
                        'project_name': entity.get('ProjectName', ''),
                        'client': entity.get('Client', ''),
                        'region': entity.get('Region', ''),
                        'industry': entity.get('Industry', ''),
                        'created_at': entity.get('CreatedAt', '')
                    }
                elif doc_type == 'RFI':
                    rfp_groups[rfp_guid]['rfi_count'] += 1
            
            # Convert to list and filter out groups without RFP info
            result = []
            for group in rfp_groups.values():
                if group['rfp_info']:
                    result.append({
                        'rfp_guid': group['rfp_guid'],
                        'project_id': group['rfp_info']['project_id'],
                        'project_name': group['rfp_info']['project_name'],
                        'client': group['rfp_info']['client'],
                        'region': group['rfp_info']['region'],
                        'industry': group['rfp_info']['industry'],
                        'created_at': group['rfp_info']['created_at'],
                        'rfi_count': group['rfi_count'],
                        'total_documents': group['total_documents']
                    })
            
            return sorted(result, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            print(f"❌ Error getting RFP summary: {str(e)}")
            return []
    
    def query_by_criteria(self, table_name: str, **criteria) -> List[TableEntity]:
        """
        Query entities by various criteria
        
        Args:
            table_name: Table name to query
            **criteria: Query criteria (client, industry, document_type, etc.)
            
        Returns:
            List of matching entities
        """
        try:
            table_client = self.table_service_client.get_table_client(table_name=table_name)
            
            # Build filter query
            filters = []
            for key, value in criteria.items():
                if key.lower() == 'client':
                    filters.append(f"Client eq '{value}'")
                elif key.lower() == 'industry':
                    filters.append(f"Industry eq '{value}'")
                elif key.lower() == 'document_type':
                    filters.append(f"DocumentType eq '{value}'")
                elif key.lower() == 'project_id':
                    filters.append(f"ProjectId eq '{value}'")
                elif key.lower() == 'region':
                    filters.append(f"Region eq '{value}'")
                elif key.lower() == 'component_name':
                    filters.append(f"SystemName eq '{value}'")
                elif key.lower() == 'field_type':
                    filters.append(f"FieldType eq '{value}'")
                elif key.lower() == 'voltage':
                    filters.append(f"Voltage eq '{value}'")
                elif key.lower() == 'contract_types':
                    filters.append(f"ContractTypes eq '{value}'")
                elif key.lower() == 'location':
                    filters.append(f"Location eq '{value}'")
                elif key.lower() == 'state':
                    filters.append(f"State eq '{value}'")
                elif key.lower() == 'country':
                    filters.append(f"Country eq '{value}'")
                
            
            if filters:
                filter_query = " and ".join(filters)
                entities = list(table_client.query_entities(filter_query))
            else:
                entities = list(table_client.list_entities())
            
            return entities
            
        except Exception as e:
            print(f"❌ Error querying by criteria: {str(e)}")
            return []


# Example usage
# if __name__ == "__main__":
#     # Initialize handler
#     handler = AzureTableMetadataHandler()
    
#     """
#     **********************************************************************************************************
#     Example: Storing and retrieving RFP and RFI metadata Which is File Metadata
#     **********************************************************************************************************    
#     """
    
#     # # Sample metadata
#     # sample_metadata = {
#     #     'project_name': 'Merivale TS- Component Replacement',
#     #     'client': 'Hydro One Networks Inc.',
#     #     'region': 'Ottawa, Ontario, Canada',
#     #     'industry': 'Power & Energy',
#     #     'prepared_date': '2021-11-15',
#     #     'station_discipline': 'AUX',
#     #     'scope_of_work': 'The project involves replacing aging assets at Merivale TS, including 230kV GIS breakers, 230/115kV autotransformers, and 115kV oil circuit breakers, along with upgrades to disconnect switches, instrument transformers, strain insulators, protection, control, telecom facilities, and AC station service supply to meet Hydro One standards.',
#     #     'required_activities': 'Design, supply, install, and commission HVAC and Fire Alarm Systems, including heat detection and emergency ventilation, integrate with existing systems, review and approve contractor packages, prepare technical specifications, provide field support, issue as-built drawings, and oversee installation of overhead gantry and monorail cranes for new buildings.',
#     #     'project_id': '705-22318727.00',
#     #     'document_type': 'RFP',
#     #     'filename': '705-22318727.00-RFP-Merivale TS Sust&Dev-EN-ST-AUX-TIP.pdf'
#     # }
    
#     # # Store the RFP metadata
#     # print("🔄 Storing RFP metadata...")
#     # rfp_key = handler.store_file_metadata(sample_metadata, "FileMetadata")
    
#     # # Create a sample RFI for the same project
#     # rfi_metadata = sample_metadata.copy()
#     # rfi_metadata.update({
#     #     'document_type': 'RFI',
#     #     'filename': '705-22318727.00-RFI-001-Clarification.pdf',
#     #     'rfi_number': 'RFI-001',
#     #     'rfi_subject': 'Clarification on HVAC specifications'
#     # })
    
#     # print("\n🔄 Storing RFI metadata...")
#     # rfi_key = handler.store_file_metadata(rfi_metadata, "FileMetadata")
    
#     # # Get RFP with associated RFIs
#     # print("\n🔍 Retrieving RFP with associated RFIs...")
#     # project_data = handler.get_rfp_with_associated_rfis('705-22318727.00', "FileMetadata")
    
#     # print(f"\n📊 Project: {project_data.get('project_id')}")
#     # if project_data.get('rfp'):
#     #     print(f"   RFP: {project_data['rfp']['project_name']}")
#     #     print(f"   RFP GUID: {project_data['rfp']['rfp_guid']}")
#     # print(f"   RFIs: {len(project_data.get('rfis', []))}")
    
#     # # Get summary of all RFPs
#     # print("\n📈 Getting RFP summary...")
#     # rfp_summary = handler.get_all_rfps_with_rfi_counts("FileMetadata")
    
#     # for rfp in rfp_summary:
#     #     print(f"   Project: {rfp['project_name']} | RFIs: {rfp['rfi_count']} | Total Docs: {rfp['total_documents']}")
        
    
#     """
#     **********************************************************************************************************
#     Example: Storing and retrieving Component Data with new structure
#     **********************************************************************************************************
#     """
#     # Sample component data with new JSON structure
#     sample_component_data = {
#         "chunk_id": "f7993bb2-32f3-412a-a8f1-f59280379ba7",
#         "project_id": "705-22318727.00",
#         "project_name": "",
#         "content_type": "text",
#         "client": "Hydro One",
#         "region": "Merivale, Ontario",
#         "industry": "Power & Energy",
#         "prepared_date": "2021-11-01",
#         "field_type": "Brown Field",
#         "voltage_class": "Transmission (115–230 kV)",
#         "contract_types": "Not mentioned in the document",
#         "pricing": "Not mentioned in RFP",
#         "components": {
#             "ELE": {
#                 "scope_of_work": "The electrical scope involves the replacement of one transformer and installation of a new transformer at Merivale TS. It includes designing and installing transformer spill containment systems, oil-water separators, and associated piping, ensuring compliance with Hydro One standards.",
#                 "required_activities": "The electrical activities include collecting design data, preparing design drawings and reports, supporting permit applications, overseeing construction, participating in commissioning, and preparing as-built documentation. The installation of spill containment pits and oil-water separators is also required.",
#                 "disconnect_switches": "not mentioned in document",
#                 "transformer": "230/115kV transformers"
#             },
#             "STE": {
#                 "scope_of_work": "The site preparation scope includes grading and drainage modifications for the Merivale TS yard, installation of new roads, fences, and spill containment pits, and ensuring compliance with Hydro One standards for drainage and erosion control.",
#                 "required_activities": "Site preparation activities involve grading the station yard, modifying existing drainage systems, installing new roads and fences, and preparing engineering drawings for regulatory approvals. The work also includes ensuring erosion and sediment control during construction.",
#                 "grading_and_roads": "Grading for new and existing station yards, installation of new roads, and modification of existing roads to facilitate work from other disciplines.",
#                 "drainage_and_water_management": "Design and modification of station yard drainage systems, including spill containment pits and oil-water separators, ensuring compliance with Hydro One standards."
#             }
#         }
#     }
    
#     # Store component data
#     print("🔄 Storing component data with new structure...")
#     component_keys = handler.store_component_data(sample_component_data, "RPIRequestDataV4")
    
#     print(f"\n✅ Stored {len(component_keys)} component records")
#     for key in component_keys:
#         print(f"   - {key}")