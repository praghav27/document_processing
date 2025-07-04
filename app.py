import streamlit as st
import os
import pandas as pd
from main import document_processor
from config import AZURE_DOC_INTELLIGENCE_ENDPOINT, AZURE_DOC_INTELLIGENCE_KEY

# Page configuration
st.set_page_config(
    page_title="Document Processor",
    page_icon="📄",
    layout="wide"
)

# Custom CSS
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
    .table-box {
        background-color: #e8f5e8;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #4caf50;
    }
    .image-box {
        background-color: #fff3e0;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #ff9800;
    }
    .status-message {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border: 1px solid #1976d2;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = []
    if 'current_file' not in st.session_state:
        st.session_state.current_file = None

initialize_session_state()

# Header
st.markdown('<h1 class="main-header">📄 Document Processor</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Upload documents and extract text, tables, and images using Azure Document Intelligence</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Azure status
    if AZURE_DOC_INTELLIGENCE_ENDPOINT and AZURE_DOC_INTELLIGENCE_KEY:
        st.success("✅ Azure Document Intelligence configured")
    else:
        st.error("❌ Azure credentials not configured")
        st.info("Please set your Azure credentials in config.py or environment variables")
    
    # Statistics
    if st.session_state.processed_data:
        stats = st.session_state.processed_data.get("stats", {})
        st.subheader("📊 Current Document Stats")
        st.metric("Text Chunks", stats.get("text_count", 0))
        st.metric("Tables", stats.get("table_count", 0))
        st.metric("Images", stats.get("image_count", 0))

# Main content
col1, col2 = st.columns([1, 2])

# Replace the file upload section in app.py with this:

with col1:
    st.subheader("📤 Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'xlsx'],
        help="Supported formats: PDF, DOCX, XLSX"
    )
    
    # Check if file was removed (uploaded_file is None but we had a file before)
    if uploaded_file is None and st.session_state.current_file is not None:
        st.session_state.processed_data = None
        st.session_state.processing_status = []
        st.session_state.current_file = None
        st.info("File removed. Upload a new document to process.")
    
    if uploaded_file:
        # Check if new file
        if st.session_state.current_file != uploaded_file.name:
            st.session_state.processed_data = None
            st.session_state.processing_status = []
            st.session_state.current_file = uploaded_file.name
        
        st.success(f"📁 File loaded: {uploaded_file.name}")
        st.info(f"📊 Size: {uploaded_file.size / 1024:.1f} KB")
        
        # Process button
        if st.button("🚀 Process Document", type="primary"):
            if not AZURE_DOC_INTELLIGENCE_ENDPOINT or not AZURE_DOC_INTELLIGENCE_KEY:
                st.error("Please configure Azure credentials")
            else:
                # Progress tracking
                status_container = st.empty()
                
                def update_progress(message):
                    st.session_state.processing_status.append(message)
                    with status_container.container():
                        for status in st.session_state.processing_status[-3:]:
                            st.markdown(f'<div class="status-message">{status}</div>', unsafe_allow_html=True)
                
                try:
                    with st.spinner("Processing document..."):
                        result = document_processor.process_document(uploaded_file, update_progress)
                    
                    st.session_state.processed_data = result
                    st.success("✅ Document processed successfully!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        # No file uploaded
        st.info("Upload a document to get started")
       

with col2:
    st.subheader("📋 Processing Status")
    
    if st.session_state.processing_status:
        for status in st.session_state.processing_status[-5:]:
            st.markdown(f'<div class="status-message">{status}</div>', unsafe_allow_html=True)
    else:
        st.info("Upload and process a document to see status updates")

# Display extracted content
if st.session_state.processed_data:
    st.markdown("---")
    st.header("📋 Extracted Content")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📝 Text Content", "📊 Tables", "🖼️ Images"])
    
    with tab1:
        st.subheader("📝 Text Chunks")
        text_chunks = st.session_state.processed_data.get("text_chunks", [])
        
        if text_chunks:
            st.info(f"Found {len(text_chunks)} text chunks")
            
            # Pagination
            chunks_per_page = st.selectbox("Chunks per page", [5, 10, 20], index=1)
            total_pages = (len(text_chunks) - 1) // chunks_per_page + 1
            
            if total_pages > 1:
                page = st.selectbox("Page", range(1, total_pages + 1))
                start_idx = (page - 1) * chunks_per_page
                end_idx = min(start_idx + chunks_per_page, len(text_chunks))
                chunks_to_show = text_chunks[start_idx:end_idx]
            else:
                chunks_to_show = text_chunks
                start_idx = 0
            
            for i, chunk in enumerate(chunks_to_show):
                with st.expander(f"Chunk {start_idx + i + 1}"):
                    st.markdown(f'<div class="content-box">{chunk}</div>', unsafe_allow_html=True)
        else:
            st.warning("No text content extracted")
    
    with tab2:
        st.subheader("📊 Extracted Tables")
        tables = st.session_state.processed_data.get("tables", [])
        
        if tables:
            st.info(f"Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                with st.expander(f"Table {i + 1} - Page {table.get('page_number', 'Unknown')}"):
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        if 'html' in table:
                            st.markdown("**Table Preview:**")
                            st.markdown(table['html'], unsafe_allow_html=True)
                        else:
                            st.markdown("**Table Content:**")
                            st.text(table['content'])
                    
                    with col_b:
                        st.markdown("**Details:**")
                        st.write(f"Page: {table.get('page_number', 'Unknown')}")
                        st.write(f"Rows: {table.get('row_count', 'N/A')}")
                        st.write(f"Columns: {table.get('column_count', 'N/A')}")
                        
                        # Download CSV
                        if 'csv_path' in table and os.path.exists(table['csv_path']):
                            with open(table['csv_path'], 'rb') as f:
                                csv_data = f.read()
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv_data,
                                file_name=os.path.basename(table['csv_path']),
                                mime="text/csv",
                                key=f"download_table_{i}"
                            )
        else:
            st.warning("No tables extracted")
    
    with tab3:
        st.subheader("🖼️ Extracted Images")
        images = st.session_state.processed_data.get("images", [])
        
        if images:
            st.info(f"Found {len(images)} images/figures")
            
            for i, image in enumerate(images):
                image_type = image.get('type', 'unknown')
                
                with st.expander(f"Image/Figure {i + 1} - Page {image.get('page_number', 'Unknown')} ({image_type})"):
                    
                    # Show actual image if available
                    if image.get('image_base64'):
                        col_img, col_details = st.columns([2, 1])
                        
                        with col_img:
                            # Display image
                            import base64
                            from PIL import Image
                            import io
                            
                            img_data = base64.b64decode(image['image_base64'])
                            img = Image.open(io.BytesIO(img_data))
                            st.image(img, caption=f"Image from Page {image.get('page_number')}", use_column_width=True)
                            
                            # Show extracted text content
                            if image.get('content') and image.get('content') != f"Image from page {image.get('page_number')}":
                                st.markdown("**Text Content from Image:**")
                                st.markdown(f'<div class="image-box">{image.get("content")}</div>', unsafe_allow_html=True)
                            
                            # Download button
                            st.download_button(
                                label="📥 Download Image",
                                data=img_data,
                                file_name=f"image_{i+1}_page_{image.get('page_number', 'unknown')}.png",
                                mime="image/png",
                                key=f"download_img_{i}"
                            )
                        
                        with col_details:
                            st.markdown("**Image Details:**")
                            st.write(f"Page: {image.get('page_number', 'Unknown')}")
                            st.write(f"Type: {image_type}")
                            if image.get('width') and image.get('height'):
                                st.write(f"Size: {image.get('width')} × {image.get('height')}")
                            if image.get('image_path'):
                                st.write(f"Saved: {os.path.basename(image.get('image_path'))}")
                    
                    else:
                        # Text-only figure (no actual image found)
                        st.markdown("**Figure Content (Text Only):**")
                        content = image.get("content", "No text content")
                        st.markdown(f'<div class="image-box">{content}</div>', unsafe_allow_html=True)
                        
                        st.info("💡 This is text content from a figure/diagram. No extractable image file was found.")
        else:
            st.warning("No images or figures extracted")

# Footer
st.markdown("---")
st.markdown('<p style="text-align: center; color: #666; font-size: 12px;">Document Processor with Azure Document Intelligence</p>', unsafe_allow_html=True)