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
    .storage-info {
        background-color: #f3e5f5;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #9c27b0;
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
        st.info("🎯 Using Layout Model for extraction")
    else:
        st.error("❌ Azure credentials not configured")
        st.info("Please set your Azure credentials in config.py or environment variables")
    
    # Statistics
    if st.session_state.processed_data:
        stats = st.session_state.processed_data.get("stats", {})
        st.subheader("📊 Document Stats")
        st.metric("Text Chunks", stats.get("text_count", 0))
        st.metric("Tables", stats.get("table_count", 0))
        st.metric("Images", stats.get("image_count", 0))
        
        # Storage info
        st.subheader("💾 Local Storage")
        st.markdown('<div class="storage-info">Content saved to:<br/>• Text: extracted_content/text/<br/>• Tables: extracted_content/tables/<br/>• Images: extracted_content/images/</div>', unsafe_allow_html=True)

# Main content
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📤 Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'xlsx'],
        help="Supported formats: PDF, DOCX, XLSX"
    )
    
    # Check if file was removed
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
                    with st.spinner("Processing document with Azure Document Intelligence..."):
                        result = document_processor.process_document(uploaded_file, update_progress)
                    
                    st.session_state.processed_data = result
                    st.success("✅ Document processed successfully!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
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
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Text Content", "📊 Tables", "🖼️ Images", "💾 Storage Info"])
    
    with tab1:
        st.subheader("📝 Text Chunks")
        text_chunks = st.session_state.processed_data.get("text_chunks", [])
        raw_text = st.session_state.processed_data.get("raw_text", "")
        
        if text_chunks:
            st.info(f"Found {len(text_chunks)} text chunks")
            
            # Show raw text option
            if st.checkbox("Show Raw Text"):
                with st.expander("Raw Extracted Text"):
                    st.text_area("Raw Text", raw_text, height=300)
            
            # Pagination for chunks
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
                chunk_content = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
                chunk_id = chunk.get("chunk_id", f"chunk_{start_idx + i + 1}") if isinstance(chunk, dict) else f"chunk_{start_idx + i + 1}"
                section_name = chunk.get("section_name", "Unknown Section") if isinstance(chunk, dict) else "Unknown Section"
                
                with st.expander(f"Chunk {start_idx + i + 1} - {section_name} ({len(chunk_content)} chars)"):
                    st.markdown(f'<div class="content-box"><strong>ID:</strong> {chunk_id}<br><strong>Content:</strong><br>{chunk_content}</div>', unsafe_allow_html=True)
                    
                    # Show metadata if available
                    if isinstance(chunk, dict) and "metadata" in chunk:
                        metadata = chunk["metadata"]
                        st.markdown(f"**Metadata:** Word Count: {metadata.get('word_count', 0)}, Created: {metadata.get('created_at', 'N/A')}")
        else:
            st.warning("No text chunks created")
    
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
            st.info(f"Found {len(images)} images")
            
            for i, image in enumerate(images):
                image_type = image.get('type', 'figure')
                
                with st.expander(f"Image {i + 1} - Page {image.get('page_number', 'Unknown')} ({image_type})"):
                    
                    # Check if actual image is available
                    if image.get('image_base64'):
                        col_img, col_details = st.columns([2, 1])
                        
                        with col_img:
                            # Display image
                            import base64
                            from PIL import Image as PILImage
                            import io
                            
                            try:
                                img_data = base64.b64decode(image['image_base64'])
                                img = PILImage.open(io.BytesIO(img_data))
                                st.image(img, caption=f"Image from Page {image.get('page_number')}", use_column_width=True)
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download Image",
                                    data=img_data,
                                    file_name=f"image_{i+1}_page_{image.get('page_number', 'unknown')}.png",
                                    mime="image/png",
                                    key=f"download_img_{i}"
                                )
                            except Exception as e:
                                st.error(f"Error displaying image: {e}")
                        
                        with col_details:
                            st.markdown("**Image Details:**")
                            st.write(f"Page: {image.get('page_number', 'Unknown')}")
                            st.write(f"Type: {image_type}")
                            if image.get('width') and image.get('height'):
                                st.write(f"Size: {image.get('width')} × {image.get('height')}")
                            if image.get('image_path'):
                                st.write(f"Saved: {os.path.basename(image.get('image_path'))}")
                    
                    # Show text content from image
                    if image.get('content') and image.get('content') != f"Figure from page {image.get('page_number')}":
                        st.markdown("**Text Content from Image:**")
                        st.markdown(f'<div class="image-box">{image.get("content")}</div>', unsafe_allow_html=True)
                    
                    # If no image but has text content
                    if not image.get('image_base64') and image.get('content'):
                        st.markdown("**Image Content (Text Only):**")
                        content = image.get("content", "No text content")
                        st.markdown(f'<div class="image-box">{content}</div>', unsafe_allow_html=True)
                        st.info("💡 This is text content from a figure/diagram detected by Azure DI.")
        else:
            st.warning("No images extracted")
    
    with tab4:
        st.subheader("💾 Storage Information")
        
        # Display file paths and storage info
        filename = st.session_state.processed_data.get("filename", "unknown")
        base_filename = os.path.splitext(filename)[0]
        
        st.markdown("**Files saved to local storage:**")
        
        # Text files
        st.markdown("**📝 Text Files:**")
        text_chunks_path = f"extracted_content/text/{base_filename}_text_chunks.json"
        raw_text_path = f"extracted_content/text/{base_filename}_raw_text.txt"
        
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(text_chunks_path):
                st.success(f"✅ Text chunks: {text_chunks_path}")
                with open(text_chunks_path, 'rb') as f:
                    st.download_button(
                        "📥 Download Text Chunks (JSON)",
                        data=f.read(),
                        file_name=f"{base_filename}_text_chunks.json",
                        mime="application/json"
                    )
            else:
                st.info("No text chunks file")
        
        with col2:
            if os.path.exists(raw_text_path):
                st.success(f"✅ Raw text: {raw_text_path}")
                with open(raw_text_path, 'rb') as f:
                    st.download_button(
                        "📥 Download Raw Text",
                        data=f.read(),
                        file_name=f"{base_filename}_raw_text.txt",
                        mime="text/plain"
                    )
            else:
                st.info("No raw text file")
        
        # Table files
        tables = st.session_state.processed_data.get("tables", [])
        if tables:
            st.markdown("**📊 Table Files:**")
            for i, table in enumerate(tables):
                if table.get('csv_path') and os.path.exists(table['csv_path']):
                    st.success(f"✅ Table {i+1}: {table['csv_path']}")
        
        # Image files
        images = st.session_state.processed_data.get("images", [])
        if images:
            st.markdown("**🖼️ Image Files:**")
            for i, image in enumerate(images):
                if image.get('image_path') and os.path.exists(image['image_path']):
                    st.success(f"✅ Image {i+1}: {image['image_path']}")
                # Check for text files
                text_file = f"extracted_content/images/{base_filename}_figure_{i+1}.txt"
                if os.path.exists(text_file):
                    st.success(f"✅ Image {i+1} text: {text_file}")
        
        # Summary
        st.markdown("---")
        st.markdown("**📈 Processing Summary:**")
        stats = st.session_state.processed_data.get("stats", {})
        processing_method = st.session_state.processed_data.get("processing_method", "azure_document_intelligence")
        
        st.info(f"""
        **Processing Method:** {processing_method}
        **Text Chunks:** {stats.get("text_count", 0)}
        **Tables:** {stats.get("table_count", 0)}
        **Images:** {stats.get("image_count", 0)}
        **File Extension:** {st.session_state.processed_data.get("file_extension", "unknown")}
        """)

# Footer
st.markdown("---")
st.markdown('<p style="text-align: center; color: #666; font-size: 12px;">Document Processor with Azure Document Intelligence - Basic Implementation</p>', unsafe_allow_html=True)