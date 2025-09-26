
import os
import uuid
from datetime import datetime
from typing import List, Dict
# from storage.local_storage import LocalStorage
from storage.storage_factory import get_storage_instance
from processors.content_verbalizer import ContentVerbalizer
import asyncio

from application_logging.custom_logging_to_app_insights import configure_logger, log_custom_event

# Configure the logger
logger = configure_logger()

class ImageExtractor:
    """Handle image/figure extraction and chunking logic"""
    
    def __init__(self):
        # self.storage = LocalStorage()
        self.storage = get_storage_instance()
        self.verbalizer = ContentVerbalizer()

    def _find_footer_position(self, page_number: int, text_elements: List[Dict]) -> dict:
        """Find footer X,Y position on given page using role attribute"""
        for element in text_elements:
            if (element.get('page_number') == page_number and 
                element.get('role') == 'pageFooter'):
                footer_pos = element.get('position', {})
                footer_x = footer_pos.get('x', 0)
                footer_y = footer_pos.get('y', 0)
                #print(f"Footer found on page {page_number} at position: ({footer_x}, {footer_y})")
                return {"x": footer_x, "y": footer_y}
        return None
    
    def _should_exclude_figure(self, figure_data: Dict, text_elements: List[Dict] = None) -> bool:
        """
        Simple logo detection based on content length and image dimensions and dist from footer logic
        Step 1: Check if content is TE TETRA TECH or Tt TETRA TECH
        Step 2: Check if image dimensions are very small
        Step 3 : Check if figure is too close to the footer 
        """
        
        content = figure_data.get('content', '')
        
        # Step 1
        logo_patterns = [
            'TE\nTETRA TECH',
            'Tt\nTETRA TECH', 
            'TE TETRA TECH',
            'Tt TETRA TECH',
            'TE'
        ]

        if content in logo_patterns:
            #print(f"🚫 Logo detected: '{content}'")
            return True
        
        # Step 2
        # width_threshold = 150  # pixels
        # height_threshold = 100  
        
        # if width > 0 and height > 0:  
        #     if width <= width_threshold and height <= height_threshold:
        #         return True

        # Step 3
        position = figure_data.get('position', {})
        figure_x = position.get('x', 0)
        figure_y = position.get('y', 0)
        page_number = figure_data.get('page_number', 1)
        
        footer_position = self._find_footer_position(page_number, text_elements) if text_elements else None
        if footer_position:  # Footer found on this page
            x_diff = abs(figure_x - footer_position['x'])
            y_diff = abs(figure_y - footer_position['y'])
            distance_from_footer = x_diff + y_diff  # Manhattan distance
            
            footer_threshold = 6.75  # pixels - adjust as needed
            if distance_from_footer <= footer_threshold:
                #print(f"🚫 Logo detected by footer proximity: distance={distance_from_footer}")
                return True
        else:
            #print(f"ℹ️ No footer found on page {page_number} - skipping footer check")
            print()

        return False
        
    def extract_figures(self, result, base_filename: str, client=None, operation_id=None, section_mapper=None, text_elements: List[Dict] = None,storage=None) -> List[Dict]:
        """Extract figures/images using Azure Document Intelligence with section association"""
        figures = []
        
        if hasattr(result, 'figures') and result.figures:
            for fig_idx, figure in enumerate(result.figures):
                try:
                    # Extract text content from figure
                    text_content = self._extract_figure_content(figure, result)
                    page_number = getattr(figure.bounding_regions[0], 'page_number', 1) if figure.bounding_regions else 1
                    
                    # Get figure position and find closest section
                    figure_position = self._get_figure_position(figure)
                    section_info = section_mapper.find_closest_section(page_number, figure_position, text_elements) if section_mapper and text_elements else {}
                    
                    figure_data = {
                        "content": text_content or f"Figure from page {page_number}",
                        "page_number": page_number,
                        "figure_index": fig_idx + 1,
                        "type": "figure",
                        "image_path": None,
                        "image_base64": None,
                        "width": None,
                        "height": None,
                        "section_info": section_info,
                        "position": figure_position
                    }
                    position = figure_data.get('position', {})
                    figure_x = position.get('x', 0)
                    figure_y = position.get('y', 0)
                    page_number = figure_data.get('page_number', 1)

                    footer_position = self._find_footer_position(page_number, text_elements) if text_elements else None
                    if footer_position:
                        x_diff = abs(figure_x - footer_position['x'])
                        y_diff = abs(figure_y - footer_position['y'])
                        distance_from_footer = x_diff + y_diff
                    else:
                        distance_from_footer = "Footer not found"

                    # Print distances
                    # print(f"Figure {fig_idx + 1} (Page {page_number}):")
                    # print(f"   Position: ({figure_x}, {figure_y})")
                    # print(f"   Distance from Footer: {distance_from_footer}")

                    # Check for logo BEFORE doing ANY storage operations
                    if self._should_exclude_figure(figure_data, text_elements):
                        #print(f"ℹ️ Skipping logo figure {fig_idx + 1} - not saving to storage")
                        continue  # Skip this figure entirely

                    # Try to extract actual image using get_analyze_result_figure
                    if figure.id and client and operation_id:
                        try:
                            #print(f"Extracting image for figure {fig_idx + 1} with ID: {figure.id}")
                            
                            # Get the raw image bytes
                            image_response = client.get_analyze_result_figure(
                                model_id=result.model_id,
                                result_id=operation_id,
                                figure_id=figure.id
                            )
                            
                            # Convert iterator to bytes
                            image_bytes = b''.join(image_response)
                            
                            if image_bytes:
                                # Save the image
                                
                                # image_path = self.storage.save_figure_image_bytes(
                                #     image_bytes, 
                                #     base_filename, 
                                #     fig_idx + 1
                                # )
                                active_storage = storage if storage else self.storage
                                image_path = active_storage.save_figure_image_bytes(image_bytes, base_filename, fig_idx + 1)

                                
                                if image_path:
                                    # Convert to base64 for display
                                    import base64
                                    img_base64 = base64.b64encode(image_bytes).decode()
                                    
                                    figure_data.update({
                                        "image_path": image_path,
                                        "image_base64": img_base64,
                                        "type": "figure_with_image"
                                    })
                                    
                                    # Get image dimensions
                                    try:
                                        from PIL import Image
                                        from io import BytesIO
                                        img = Image.open(BytesIO(image_bytes))
                                        figure_data.update({
                                            "width": img.width,
                                            "height": img.height
                                        })
                                        
                                    except Exception as e:
                                        #print(f"Error getting image dimensions: {e}")
                                        print()


                                    
                                #print(f"✅ Successfully extracted image for figure {fig_idx + 1}")
                                log_custom_event(
                                                logger,
                                                f"Successfully extracted image for figure {fig_idx + 1}",
                                                level="info",
                                                )
                            else:
                                #print(f"⚠️ No image data received for figure {fig_idx + 1}")
                                log_custom_event(
                                                logger,
                                                f"No image data received for figure {fig_idx + 1}",
                                                level="warning",
                                                )
                                
                        except Exception as e:
                            print()
                            #print(f"❌ Error extracting image for figure {fig_idx + 1}: {e}")
                            # Continue with text-only figure
                            
                    
                    else:
                        if not figure.id:
                            #print(f"ℹ️ Figure {fig_idx + 1} has no ID - text content only")
                            print()
                        if not client or not operation_id:
                            #print(f"ℹ️ Client or operation_id not provided - text content only")
                            print()
                    
                    # Save text content if available
                    if text_content and text_content.strip():
                        #print(f"💾 Saving text content for figure {fig_idx + 1}: {len(text_content)} characters")
                        log_custom_event(
                                        logger,
                                        f"Saving text content for figure {fig_idx + 1}: {len(text_content)} characters",
                                        level="info",
                                        )
                        
                        # text_path = self.storage.save_figure_text(text_content, base_filename, fig_idx + 1)
                        text_path = active_storage.save_figure_text(text_content, base_filename, fig_idx + 1)
                        if text_path:
                            #print(f"✅ Text saved successfully: {text_path}")
                            log_custom_event(
                                            logger,
                                            f"Text saved successfully: {text_path}",
                                            level="info",
                                            )
                        else:
                            #print(f"❌ Failed to save text for figure {fig_idx + 1}")
                            log_custom_event(
                                            logger,
                                            f"Failed to save text for figure {fig_idx + 1}",
                                            level="warning",
                                            )

                    else:
                        #print(f"ℹ️ No text content for figure {fig_idx + 1}")
                        log_custom_event(
                                        logger,
                                        f"No text content for figure {fig_idx + 1}",
                                        level="info",
                                        )

                    
                    figures.append(figure_data)
                    
                except Exception as e:
                    #print(f"Error processing figure {fig_idx + 1}: {e}")
                    continue
        
        return figures
    
    # async def create_image_chunks(self, figures: List[Dict], base_filename: str, document_metadata: Dict, section_mapper, text_elements: List[Dict], rfp_id: str = None) -> List[Dict]:
    async def create_image_chunks(self, figures: List[Dict], base_filename: str, document_metadata: Dict, section_mapper, text_elements: List[Dict], rfp_id: str = None, project_id: str = None) -> List[Dict]:
        """Create chunks for images with ASYNC verbalization, section mapping, and LLM metadata"""
        image_chunks = []
       
        # Create a list of tasks for concurrent verbalization
        verbalization_tasks = []
        image_data_list = []
       
        for idx, figure in enumerate(figures):
            try:
                # Get section info from closest text chunk
                section_mapping = section_mapper.get_section_info_from_closest_text_chunk(
                    figure.get('page_number', 1),
                    figure.get('position', {}),
                    text_elements
                )
               
                # Store image data and section mapping for later use
                image_info = {
                    'figure': figure,
                    'idx': idx,
                    'section_mapping': section_mapping,
                    'base_filename': base_filename,
                    'document_metadata': document_metadata
                }
                image_data_list.append(image_info)
               
                # Add verbalization task to concurrent execution
                verbalization_tasks.append(self.verbalizer.verbalize_image(figure))
               
            except Exception as e:
                #print(f"   ❌ Error preparing image chunk {idx + 1}: {e}")
                continue
       
        # Execute all verbalizations concurrently
        if verbalization_tasks:
            #print(f"🤖 Running {len(verbalization_tasks)} image verbalizations concurrently...")
            log_custom_event(
                            logger,
                            f"Running {len(verbalization_tasks)} image verbalizations concurrently...",
                            level="info",
                            )
            try:
                verbalized_contents = await asyncio.gather(*verbalization_tasks, return_exceptions=True)
            except Exception as e:
                #print(f"❌ Error in concurrent verbalization: {e}")
                verbalized_contents = [f"Error verbalizing image {i+1}" for i in range(len(verbalization_tasks))]
        else:
            verbalized_contents = []
       
        # Create chunks with verbalized content
        for i, image_info in enumerate(image_data_list):
            try:
                figure = image_info['figure']
                idx = image_info['idx']
                section_mapping = image_info['section_mapping']
                document_metadata = image_info['document_metadata']
               
                # Get verbalized content (handle exceptions from gather)
                if i < len(verbalized_contents) and not isinstance(verbalized_contents[i], Exception):
                    verbalized_content = verbalized_contents[i]
                else:
                    #print(f"⚠️ Verbalization failed for image {idx + 1}, using fallback")
                    log_custom_event(
                                    logger,
                                    f"Verbalization failed for image {idx + 1}, using fallback",
                                    level="info",
                                    )
                    verbalized_content = f"Image from page {figure.get('page_number', 'unknown')}"
               
                # Use LLM-extracted metadata for chunk creation
                file_name = document_metadata.get('project_title', base_filename)
                if file_name == 'Not Specified':
                    file_name = base_filename
                elif len(file_name) > 50:
                    file_name = file_name[:50]
               
                domain = document_metadata.get('domain_category', 'none')
                if domain == 'Not Specified' or domain == 'Other':
                    domain = 'none'
               
                vendor_name = document_metadata.get('vendor_name', 'tetratech')
                if vendor_name == 'Not Specified':
                    vendor_name = 'tetratech'
               
                # Create image chunk with LLM metadata integration
                chunk = {
                    # 'chunk_id': str(uuid.uuid4())[:8],
                    'chunk_id': str(uuid.uuid4()),
                    'file_name': file_name,
                    'project_id': project_id,
                    'section_name': section_mapping['section_name'],  # From closest text chunk
                    'section_no': section_mapping['section_no'],      # From closest text chunk
                    'domain': domain,                                  # From LLM extraction
                    'content_type': 'image',
                    'author': vendor_name,                             # From LLM extraction (vendor_name)
                    'content': figure.get('content', ''),
                    'verbalized_content': verbalized_content,  # AI-generated description (ASYNC)
                    'rfp_id': rfp_id,  # RFP ID extracted from document
                    'metadata': {
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'chunk_index': idx,
                        'word_count': len(verbalized_content.split()),
                        'char_count': len(verbalized_content),
                        'image_info': {
                            'page_number': figure.get('page_number', 1),
                            'image_type': figure.get('type', 'figure'),
                            'image_path': figure.get('image_path', ''),
                            'width': figure.get('width'),
                            'height': figure.get('height'),
                            'section_info': figure.get('section_info', {})
                        },
                        # Store LLM-extracted metadata for reference
                        'llm_extracted_metadata': document_metadata
                    }
                }
               
                image_chunks.append(chunk)
                #print(f"   ✅ Created image chunk {idx + 1} with ASYNC verbalization - Author: {vendor_name}, Domain: {domain}")
                log_custom_event(
                                logger,
                                f"Created image chunk {idx + 1} with ASYNC verbalization - Author: {vendor_name}, Domain: {domain}",
                                level="info",
                                )
               
            except Exception as e:
                #print(f"   ❌ Error creating image chunk {i + 1}: {e}")
                continue
       
        return image_chunks
    
    def _get_figure_position(self, figure):
        """Get figure position from bounding regions"""
        if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
            bounding_region = figure.bounding_regions[0]
            if hasattr(bounding_region, 'polygon') and bounding_region.polygon:
                polygon = bounding_region.polygon
                if len(polygon) >= 2:
                    return {
                        "x": polygon[0],
                        "y": polygon[1],
                        "page": getattr(bounding_region, 'page_number', 1)
                    }
        return {"x": 0, "y": 0, "page": 1}
    
    def _extract_figure_content(self, figure, result) -> str:
        """Extract text content from figure using spans"""
        if hasattr(figure, 'spans') and figure.spans and hasattr(result, 'content'):
            content_parts = []
            for span in figure.spans:
                try:
                    span_content = result.content[span.offset:span.offset + span.length]
                    if span_content.strip():
                        content_parts.append(span_content.strip())
                except:
                    continue
            return " ".join(content_parts)
        return ""