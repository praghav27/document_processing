

import streamlit as st
import os
import pandas as pd
from main import document_processor
from config import AZURE_DOC_INTELLIGENCE_ENDPOINT, AZURE_DOC_INTELLIGENCE_KEY
import asyncio

# Page configuration
st.set_page_config(
    page_title="Enhanced Document Processor",
    page_icon="📄",
    layout="wide"
)

# Custom CSS - simplified
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    .content-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #1976d2;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #dc3545;
    }
    .table-storage-box {
        background-color: #e3f2fd;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #2196f3;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []
    if 'current_files' not in st.session_state:
        st.session_state.current_files = []

initialize_session_state()

# Header
st.markdown('<h1 class="main-header">📄 Enhanced Document Processor - Multi-File RFI Processing + Azure Table Storage</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Upload multiple documents for parallel RFI processing with enhanced component extraction and Azure Table Storage</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Azure status
    if AZURE_DOC_INTELLIGENCE_ENDPOINT and AZURE_DOC_INTELLIGENCE_KEY:
        st.success("✅ Azure Document Intelligence configured")
        st.info("🎯 Using Enhanced Layout Model for extraction")
    else:
        st.error("❌ Azure credentials not configured")
        st.info("Please set your Azure credentials in config.py")
    
    # Processing info
    st.subheader("📊 Multi-File Processing")
    st.info("• Maximum files: 10")
    st.info("• Supported: PDF, DOCX, XLSX")
    st.info("• Processing: Parallel")
    st.info("• Output: Terminal chunks")
    
    # NEW: Table Storage info
    st.subheader("🗃️ Azure Table Storage")
    st.success("✅ Table Storage: ENABLED")
    st.info("• File Metadata: FileMetadataV2")
    st.info("• Component Data: ComponentDataV2")
    st.info("• Structured querying enabled")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Multiple Documents")
    
    # Multiple file uploader
    uploaded_files = st.file_uploader(
        "Choose files (Max 10 files)",
        type=['pdf', 'docx', 'xlsx'],
        accept_multiple_files=True,
        help="Select multiple RFI documents for parallel processing with Azure Table Storage"
    )
    
    # Check file limits
    if uploaded_files and len(uploaded_files) > 10:
        st.error("❌ Maximum 10 files allowed. Please remove some files.")
        uploaded_files = uploaded_files[:10]
    
    # Show uploaded files
    if uploaded_files:
        st.success(f"📁 {len(uploaded_files)} files loaded:")
        for i, file in enumerate(uploaded_files, 1):
            st.write(f"{i}. {file.name} ({file.size / 1024:.1f} KB)")
        
        # Process button
        if st.button("🚀 Process All Documents (RFI + Azure Table Storage)", type="primary"):
            if not AZURE_DOC_INTELLIGENCE_ENDPOINT or not AZURE_DOC_INTELLIGENCE_KEY:
                st.error("Please configure Azure credentials")
            else:
                with st.spinner(f"Processing {len(uploaded_files)} documents in parallel + storing in Azure Table Storage..."):
                    try:
                        # Call the enhanced multi-file RFI processing method with table storage
                        results = asyncio.run(
                            document_processor.process_multiple_documents_rfi(uploaded_files)
                        )
                        
                        st.session_state.processing_results = results
                        st.session_state.current_files = [f.name for f in uploaded_files]
                        
                        # Show summary
                        successful = len([r for r in results if r.get('success', False)])
                        failed = len(results) - successful
                        
                        # Count table storage success
                        table_storage_successful = len([r for r in results if r.get('table_storage', {}).get('stored', False)])
                        table_storage_failed = len(results) - table_storage_successful
                        
                        if successful > 0:
                            st.success(f"✅ Successfully processed {successful}/{len(uploaded_files)} documents!")
                        if failed > 0:
                            st.error(f"❌ Failed to process {failed} documents")
                        
                        # Table storage summary
                        if table_storage_successful > 0:
                            st.success(f"🗃️ Successfully stored metadata for {table_storage_successful}/{len(uploaded_files)} documents in Azure Table Storage!")
                        if table_storage_failed > 0:
                            st.warning(f"⚠️ Failed to store metadata for {table_storage_failed} documents in Azure Table Storage")
                        
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    else:
        st.info("Upload RFI documents to get started with parallel processing + Azure Table Storage")

with col2:
    st.subheader("📋 Processing Results")
    
    if st.session_state.processing_results:
        successful_results = [r for r in st.session_state.processing_results if r.get('success', False)]
        failed_results = [r for r in st.session_state.processing_results if not r.get('success', False)]
        
        # Show successful results
        if successful_results:
            st.markdown(f'<div class="success-box"><strong>✅ Successfully Processed ({len(successful_results)} files):</strong><br/>', unsafe_allow_html=True)
            for result in successful_results:
                filename = result.get('filename', 'Unknown')
                chunks_count = len(result.get('chunks', []))
                components_count = len(result.get('metadata', {}).get('components', {}))
                table_stored = result.get('table_storage', {}).get('stored', False)
                
                st.markdown(f'• <strong>{filename}</strong>: {chunks_count} chunks, {components_count} components', unsafe_allow_html=True)
                if table_stored:
                    st.markdown(f'  🗃️ Metadata stored in Azure Table Storage ✅<br/>', unsafe_allow_html=True)
                else:
                    st.markdown(f'  🗃️ Table storage failed ❌<br/>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Show failed results
        if failed_results:
            st.markdown(f'<div class="error-box"><strong>❌ Failed to Process ({len(failed_results)} files):</strong><br/>', unsafe_allow_html=True)
            for result in failed_results:
                filename = result.get('filename', 'Unknown')
                error = result.get('error', 'Unknown error')
                st.markdown(f'• <strong>{filename}</strong>: {error}<br/>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Show overall statistics
        st.subheader("📊 Overall Statistics")
        total_chunks = sum(len(r.get('chunks', [])) for r in successful_results)
        total_components = sum(len(r.get('metadata', {}).get('components', {})) for r in successful_results)
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("Total Files", len(st.session_state.processing_results))
        with col_stat2:
            st.metric("Successful", len(successful_results))
        with col_stat3:
            st.metric("Total Chunks", total_chunks)
        with col_stat4:
            st.metric("Total Components", total_components)
        
        # NEW: Table Storage Statistics
        st.subheader("🗃️ Azure Table Storage Statistics")
        table_storage_successful = len([r for r in st.session_state.processing_results if r.get('table_storage', {}).get('stored', False)])
        table_storage_failed = len(st.session_state.processing_results) - table_storage_successful
        
        col_table1, col_table2, col_table3, col_table4 = st.columns(4)
        with col_table1:
            st.metric("Metadata Stored", table_storage_successful)
        with col_table2:
            st.metric("Storage Failed", table_storage_failed)
        with col_table3:
            component_records = sum(len(r.get('metadata', {}).get('components', {})) for r in successful_results if r.get('table_storage', {}).get('stored', False))
            st.metric("Component Records", component_records)
        with col_table4:
            st.metric("Tables Used", "2" if any(r.get('document_type') == 'RFI' for r in successful_results) else "1")
        
        # Table Storage Details
        st.markdown(f'<div class="table-storage-box">', unsafe_allow_html=True)
        st.markdown(f'<strong>🗃️ Azure Table Storage Details:</strong><br/>', unsafe_allow_html=True)
        st.markdown(f'• <strong>FileMetadataV2</strong>: Document-level metadata for all processed files<br/>', unsafe_allow_html=True)
        st.markdown(f'• <strong>ComponentDataV2</strong>: Component-specific data for RFI documents<br/>', unsafe_allow_html=True)
        st.markdown(f'• <strong>Query Capability</strong>: Structured querying by project, client, industry, components<br/>', unsafe_allow_html=True)
        st.markdown(f'• <strong>GUID Association</strong>: RFP-RFI linking for project management<br/>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Terminal output info
        st.info("📋 **All chunks have been printed to the terminal console.** Check your terminal for detailed chunk output with Azure Table Storage confirmation.")
        
    else:
        st.info("Upload and process documents to see results here")

# NEW: Table Storage Query Section
if st.session_state.processing_results:
    st.markdown("---")
    st.header("🗃️ Azure Table Storage Query Examples")
    
    with st.expander("View Sample Queries for Your Data"):
        successful_results = [r for r in st.session_state.processing_results if r.get('success', False)]
        
        if successful_results:
            # Extract some sample data for query examples
            sample_result = successful_results[0]
            sample_metadata = sample_result.get('metadata', {})
            
            st.subheader("📝 Sample Table Storage Queries")
            
            # File Metadata Queries
            st.write("**FileMetadataV2 Table Queries:**")
            st.code(f"""
# Query by client
handler.query_by_criteria("FileMetadataV2", client="{sample_metadata.get('client', 'example_client')}")

# Query by industry
handler.query_by_criteria("FileMetadataV2", industry="{sample_metadata.get('industry', 'Power & Energy')}")

# Query by document type
handler.query_by_criteria("FileMetadataV2", document_type="RFI")

# Get project with associated documents
handler.get_rfp_with_associated_rfis("{sample_result.get('project_id', 'example_project')}")
            """, language="python")
            
            # Component Data Queries
            if sample_metadata.get('components'):
                st.write("**ComponentDataV2 Table Queries:**")
                sample_components = list(sample_metadata.get('components', {}).keys())
                sample_component = sample_components[0] if sample_components else 'ELE'
                
                st.code(f"""
# Query by component type
handler.query_by_criteria("ComponentDataV2", component_name="{sample_component}")

# Get all components for a project
handler.get_components_by_project("{sample_result.get('project_id', 'example_project')}")

# Query by voltage class
handler.query_by_criteria("ComponentDataV2", voltage_class="{sample_metadata.get('voltage_class', 'Distribution')}")

# Query by field type
handler.query_by_criteria("ComponentDataV2", field_type="{sample_metadata.get('field_type', 'Brown Field')}")
                """, language="python")
            
            st.info("💡 **Note**: Use the AzureTableMetadataHandler class to execute these queries in your Python environment.")

# Footer
st.markdown("---")
st.markdown('<p style="text-align: center; color: #666; font-size: 12px;">Enhanced Multi-File RFI Document Processor with Parallel Processing + Azure Table Storage - Azure Document Intelligence</p>', unsafe_allow_html=True)