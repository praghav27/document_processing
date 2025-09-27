import os
from typing import List, Dict, Tuple
from azure.storage.blob import BlobServiceClient
from io import BytesIO

class MockUploadedFile:
    """Mock Streamlit UploadedFile for blob compatibility"""
    def __init__(self, name: str, file_bytes: bytes):
        self.name = name
        self._bytes = file_bytes
    
    def read(self) -> bytes:
        return self._bytes

class BlobDocumentReader:
    def __init__(self, connection_string: str, container_name: str = "input-docs"):
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
    
    def list_projects(self) -> List[str]:
        """List all project folders"""
        container_client = self.blob_service_client.get_container_client(self.container_name)
        projects = []
        
        for blob in container_client.list_blobs():
            if '/' in blob.name:
                project_folder = blob.name.split('/')[0]
                if project_folder not in projects:
                    projects.append(project_folder)
        
        return sorted(projects)
    
    def standardize_filename(self, blob_path: str) -> str:
        """Add project ID to filename if missing"""
        path_parts = blob_path.split('/')
        folder_name = path_parts[0]
        original_filename = path_parts[-1]
        
        # Extract project ID from folder (first 15 chars before ' - ')
        project_id = folder_name.split(' - ')[0] if ' - ' in folder_name else folder_name[:15]
        
        # Check if filename already starts with project ID
        if original_filename.startswith(project_id):
            return original_filename
        else:
            name, ext = os.path.splitext(original_filename)
            return f"{project_id}-{name}{ext}"
    
    def read_folder_files(self, project_folder: str, folder_type: str) -> List[MockUploadedFile]:
        """Read files from specific project folder (Proposal or RFP)"""
        container_client = self.blob_service_client.get_container_client(self.container_name)
        files = []
        
        blob_prefix = f"{project_folder}/{folder_type}/"
        for blob in container_client.list_blobs(name_starts_with=blob_prefix):
            if blob.name.endswith('.pdf'):  # Only process PDF files
                try:
                    # Download blob
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name, 
                        blob=blob.name
                    )
                    file_bytes = blob_client.download_blob().readall()
                    
                    # Standardize filename
                    standardized_filename = self.standardize_filename(blob.name)
                    
                    # Create mock file
                    mock_file = MockUploadedFile(standardized_filename, file_bytes)
                    files.append(mock_file)
                    
                except Exception as e:
                    print(f"Error reading {blob.name}: {e}")
                    continue
        
        return files
    
    def get_project_structure(self, project_folder: str) -> Dict:
        """Get folder structure for a project"""
        container_client = self.blob_service_client.get_container_client(self.container_name)
        structure = {"Proposal": [], "RFP": []}
        
        for blob in container_client.list_blobs(name_starts_with=f"{project_folder}/"):
            if blob.name.endswith('.pdf'):
                path_parts = blob.name.split('/')
                if len(path_parts) >= 3:
                    folder_type = path_parts[1]
                    if folder_type in structure:
                        structure[folder_type].append(path_parts[2])
        
        return structure