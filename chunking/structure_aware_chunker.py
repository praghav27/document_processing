import re
from typing import Dict, List, Optional
from llm_processing import DocumentStructureAnalyzer, ContentMapper, MultimodalVerbalizer, MetadataGenerator
from .section_processor import SectionProcessor
from .chunk_optimizer import ChunkOptimizer
from config import CHUNKING_CONFIG

class StructureAwareChunker:
    """Main class for creating structure-aware chunks with rich metadata"""
    
    def __init__(self):
        self.structure_analyzer = DocumentStructureAnalyzer()
        self.content_mapper = ContentMapper()
        self.verbalizer = MultimodalVerbalizer()
        self.metadata_generator = MetadataGenerator()
        self.section_processor = SectionProcessor()
        self.chunk_optimizer = ChunkOptimizer()
        self.config = CHUNKING_CONFIG
    
    def create_structure_based_chunks(self, raw_text: str, tables: List[Dict], images: List[Dict], document_metadata: Dict) -> Dict:
        """
        Main method to create structure-aware chunks from document content
        Returns complete chunking result with metadata and statistics
        """
        print("🧠 Starting structure-aware chunking process...")
        
        try:
            # Step 1: Analyze document structure
            print("📊 Step 1: Analyzing document structure...")
            structure = self.structure_analyzer.analyze_document_structure(raw_text)
            
            if not structure.get("sections"):
                print("⚠️ No structure found, using fallback chunking")
                return self._fallback_chunking(raw_text, tables, images, document_metadata)
            
            # Step 2: Map multimodal content to sections
            print("🗺️ Step 2: Mapping tables and images to sections...")
            content_map = self.content_mapper.map_multimodal_to_sections(structure, tables, images)
            
            # Step 3: Process each section with integrated content
            print("⚙️ Step 3: Processing sections with multimodal content...")
            all_chunks = []
            
            for section in content_map.get("sections", []):
                try:
                    section_chunks = self._process_section_for_chunking(section, raw_text, document_metadata)
                    all_chunks.extend(section_chunks)
                except Exception as e:
                    print(f"⚠️ Error processing section '{section.get('title', 'Unknown')}': {e}")
                    continue
            
            # Step 4: Optimize chunks
            print("🔧 Step 4: Optimizing chunk boundaries...")
            optimized_chunks = self.chunk_optimizer.optimize_chunks(all_chunks)
            
            # Step 5: Generate final metadata and statistics
            print("📈 Step 5: Generating metadata and statistics...")
            final_result = self._create_final_result(optimized_chunks, structure, content_map, document_metadata)
            
            print(f"✅ Structure-aware chunking complete!")
            print(f"   📝 Created {len(optimized_chunks)} chunks from {len(structure.get('sections', []))} sections")
            print(f"   📊 Coverage: {final_result['statistics']['text_coverage_percentage']:.1f}%")
            
            return final_result
            
        except Exception as e:
            print(f"❌ Error in structure-aware chunking: {e}")
            return self._fallback_chunking(raw_text, tables, images, document_metadata)
    
    def _process_section_for_chunking(self, section: Dict, full_text: str, document_metadata: Dict) -> List[Dict]:
        """Process individual section to create chunks"""
        
        section_title = section.get("title", "Unknown Section")
        section_start = section.get("start_char", 0)
        section_end = section.get("end_char", len(full_text))
        
        # Extract section text
        section_text = full_text[section_start:section_end]
        
        if not section_text.strip():
            return []
        
        # Integrate multimodal content
        enhanced_text = self.verbalizer.create_section_with_multimodal_content(
            section_text,
            section.get("tables", []),
            section.get("images", [])
        )
        
        # Determine chunking strategy based on section
        section_type = section.get("section_type", "general")
        strategy = self.config["section_strategies"].get(section_type, self.config["section_strategies"]["general"])
        
        # Create chunks for this section
        section_chunks = self.section_processor.create_section_chunks(
            enhanced_text,
            section,
            strategy,
            document_metadata
        )
        
        return section_chunks
    
    def _create_final_result(self, chunks: List[Dict], structure: Dict, content_map: Dict, document_metadata: Dict) -> Dict:
        """Create final result with comprehensive statistics"""
        
        # Calculate statistics
        total_chars = sum(chunk.get("char_count", 0) for chunk in chunks)
        total_tokens = sum(chunk.get("token_count", 0) for chunk in chunks)
        original_text_length = sum(
            section.get("end_char", 0) - section.get("start_char", 0) 
            for section in structure.get("sections", [])
        )
        
        statistics = {
            "total_chunks": len(chunks),
            "total_sections_processed": len(structure.get("sections", [])),
            "total_tokens": total_tokens,
            "total_characters": total_chars,
            "average_chunk_size_tokens": total_tokens / len(chunks) if chunks else 0,
            "average_chunk_size_chars": total_chars / len(chunks) if chunks else 0,
            "text_coverage_percentage": (total_chars / original_text_length * 100) if original_text_length > 0 else 100,
            "multimodal_integration": {
                "tables_integrated": content_map.get("mapping_stats", {}).get("mapped_tables", 0),
                "images_integrated": content_map.get("mapping_stats", {}).get("mapped_images", 0),
                "chunks_with_tables": sum(1 for chunk in chunks if chunk.get("has_table_content", False)),
                "chunks_with_images": sum(1 for chunk in chunks if chunk.get("has_image_content", False))
            }
        }
        
        # Create metadata summary
        metadata_summary = self.metadata_generator.create_metadata_summary(chunks)
        
        # Processing details
        processing_details = {
            "structure_analysis_method": structure.get("analysis_method", "llm_based"),
            "total_sections_found": len(structure.get("sections", [])),
            "content_mapping_stats": content_map.get("mapping_stats", {}),
            "unmapped_content": {
                "tables": len(content_map.get("unmapped_tables", [])),
                "images": len(content_map.get("unmapped_images", []))
            }
        }
        
        return {
            "chunks": chunks,
            "statistics": statistics,
            "metadata_summary": metadata_summary,
            "processing_details": processing_details,
            "document_structure": structure,
            "content_mapping": content_map
        }
    
    def _fallback_chunking(self, raw_text: str, tables: List[Dict], images: List[Dict], document_metadata: Dict) -> Dict:
        """Fallback chunking when structure analysis fails"""
        print("🔄 Using fallback chunking approach...")
        
        # Create simple chunks
        target_size = self.config["target_chunk_size"]
        overlap = self.config["semantic_overlap"]
        
        # Simple paragraph-based chunking
        paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_number = 1
        
        for paragraph in paragraphs:
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            estimated_tokens = len(test_chunk.split()) * 1.3
            
            if estimated_tokens > target_size and current_chunk:
                # Create chunk
                chunk_metadata = self.metadata_generator.generate_chunk_metadata(
                    current_chunk,
                    {"title": f"Document Section {chunk_number}", "section_type": "general"},
                    document_metadata,
                    chunk_number,
                    1  # Will be updated later
                )
                chunks.append(chunk_metadata)
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
                current_chunk = overlap_text + "\n\n" + paragraph if overlap_text else paragraph
                chunk_number += 1
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunk_metadata = self.metadata_generator.generate_chunk_metadata(
                current_chunk,
                {"title": f"Document Section {chunk_number}", "section_type": "general"},
                document_metadata,
                chunk_number,
                1
            )
            chunks.append(chunk_metadata)
        
        # Update total chunks count
        for chunk in chunks:
            chunk["total_chunks_in_section"] = len(chunks)
        
        # Create basic statistics
        statistics = {
            "total_chunks": len(chunks),
            "total_sections_processed": 1,
            "total_tokens": sum(chunk.get("token_count", 0) for chunk in chunks),
            "total_characters": sum(chunk.get("char_count", 0) for chunk in chunks),
            "text_coverage_percentage": 100.0,
            "processing_method": "fallback",
            "multimodal_integration": {
                "tables_integrated": 0,
                "images_integrated": 0,
                "chunks_with_tables": 0,
                "chunks_with_images": 0
            }
        }
        
        return {
            "chunks": chunks,
            "statistics": statistics,
            "metadata_summary": self.metadata_generator.create_metadata_summary(chunks),
            "processing_details": {"method": "fallback", "reason": "structure_analysis_failed"},
            "document_structure": {"sections": [], "total_sections": 0},
            "content_mapping": {"sections": [], "mapping_stats": {}}
        }
    
    def validate_chunks(self, chunks: List[Dict]) -> Dict:
        """Validate created chunks for quality and completeness"""
        
        validation_results = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "statistics": {
                "valid_chunks": 0,
                "invalid_chunks": 0,
                "empty_chunks": 0,
                "oversized_chunks": 0,
                "undersized_chunks": 0
            }
        }
        
        for i, chunk in enumerate(chunks):
            chunk_issues = []
            
            # Check required fields
            required_fields = ["chunk_id", "content", "section_type", "domain_category"]
            missing_fields = [field for field in required_fields if field not in chunk]
            if missing_fields:
                chunk_issues.append(f"Missing fields: {missing_fields}")
            
            # Check content quality
            content = chunk.get("content", "")
            if not content.strip():
                validation_results["statistics"]["empty_chunks"] += 1
                chunk_issues.append("Empty content")
            elif len(content) < self.config["min_chunk_size"] * 4:  # Rough char estimate
                validation_results["statistics"]["undersized_chunks"] += 1
                validation_results["warnings"].append(f"Chunk {i+1} is undersized")
            elif len(content) > self.config["max_chunk_size"] * 6:  # Rough char estimate
                validation_results["statistics"]["oversized_chunks"] += 1
                validation_results["warnings"].append(f"Chunk {i+1} is oversized")
            
            # Track statistics
            if chunk_issues:
                validation_results["statistics"]["invalid_chunks"] += 1
                validation_results["issues"].extend([f"Chunk {i+1}: {issue}" for issue in chunk_issues])
            else:
                validation_results["statistics"]["valid_chunks"] += 1
        
        # Overall validation
        if validation_results["statistics"]["invalid_chunks"] > 0:
            validation_results["is_valid"] = False
        
        return validation_results