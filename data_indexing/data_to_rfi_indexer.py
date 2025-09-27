import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
 
from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event
from opentelemetry import trace
 
# Configure the logger
logger = configure_logger()
 
# Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
tracer = trace.get_tracer(__name__)
 
from config import (
    AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_RFI_INDEX_NAME,
    AZURE_EMBEDDING_MODEL,
    AZURE_EMBEDDING_API_KEY,
    AZURE_EMBEDDING_ENDPOINT
)
 
class AzureSearchRFPRequestUploader:
    @tracer.start_as_current_span("AzureSearchRFPRequestUploader_init_fn")
    def __init__(self):
        load_dotenv()
 
        # Azure clients
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
    @tracer.start_as_current_span("get_embedding_fn")
    def get_embedding(self, text: str, model: str = None) -> List[float]:
        """Generate embeddings for given text."""
        if model is None:
            model = AZURE_EMBEDDING_MODEL
        try:
            response = self.openai_client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f" Error generating embedding: {e}")
            return [0.0] * 3072
   
    def parse_date(self, date_str: str) -> str:
        if not date_str:
            return None
        normalized = date_str.replace(" ", "T")
        try:
            dt = datetime.fromisoformat(normalized)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%d/%m/%Y",
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue
            print(f" Could not parse date: {date_str}")
            date_str=None
            return date_str
   
    def created_at_parse_date(self, date_str: str) -> str:
        """Parse various date formats and return ISO format datetime string with timezone."""
        if not date_str:
            return None
        # Handle datetime strings that already have 'T' separator
        normalized = date_str.replace(" ", "T")
        # Try parsing as ISO format first
        try:
            dt = datetime.fromisoformat(normalized)
            # Ensure timezone is set
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            pass
        # Try various common date formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",      # 2025-09-25 16:31:09.436486
            "%Y-%m-%dT%H:%M:%S.%f",      # 2025-09-25T16:31:09.436486
            "%Y-%m-%d %H:%M:%S",         # 2025-09-25 16:31:09
            "%Y-%m-%dT%H:%M:%S",         # 2025-09-25T16:31:09
            "%Y/%m/%d %H:%M:%S",         # 2025/09/25 16:31:09
            "%d-%m-%Y %H:%M:%S",         # 25-09-2025 16:31:09
            "%d/%m/%Y %H:%M:%S",         # 25/09/2025 16:31:09
            "%Y-%m-%d",                  # 2025-09-25
            "%d-%m-%Y",                  # 25-09-2025
            "%Y/%m/%d",                  # 2025/09/25
            "%d/%m/%Y",                  # 25/09/2025
            "%Y-%m",                     # 2025-09
            "%m-%Y",                     # 09-2025
            "%Y",                        # 2025
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Always set timezone to UTC if not present
                dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                continue
        # If all parsing attempts failed, log the issue but don't return None
        print(f"Warning: Could not parse date '{date_str}', using current time as fallback")
        log_custom_event(
            logger,
            f"Could not parse date: {date_str}",
            level="warning",
        )
        # Return None to indicate parsing failed - let the caller handle the fallback
        return None
 
    @tracer.start_as_current_span("expand_chunk_by_components_fn")
    def expand_chunk_by_components(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Expand a single chunk into multiple documents, one per discipline inside 'components'.
        Vectorize all fields listed in SUMMARY_VECTORIZE_FIELDS for each component and store their string values.
        All other fields are stored as strings only.
        """
        SUMMARY_VECTORIZE_FIELDS = {
            "electrical":                  ["pricing", "scope_of_work", "required_activities", "electrical_description"],
            "equipment":                   ["pricing", "scope_of_work", "required_activities", "equipment_description"],
            "auxiliary":                   ["pricing", "scope_of_work", "required_activities", "auxiliary_description"],
            "line":                        ["pricing", "scope_of_work", "required_activities", "line_description"],
            "site_preparation":            ["pricing", "scope_of_work", "required_activities", "site_preparation_description"],
            "access_roads":                ["pricing", "scope_of_work", "required_activities", "access_roads_description"],
            "drainage":                    ["pricing", "scope_of_work", "required_activities", "drainage_description"],
            "undergrounds":                ["pricing", "scope_of_work", "required_activities", "undergrounds_description"],
            "environment":                 ["pricing", "scope_of_work", "required_activities", "environment_description"],
            "foundations":                 ["pricing", "scope_of_work", "required_activities", "foundations_description"],
            "substation_structures":       ["pricing", "scope_of_work", "required_activities", "substation_structures_description"],
            "buildings":                   ["pricing", "scope_of_work", "required_activities", "buildings_description"],
            "firewalls_and_barriers":      ["pricing", "scope_of_work", "required_activities", "firewalls_and_barriers_description"],
            "line_structures":             ["pricing", "scope_of_work", "required_activities", "line_structures_description"],
            "protection_and_control":      ["pricing", "scope_of_work", "required_activities", "protection_and_control_description"],
            "metering":                    ["pricing", "scope_of_work", "required_activities", "metering_description"],
            "telecom_and_teleprotection":  ["pricing", "scope_of_work", "required_activities", "telecom_and_teleprotection_description"],
        }
 
        created_at = chunk.get("created_at")
        prepared_date = chunk.get("prepared_date")  
        print("created_at:",created_at)
        print("prepared_date:",prepared_date)
        if created_at:
            created_at = self.created_at_parse_date(created_at)
        if prepared_date:
            prepared_date = self.parse_date(prepared_date)
        documents = []
        base_fields = {
            "chunk_id": chunk.get("chunk_id"),
            "project_id": chunk.get("project_id"),
            "file_name": chunk.get("file_name"),
            "content_type": chunk.get("content_type"),
            "created_at": self.created_at_parse_date(datetime.now().isoformat()),
            "project_name": chunk.get("project_name"),
            "client": chunk.get("client"),
            "industry": chunk.get("industry"),
            "region": chunk.get("region"),
            "prepared_date": prepared_date,
            "field_type": chunk.get("field_type"),
            "voltage": chunk.get("voltage"),
            "contract_types": chunk.get("contract_types"),
            "pricing": chunk.get("pricing"),
            "location": chunk.get("location"),
            "state": chunk.get("state"),
            "country": chunk.get("country"),
        }
        components = chunk.get("components", {})
        if not components:
            print(f" No components found in chunk {chunk.get('chunk_id')}")
            log_custom_event(
                logger,
                f"No components found in chunk {chunk.get('chunk_id')}",
                level="warning",
            )
            return []
        discipline_system_map = {
            "electrical_arrangements" : ["electrical", "equipment", "auxiliary", "line"],
            "civil" : ["site_preparation", "access_roads", "drainage","undergrounds","environment"],
            "structure" : ["foundations", "substation_structures", "buildings", "firewalls_and_barriers","line_structures"],
            "PCMTT" : ["protection_and_control","metering","telecom_and_teleprotection"]
        }
        for discipline, comp_data in components.items():
            doc = dict(base_fields)
            matched_category = ""
            for category, keys in discipline_system_map.items():
                if discipline.lower() in [k.lower() for k in keys]:
                    matched_category = category
                    break
            doc["Discipline"] = matched_category
            doc["SystemName"] = discipline
 
            # Store all fields as plain strings
            for f, val in comp_data.items():
                doc[f] = val
 
            # Vectorize only the fields listed in SUMMARY_VECTORIZE_FIELDS for this component
            vectorize_fields = SUMMARY_VECTORIZE_FIELDS.get(discipline.lower(), [])
            for f in vectorize_fields:
                val = comp_data.get(f, "")
                vec_field = f"{f}_vectorized"
                if val:
                    doc[vec_field] = self.get_embedding(val)
                else:
                    doc[vec_field] = [0.0] * 3072
 
            # unique chunk_id per discipline
            doc["chunk_id"] = f"{chunk.get('chunk_id')}_{discipline}"
            documents.append(doc)
        with open("expand_chunk_by_component", "a") as outfile:
            json.dump(documents, outfile)
            outfile.write("\n")
        return documents
 
 
    @tracer.start_as_current_span("upload_documents_in_batches_fn")
    def upload_documents_in_batches(self, documents: List[Dict[str, Any]], batch_size: int = 100):
        """Upload documents to Azure Search in LARGER batches for better performance"""
        total_docs = len(documents)
        successful, failed = 0, 0
        # Optimize batch size for parallel processing
        optimized_batch_size = min(batch_size, max(50, total_docs // 5)) if total_docs > 0 else batch_size
 
        print(f" Optimized batch upload: {total_docs} documents in batches of {optimized_batch_size}")
        log_custom_event(
                 logger,
                 f"Optimized batch upload: {total_docs} documents in batches of {optimized_batch_size}",
                 level="info",
                )
 
        for i in range(0, total_docs, optimized_batch_size):
            batch = documents[i:i+optimized_batch_size]
            batch_num = (i // optimized_batch_size) + 1
            total_batches = (total_docs + optimized_batch_size - 1) // optimized_batch_size
 
            print(f" Uploading batch {batch_num}/{total_batches} ({len(batch)} documents)...")
           
            try:
                result = self.search_client.upload_documents(documents=batch)
                batch_success = sum(1 for r in result if r.succeeded)
                batch_fail = len(batch) - batch_success
                successful += batch_success
                failed += batch_fail
                print(f" Batch {batch_num} completed: {batch_success} successful, {batch_fail} failed")
            except Exception as e:
                print(f" Error uploading batch {batch_num}: {e}")
                failed += len(batch)
        print(f"\n Upload summary: {successful} successful, {failed} failed (total {total_docs})")
        log_custom_event(
                 logger,
                 f"\n Upload summary: {successful} successful, {failed} failed (total {total_docs})",
                 level="info",
                )
        return successful, failed
   
    @tracer.start_as_current_span("upload_chunks_from_dict_fn")
    def upload_chunks_from_dict(self, chunk_data: Dict[str, Any]):
        """Enhanced batch upload with better performance"""
        chunks = chunk_data.get("chunks", [])
        if not chunks:
            print(" No chunks found in input data")
            log_custom_event(
                 logger,
                 "No chunks found in input data",
                 level="warning",
                )
            return
        print(f" Processing {len(chunks)} chunks for batch upload...")
        log_custom_event(
                 logger,
                 f" Processing {len(chunks)} chunks for batch upload...",
                 level="info",
                )
        documents = []
        # Process chunks in parallel batches
        for chunk in chunks:
            expanded_docs = self.expand_chunk_by_components(chunk)
            print(f" Expanded chunk {chunk.get('chunk_id')} into {len(expanded_docs)} documents")
            documents.extend(expanded_docs)
        with open("expanded_doc", "a") as outfile:
            json.dump(documents, outfile)
            outfile.write("\n")
        print(f" Expanded {len(chunks)} chunks into {len(documents)} component documents")
        log_custom_event(
                 logger,
                 f"Expanded {len(chunks)} chunks into {len(documents)} component documents",
                 level="info",
                )
        # Upload with optimized batch processing
        if documents:
            self.upload_documents_in_batches(documents, batch_size=100)  # Larger batches
            # print("Uploading commented out for testing")
        else:
            print(" No valid documents to upload")
            log_custom_event(
                 logger,
                 "No valid documents to upload",
                 level="warning",
                )
           
    @tracer.start_as_current_span("load_and_upload_chunks_fn")        
    def load_and_upload_chunks(self, json_file_path: str):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f" Loaded {json_file_path}")
        except Exception as e:
            print(f" Error loading JSON: {e}")
            return
        self.upload_chunks_from_dict(data)
 
    @tracer.start_as_current_span("upload_direct_data_fn")
    def upload_direct_data(self, data: Dict[str, Any]):
        print(" Uploading direct data...")
        self.upload_chunks_from_dict(data)
 
    @tracer.start_as_current_span("test_single_document_upload_fn")
    def test_single_document_upload(self, chunk: Dict[str, Any]):
        doc = self.transform_chunk_to_document(chunk)
        print(" Document preview:")
        for k, v in doc.items():
            if isinstance(v, list) and len(v) == 3072:
                print(f"  {k}: [embedding length {len(v)}]")
                log_custom_event(
                 logger,
                 f"  {k}: [embedding length {len(v)}]",
                 level="info",
                )
            else:
                print(f"  {k}: {v}")
                log_custom_event(
                 logger,
                 f"  {k}: {v}",
                 level="info",
                )
        try:
            res = self.search_client.upload_documents(documents=[doc])
            if res[0].succeeded:
                print(f" Uploaded doc {res[0].key}")
                log_custom_event(
                 logger,
                 f" Uploaded doc {res[0].key}",
                 level="info",
                )
            else:
                print(f" Upload failed: {res[0].error_message}")
                log_custom_event(
                 logger,
                 f" Uploaded doc {res[0].key}",
                 level="warning",
                )
        except Exception as e:
            print(f" Error: {e}")
            print()
 
 
if __name__ == "__main__":
    # Initialize uploader
    uploader = AzureSearchRFPRequestUploader()
 
    # -------- Sample test data --------
    sample_data = {
        "chunks": [
{
  "chunk_id": "9475006a",
  "project_id": "proj_t2_docx",
  "file_name": "t2.docx",
  "content_type": "document",
  "created_at": "2025-09-25T16:31:09.436486",
  "project_name": "",
  "client": "Ontario Power Generation",
  "industry": "Power & Energy",
  "region": "DeCew Falls GS, Ontario, Canada",
  "prepared_date": "2024-03-07",
  "field_type": "Brown Field",
  "voltage": "600VAC",
  "contract_types": "Fixed Price",
  "pricing": "Not mentioned in the document",
  "location": "DeCew Falls GS",
  "state": "Ontario",
  "country": "Canada",
  "components": {
    "electrical": {
      "scope_of_work": "The project involves designing, constructing, installing, and commissioning a new communications network at the DeCew site, including establishing communication rooms with reliable power systems for all communication equipment.",
      "required_activities": "Install 600VAC distribution panels, lighting transformers, and UPS battery solutions. Ensure compatibility with existing systems. Provide power supply for IT, SCADA, and security equipment. Conduct ESA inspections and obtain certifications.",
      "cables_and_accessories": "Installation of armored cables for power and communication, including Cat6a and fiber optic cables with specific color coding for IT, SCADA, security, and revenue metering.",
      "buswork_and_insulators": "not mentioned in document",
      "electrical_others": "Integration of new electrical panels with existing systems, ensuring compatibility and redundancy for critical loads.",
      "electrical_description": "The electrical scope includes installing armored cables for power and communication, integrating new electrical panels with existing systems, and ensuring compatibility and redundancy for critical loads."
    },
    "equipment": {
      "scope_of_work": "The project includes the installation of IT, SCADA, and security equipment in new communication rooms and modular E-House buildings.",
      "required_activities": "Install IT racks, SCADA network racks, and security server racks. Relocate existing equipment to new racks. Provide UPS solutions for critical loads. Ensure compatibility with existing systems.",      
      "power_transformers": "Installation of 600/120/240V lighting transformers for power distribution in communication rooms.",
      "switching_equipment": "Deployment of RuggedCOM network switches and Mercury access controllers for IT and security systems.",
      "equipment_others": "Installation of PA systems, local workstations, and SCADA servers in designated racks.",
      "equipment_description": "The equipment scope includes installing lighting transformers, RuggedCOM network switches, Mercury access controllers, PA systems, local workstations, and SCADA servers in designated racks."
    },
    "site_preparation": {
      "scope_of_work": "Preparation of sites for new modular E-House buildings and communication rooms, including structural and environmental considerations.",
      "required_activities": "Conduct site inspections, prepare foundations, and ensure compliance with local building codes. Install HVAC systems and fire protection measures.",
      "clearing_and_demolition": "not mentioned in document",
      "fencing_and_Gates": "not mentioned in document",
      "site_preparation_others": "Preparation of modular E-House foundations and ensuring structural integrity for new installations.",
      "site_preparation_description": "The site preparation scope includes preparing modular E-House foundations, ensuring structural integrity, and installing HVAC systems and fire protection measures."
    },
    "protection_and_control": {
      "scope_of_work": "The project involves upgrading protection and control systems, including SCADA and security network integration.",
      "required_activities": "Install SCADA network racks, configure protection relays, and integrate with existing systems. Ensure redundancy and reliability for critical operations.",
      "protection_relays_and_schemes": "Configuration and installation of protection relays for SCADA systems.",    
      "scada_RTU_and_Automation": "Integration of SCADA systems with new network racks and automation equipment.",  
      "protection_and_control_others": "Ensuring compatibility and redundancy for protection and control systems.",
      "protection_and_control_description": "The protection and control scope includes configuring protection relays, integrating SCADA systems with new network racks, and ensuring compatibility and redundancy for critical operations."
    },
    "metering": {
      "scope_of_work": "Relocation and upgrade of revenue metering cabinets to new communication rooms.",
      "required_activities": "Install new metering racks, relocate existing P.O.P. and P.O.M. cabinets, and ensure dual power sources for reliability.",
      "metering_cts_and_vts": "Relocation of revenue metering cabinets with dual power sources for reliability.",  
      "meters_and_recorders": "Installation of new metering racks and integration with existing systems.",
      "metering_others": "Coordination with OPG teams for approval and compliance.",
      "metering_description": "The metering scope includes relocating revenue metering cabinets, installing new metering racks, and ensuring dual power sources for reliability and compliance."
    },
    "telecom_and_teleprotection": {
      "scope_of_work": "Upgrade and installation of telecom systems, including fiber optic networks and Bell telecommunication circuits.",
      "required_activities": "Install new fiber optic cables, configure WAN switches, and upgrade Bell circuits for SCADA and IT systems.",
      "switching_routing_and_transport": "Configuration of NRBN WAN switches and integration with SCADA and IT systems.",
      "radio_and_wan_access": "Upgrade of Bell telecommunication circuits and installation of fiber optic networks.",
      "telecom_and_teleprotection_others": "Ensuring redundancy and reliability for telecom systems.",
      "telecom_and_teleprotection_description": "The telecom and teleprotection scope includes configuring NRBN WAN switches, upgrading Bell circuits, and installing fiber optic networks to ensure redundancy and reliability."      
    }
  },
  "text_elements_count": 2173,
  "total_content_length": 117857,
  "processing_timestamp": "2025-09-25T16:31:09.436987"
}]
}
 
    # -------- Upload workflow --------
    print("🚀 Starting test upload...")
    log_custom_event(
                 logger,
                 "Starting test upload...",
                 level="info",
                )
    uploader.upload_direct_data(sample_data)