import re
from typing import Dict, List
from llm_processing import MetadataGenerator
from config import CHUNKING_CONFIG

class SectionProcessor:
    """Processes individual sections to create optimized chunks"""
    
    def __init__(self):
        self.metadata_generator = MetadataGenerator()
        self.config = CHUNKING_CONFIG
    
    def create_section_chunks(self, section_text: str, section_info: Dict, strategy: Dict, document_metadata: Dict) -> List[Dict]:
        """Create chunks for a single section using the specified strategy"""
        
        if not section_text.strip():
            return []
        
        target_size = strategy.get("target_size", self.config["target_chunk_size"])
        allow_split = strategy.get("allow_split", True)
        
        # Estimate token count
        estimated_tokens = self._estimate_tokens(section_text)
        
        # Determine if section needs splitting
        if estimated_tokens <= target_size or not allow_split:
            # Single chunk for entire section
            return [self._create_single_chunk(section_text, section_info, document_metadata, 1, 1)]
        else:
            # Multiple chunks needed
            return self._create_multiple_chunks(section_text, section_info, target_size, document_metadata)
    
    def _create_single_chunk(self, content: str, section_info: Dict, document_metadata: Dict, chunk_index: int, total_chunks: int) -> Dict:
        """Create a single chunk with enhanced section information"""
        
        # Add multimodal flags to section info
        enhanced_section_info = dict(section_info)
        enhanced_section_info.update({
            "has_tables": len(section_info.get("tables", [])) > 0,
            "has_images": len(section_info.get("images", [])) > 0
        })
        
        # Generate comprehensive metadata
        chunk_metadata = self.metadata_generator.generate_chunk_metadata(
            content,
            enhanced_section_info,
            document_metadata,
            chunk_index,
            total_chunks
        )
        
        return chunk_metadata
    
    def _create_multiple_chunks(self, section_text: str, section_info: Dict, target_size: int, document_metadata: Dict) -> List[Dict]:
        """Split section into multiple semantic chunks"""
        
        # Find semantic boundaries for splitting
        split_points = self._find_semantic_boundaries(section_text)
        
        if not split_points:
            # Fallback to paragraph splitting
            split_points = self._find_paragraph_boundaries(section_text)
        
        # Create chunks based on boundaries
        chunks = self._create_chunks_from_boundaries(section_text, split_points, target_size)
        
        # Generate metadata for each chunk
        chunk_objects = []
        total_chunks = len(chunks)
        
        for i, chunk_content in enumerate(chunks):
            if chunk_content.strip():
                chunk_metadata = self._create_single_chunk(
                    chunk_content,
                    section_info,
                    document_metadata,
                    i + 1,
                    total_chunks
                )
                chunk_objects.append(chunk_metadata)
        
        return chunk_objects
    
    def _find_semantic_boundaries(self, text: str) -> List[int]:
        """Find semantic boundaries in text for natural splitting"""
        
        boundaries = []
        
        # Look for subsection markers (numbered or bulleted lists)
        subsection_patterns = [
            r'\n\s*\d+\.\d+\.?\s+[A-Z]',  # 1.1, 2.3, etc.
            r'\n\s*[a-z]\)\s+[A-Z]',      # a), b), etc.
            r'\n\s*[A-Z]\.\s+[A-Z]',      # A., B., etc.
            r'\n\s*•\s+[A-Z]',            # Bullet points
            r'\n\s*-\s+[A-Z]',            # Dash points
        ]
        
        for pattern in subsection_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                boundaries.append(match.start())
        
        # Look for natural topic transitions
        transition_patterns = [
            r'\n\s*(?:Additionally|Furthermore|Moreover|However|Nevertheless|In contrast|Similarly|Likewise)\s',
            r'\n\s*(?:The following|As follows|Below are|The above|In summary|To conclude)\s',
            r'\n\s*(?:Phase \d+|Step \d+|Stage \d+|Part \d+)\s'
        ]
        
        for pattern in transition_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                boundaries.append(match.start())
        
        # Remove duplicates and sort
        boundaries = sorted(list(set(boundaries)))
        
        return boundaries
    
    def _find_paragraph_boundaries(self, text: str) -> List[int]:
        """Find paragraph boundaries as fallback splitting points"""
        
        boundaries = []
        
        # Find double newlines (paragraph breaks)
        for match in re.finditer(r'\n\s*\n', text):
            boundaries.append(match.end())
        
        return boundaries
    
    def _create_chunks_from_boundaries(self, text: str, boundaries: List[int], target_size: int) -> List[str]:
        """Create chunks based on identified boundaries"""
        
        if not boundaries:
            # No boundaries found, split by estimated token size
            return self._split_by_token_estimate(text, target_size)
        
        chunks = []
        current_chunk = ""
        last_pos = 0
        
        # Add text start and end positions
        all_positions = [0] + boundaries + [len(text)]
        all_positions = sorted(list(set(all_positions)))
        
        for i in range(len(all_positions) - 1):
            start_pos = all_positions[i]
            end_pos = all_positions[i + 1]
            segment = text[start_pos:end_pos].strip()
            
            if not segment:
                continue
            
            # Check if adding this segment would exceed target size
            test_chunk = current_chunk + "\n\n" + segment if current_chunk else segment
            estimated_tokens = self._estimate_tokens(test_chunk)
            
            if estimated_tokens > target_size and current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk.strip())
                current_chunk = segment
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_token_estimate(self, text: str, target_size: int) -> List[str]:
        """Split text by estimated token count when no semantic boundaries found"""
        
        words = text.split()
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        # Rough conversion: 1 token ≈ 0.75 words
        words_per_target = int(target_size * 0.75)
        
        for word in words:
            current_chunk.append(word)
            current_tokens += 1.3  # Rough token estimate
            
            if current_tokens >= words_per_target:
                # Try to end at sentence boundary
                chunk_text = " ".join(current_chunk)
                sentence_end = self._find_last_sentence_boundary(chunk_text)
                
                if sentence_end > len(chunk_text) * 0.7:  # If sentence boundary is reasonable
                    final_chunk = chunk_text[:sentence_end]
                    remaining_text = chunk_text[sentence_end:].strip()
                    
                    chunks.append(final_chunk.strip())
                    current_chunk = remaining_text.split() if remaining_text else []
                    current_tokens = len(current_chunk) * 1.3
                else:
                    # No good sentence boundary, split at word boundary
                    chunks.append(chunk_text)
                    current_chunk = []
                    current_tokens = 0
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _find_last_sentence_boundary(self, text: str) -> int:
        """Find the last sentence boundary in text"""
        
        # Look for sentence endings
        sentence_endings = list(re.finditer(r'[.!?]\s+', text))
        
        if sentence_endings:
            return sentence_endings[-1].end()
        
        return len(text)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation: 1 token ≈ 0.75 words for English text
        words = len(text.split())
        return int(words / 0.75)
    
    def integrate_section_content(self, section_text: str, tables: List[Dict], images: List[Dict]) -> str:
        """Integrate multimodal content into section text"""
        
        # This is now handled by MultimodalVerbalizer, but keeping for compatibility
        enhanced_text = section_text
        
        # Add table content
        for table in tables:
            table_content = table.get('content', '')
            if table_content:
                enhanced_text += f"\n\n[TABLE]: {table_content}"
        
        # Add image content
        for image in images:
            image_content = image.get('content', '')
            if image_content:
                enhanced_text += f"\n\n[FIGURE]: {image_content}"
        
        return enhanced_text
    
    def determine_section_chunk_strategy(self, section_content: str, section_type: str) -> str:
        """Determine optimal chunking strategy for section"""
        
        content_length = len(section_content)
        estimated_tokens = self._estimate_tokens(section_content)
        
        # Strategy based on section type and content characteristics
        if section_type in ["introduction", "assumptions", "exclusions"]:
            if estimated_tokens <= self.config["target_chunk_size"]:
                return "single_chunk"
            else:
                return "semantic_split"
        
        elif section_type in ["scope_of_work", "technical_requirements"]:
            if estimated_tokens <= self.config["max_chunk_size"]:
                return "single_chunk"
            else:
                return "subsection_split"
        
        elif section_type == "pricing":
            # Pricing sections often have tabular data
            return "table_aware_split"
        
        else:
            # General sections
            if estimated_tokens <= self.config["target_chunk_size"]:
                return "single_chunk"
            else:
                return "semantic_split"
    
    def split_section_semantically(self, content: str, max_size: int) -> List[str]:
        """Split section at semantic boundaries while respecting size limits"""
        
        # Find all possible split points
        boundaries = self._find_semantic_boundaries(content)
        
        if not boundaries:
            boundaries = self._find_paragraph_boundaries(content)
        
        if not boundaries:
            # Fallback to sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', content)
            return self._combine_sentences_to_chunks(sentences, max_size)
        
        return self._create_chunks_from_boundaries(content, boundaries, max_size)
    
    def _combine_sentences_to_chunks(self, sentences: List[str], max_size: int) -> List[str]:
        """Combine sentences into chunks respecting size limits"""
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            estimated_tokens = self._estimate_tokens(test_chunk)
            
            if estimated_tokens > max_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk = test_chunk
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def validate_section_chunks(self, chunks: List[Dict], section_info: Dict) -> Dict:
        """Validate chunks created for a section"""
        
        validation = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "statistics": {
                "total_chunks": len(chunks),
                "avg_size_tokens": 0,
                "min_size_tokens": float('inf'),
                "max_size_tokens": 0,
                "content_coverage": 0
            }
        }
        
        if not chunks:
            validation["is_valid"] = False
            validation["issues"].append("No chunks created for section")
            return validation
        
        # Calculate statistics
        token_counts = [chunk.get("token_count", 0) for chunk in chunks]
        validation["statistics"]["avg_size_tokens"] = sum(token_counts) / len(token_counts)
        validation["statistics"]["min_size_tokens"] = min(token_counts) if token_counts else 0
        validation["statistics"]["max_size_tokens"] = max(token_counts) if token_counts else 0
        
        # Check chunk sizes
        for i, chunk in enumerate(chunks):
            token_count = chunk.get("token_count", 0)
            
            if token_count < self.config["min_chunk_size"]:
                validation["warnings"].append(f"Chunk {i+1} is below minimum size ({token_count} tokens)")
            
            if token_count > self.config["max_chunk_size"]:
                validation["issues"].append(f"Chunk {i+1} exceeds maximum size ({token_count} tokens)")
                validation["is_valid"] = False
        
        # Check content coverage
        total_chunk_chars = sum(len(chunk.get("content", "")) for chunk in chunks)
        section_chars = section_info.get("end_char", 0) - section_info.get("start_char", 0)
        
        if section_chars > 0:
            coverage = (total_chunk_chars / section_chars) * 100
            validation["statistics"]["content_coverage"] = coverage
            
            if coverage < 90:
                validation["warnings"].append(f"Low content coverage: {coverage:.1f}%")
        
        return validation