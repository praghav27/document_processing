import asyncio
import os
from blob_document_reader import BlobDocumentReader
from main import DocumentProcessorMain
from config import AZURE_STORAGE_CONNECTION_STRING
import config  # Import config module to modify directly

async def process_project_from_blob(project_folder: str):
    """Process single project folder with document type hints in filenames"""
    print(f"\n{'='*80}")
    print(f"PROCESSING PROJECT: {project_folder}")
    print(f"{'='*80}")
    
    blob_reader = BlobDocumentReader(AZURE_STORAGE_CONNECTION_STRING)
    processor = DocumentProcessorMain()
    
    total_start_time = asyncio.get_event_loop().time()
    
    # Step 1: Process Proposal folder (RFP Response documents)
    print(f"Step 1: Processing Proposal folder (RFP Response documents)...")
    proposal_start = asyncio.get_event_loop().time()
    
    try:
        proposal_files = blob_reader.read_folder_files(project_folder, "Proposal")
        if proposal_files:
            print(f"Found {len(proposal_files)} file(s) in Proposal folder")
            
            # Add document type hint to file metadata
            for file in proposal_files:
                file._document_type_hint = "RFP"  # These are proposals/responses
            
            results = await processor.process_multiple_documents_rfi(proposal_files)
            proposal_time = asyncio.get_event_loop().time() - proposal_start
            
            successful = len([r for r in results if r.get('success', False)])
            print(f"Proposal processing completed in {proposal_time:.1f}s - {successful}/{len(proposal_files)} successful")
        else:
            print("No files found in Proposal folder")
    except Exception as e:
        print(f"Error processing Proposal folder: {e}")
    
    # Step 2: Process RFP folder (RFI Request documents)  
    print(f"\nStep 2: Processing RFP folder (RFI Request documents)...")
    rfp_start = asyncio.get_event_loop().time()
    
    try:
        rfp_files = blob_reader.read_folder_files(project_folder, "RFP")
        if rfp_files:
            print(f"Found {len(rfp_files)} file(s) in RFP folder")
            
            # Add document type hint to file metadata
            for file in rfp_files:
                file._document_type_hint = "RFI"  # These are RFI documents
            
            results = await processor.process_multiple_documents_rfi(rfp_files)
            rfp_time = asyncio.get_event_loop().time() - rfp_start
            
            successful = len([r for r in results if r.get('success', False)])
            print(f"RFP processing completed in {rfp_time:.1f}s - {successful}/{len(rfp_files)} successful")
        else:
            print("No files found in RFP folder")
    except Exception as e:
        print(f"Error processing RFP folder: {e}")
    
    total_time = asyncio.get_event_loop().time() - total_start_time
    print(f"\nPROJECT COMPLETED: {project_folder}")
    print(f"Total time: {total_time:.1f}s")

# async def process_project_from_blob(project_folder: str):
#     """Process single project folder (Proposal + RFP)"""
#     print(f"\n{'='*80}")
#     print(f"PROCESSING PROJECT: {project_folder}")
#     print(f"{'='*80}")
    
#     blob_reader = BlobDocumentReader(AZURE_STORAGE_CONNECTION_STRING)
#     processor = DocumentProcessorMain()
    
#     total_start_time = asyncio.get_event_loop().time()
    
#     # Step 1: Process Proposal folder (as RFP)
#     print(f"Step 1: Processing Proposal folder (RFP documents)...")
#     proposal_start = asyncio.get_event_loop().time()
    
#     try:
#         proposal_files = blob_reader.read_folder_files(project_folder, "Proposal")
#         if proposal_files:
#             print(f"Found {len(proposal_files)} file(s) in Proposal folder")
            
#             print(f"Processing as RFP documents")
    
            
#             # DIRECT CONFIG MODIFICATION for RFP
#             config.DEFAULT_DOCUMENT_TYPE = "RFP"
#             config.ENABLE_DOCUMENT_TYPE_DETECTION = False
#             print(f"Set document type to: {config.DEFAULT_DOCUMENT_TYPE}")
            
#             results = await processor.process_multiple_documents_rfi(proposal_files)
#             proposal_time = asyncio.get_event_loop().time() - proposal_start
            
#             successful = len([r for r in results if r.get('success', False)])
#             print(f"Proposal processing completed in {proposal_time:.1f}s - {successful}/{len(proposal_files)} successful")
#         else:
#             print("No files found in Proposal folder")
#     except Exception as e:
#         print(f"Error processing Proposal folder: {e}")
    
#     # Step 2: Process RFP folder (as RFI)
#     print(f"\nStep 2: Processing RFP folder (RFI documents)...")
#     rfp_start = asyncio.get_event_loop().time()
    
#     try:
#         rfp_files = blob_reader.read_folder_files(project_folder, "RFP")
#         if rfp_files:
#             print(f"Found {len(rfp_files)} file(s) in RFP folder")
#             print(f"Processing as RFI documents")
#             # DIRECT CONFIG MODIFICATION for RFI
#             config.DEFAULT_DOCUMENT_TYPE = "RFI"
#             config.ENABLE_DOCUMENT_TYPE_DETECTION = False
#             print(f"Set document type to: {config.DEFAULT_DOCUMENT_TYPE}")
            
#             results = await processor.process_multiple_documents_rfi(rfp_files)
           
#             rfp_time = asyncio.get_event_loop().time() - rfp_start
            
#             successful = len([r for r in results if r.get('success', False)])
#             print(f"RFP processing completed in {rfp_time:.1f}s - {successful}/{len(rfp_files)} successful")
#         else:
#             print("No files found in RFP folder")
#     except Exception as e:
#         print(f"Error processing RFP folder: {e}")
    
#     total_time = asyncio.get_event_loop().time() - total_start_time
#     print(f"\nPROJECT COMPLETED: {project_folder}")
#     print(f"Total time: {total_time:.1f}s")

async def main():
    """Main execution function"""
    print("Blob Document Processor")
    print("=" * 60)
    
    try:
        blob_reader = BlobDocumentReader(AZURE_STORAGE_CONNECTION_STRING)
        projects = blob_reader.list_projects()
        
        if not projects:
            print("No project folders found in blob container")
            return
        
        print(f"Found {len(projects)} project(s):")
        for i, project in enumerate(projects, 1):
            print(f" {i}. {project}")
        
        print(f"\nStarting processing...")
        overall_start = asyncio.get_event_loop().time()
        
        # Process each project sequentially
        for project in projects:
            await process_project_from_blob(project)
        
        overall_time = asyncio.get_event_loop().time() - overall_start
        print(f"\n{'='*80}")
        print(f"ALL PROJECTS COMPLETED!")
        print(f"Processed {len(projects)} projects in {overall_time/60:.1f} minutes")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())