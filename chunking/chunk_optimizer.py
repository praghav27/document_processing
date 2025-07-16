import re
from typing import List, Dict, Tuple
from config import CHUNKING_CONFIG

class ChunkOptimizer:
    """Optimizes chunk boundaries and quality for better semantic coherence"""
    
    def __init__(self):
        self.config = CHUNKING_CONFIG
    
    def optimize_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Main optimization method for chunk quality and boundaries"""
        
        if not chunks:
            return chunks
        
        print(f"🔧 Optimizing {len(chunks)} chunks...")
        
        # Step 1: Optimize individual chunk boundaries
        boundary_optimized = self._optimize_chunk_boundaries(chunks)
        
        # Step 2: Balance chunk sizes
        size_balanced = self._balance_chunk_sizes(boundary_optimized)
        
        # Step 3: Validate and fix chunk quality
        quality_validated = self._validate_and_fix_chunk_quality(size_balanced)
        
        # Step 4: Final cleanup
        final_chunks = self._final_cleanup(quality_validated)
        
        print(f"✅ Optimization complete: {len(chunks)} → {len(final_chunks)} chunks")
        
        return final_chunks
    
    def _optimize_chunk_boundaries(self, chunks: List[Dict]) -> List[Dict]:
        """Optimize chunk boundaries for better semantic coherence"""
        
        optimized_chunks = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            
            if not content.strip():
                continue
            
            # Find and fix poor boundaries
            optimized_content = self._fix_chunk_boundaries(content)
            
            # Update chunk with optimized content
            optimized_chunk = dict(chunk)
            optimized_chunk["content"] = optimized_content
            optimized_chunk["char_count"] = len(optimized_content)
            optimized_chunk["token_count"] = self._estimate_tokens(optimized_content)
            
            optimized_chunks.append(optimized_chunk)
        
        return optimized_chunks
    
    def _fix_chunk_boundaries(self, content: str) -> str:
        """Fix poor chunk boundaries within content"""
        
        # Remove orphaned section headers at the end
        content = self._remove_orphaned_headers(content)
        
        # Fix incomplete sentences at boundaries
        content = self._fix_incomplete_sentences(content)
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        return content.strip()
    
    def _remove_orphaned_headers(self, content: str) -> str:
        """Remove section headers that appear at the end without content"""
        
        lines = content.split('\n')
        
        # Look for headers at the end (last 2 lines)
        if len(lines) >= 2:
            last_lines = lines[-2:]
            
            for i, line in enumerate(last_lines):
                line = line.strip()
                
                # Check if line looks like a header
                if self._is_likely_header(line):
                    # Check if there's sufficient content after it
                    remaining_content = '\n'.join(last_lines[i+1:]).strip()
                    
                    if len(remaining_content) < 50:  # Insufficient content
                        # Remove this header and everything after
                        content = '\n'.join(lines[:-(len(last_lines)-i)])
                        break
        
        return content
    
    def _is_likely_header(self, line: str) -> bool:
        """Check if a line is likely a section header"""
        
        line = line.strip()
        
        # Header patterns
        header_patterns = [
            r'^\d+\.\d*\.?\s+[A-Z]',  # 1.1, 2.3, etc.
            r'^[A-Z][A-Z\s]{5,}$',   # ALL CAPS
            r'^[A-Z][^.!?]*:$',      # Ends with colon
            r'^\([a-z]\)\s*[A-Z]',   # (a), (b), etc.
        ]
        
        for pattern in header_patterns:
            if re.match(pattern, line):
                return True
        
        # Check for typical header characteristics
        if (len(line) < 80 and 
            len(line) > 5 and 
            not line.endswith('.') and 
            not line.endswith(',') and
            not line.endswith(';')):
            
            # Check if it starts with capital and has mostly capitals/title case
            words = line.split()
            if words and words[0][0].isupper():
                capital_ratio = sum(1 for word in words if word[0].isupper()) / len(words)
                if capital_ratio > 0.6:
                    return True
        
        return False
    
    def _fix_incomplete_sentences(self, content: str) -> str:
        """Fix incomplete sentences at chunk boundaries"""
        
        # Check if content ends mid-sentence
        content = content.rstrip()
        
        if content and not content[-1] in '.!?':
            # Find the last complete sentence
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            if len(sentences) > 1:
                # Keep only complete sentences
                complete_sentences = sentences[:-1]
                content = ' '.join(complete_sentences)
                
                # Ensure proper ending
                if content and not content[-1] in '.!?':
                    content += '.'
        
        return content
    
    def _balance_chunk_sizes(self, chunks: List[Dict]) -> List[Dict]:
        """Balance chunk sizes to be more uniform"""
        
        if len(chunks) <= 1:
            return chunks
        
        balanced_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            current_tokens = current_chunk.get("token_count", 0)
            
            # Check if chunk is too small and can be merged
            if (current_tokens < self.config["min_chunk_size"] and 
                i < len(chunks) - 1):
                
                next_chunk = chunks[i + 1]
                next_tokens = next_chunk.get("token_count", 0)
                
                # Merge if combined size is reasonable
                if current_tokens + next_tokens <= self.config["max_chunk_size"]:
                    merged_chunk = self._merge_chunks(current_chunk, next_chunk)
                    balanced_chunks.append(merged_chunk)
                    i += 2  # Skip next chunk as it's been merged
                    continue
            
            # Check if chunk is too large and needs splitting
            elif current_tokens > self.config["max_chunk_size"]:
                split_chunks = self._split_oversized_chunk(current_chunk)
                balanced_chunks.extend(split_chunks)
                i += 1
                continue
            
            # Chunk size is acceptable
            balanced_chunks.append(current_chunk)
            i += 1
        
        return balanced_chunks
    
    def _merge_chunks(self, chunk1: Dict, chunk2: Dict) -> Dict:
        """Merge two chunks into one"""
        
        merged_content = chunk1.get("content", "") + "\n\n" + chunk2.get("content", "")
        
        # Create merged chunk with updated metadata
        merged_chunk = dict(chunk1)  # Start with first chunk's metadata
        merged_chunk.update({
            "content": merged_content,
            "char_count": len(merged_content),
            "token_count": self._estimate_tokens(merged_content),
            "chunk_number": chunk1.get("chunk_number", 1),
            # Combine multimodal flags
            "has_table_content": (chunk1.get("has_table_content", False) or 
                                chunk2.get("has_table_content", False)),
            "has_image_content": (chunk1.get("has_image_content", False) or 
                                chunk2.get("has_image_content", False)),
            "table_count": chunk1.get("table_count", 0) + chunk2.get("table_count", 0),
            "image_count": chunk1.get("image_count", 0) + chunk2.get("image_count", 0)
        })
        
        # Update content type if needed
        if merged_chunk.get("has_table_content") and merged_chunk.get("has_image_content"):
            merged_chunk["content_type"] = "text_with_multimodal"
        elif merged_chunk.get("has_table_content"):
            merged_chunk["content_type"] = "text_with_table"
        elif merged_chunk.get("has_image_content"):
            merged_chunk["content_type"] = "text_with_image"
        
        return merged_chunk
    
    def _split_oversized_chunk(self, chunk: Dict) -> List[Dict]:
        """Split an oversized chunk into smaller pieces"""
        
        content = chunk.get("content", "")
        target_size = self.config["target_chunk_size"]
        
        # Find semantic boundaries for splitting
        boundaries = self.find_semantic_boundaries(content)
        
        if not boundaries:
            # Fallback to paragraph splitting
            paragraphs = content.split('\n\n')
            split_contents = self._split_paragraphs_to_size(paragraphs, target_size)
        else:
            split_contents = self._split_by_boundaries(content, boundaries, target_size)
        
        # Create new chunk objects
        split_chunks = []
        for i, split_content in enumerate(split_contents):
            if split_content.strip():
                new_chunk = dict(chunk)
                new_chunk.update({
                    "content": split_content,
                    "char_count": len(split_content),
                    "token_count": self._estimate_tokens(split_content),
                    "chunk_number": chunk.get("chunk_number", 1) + i,
                    "chunk_id": f"{chunk.get('chunk_id', '')}_split_{i+1}"
                })
                split_chunks.append(new_chunk)
        
        return split_chunks
    
    def _split_paragraphs_to_size(self, paragraphs: List[str], target_size: int) -> List[str]:
        """Split paragraphs into chunks of target size"""
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            estimated_tokens = self._estimate_tokens(test_chunk)
            
            if estimated_tokens > target_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk = test_chunk
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_boundaries(self, content: str, boundaries: List[int], target_size: int) -> List[str]:
        """Split content using identified boundaries"""
        
        chunks = []
        current_chunk = ""
        last_pos = 0
        
        for boundary in boundaries + [len(content)]:
            segment = content[last_pos:boundary]
            test_chunk = current_chunk + segment
            estimated_tokens = self._estimate_tokens(test_chunk)
            
            if estimated_tokens > target_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = segment
            else:
                current_chunk = test_chunk
            
            last_pos = boundary
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def find_semantic_boundaries(self, text: str) -> List[int]:
        """Find semantic boundaries in text for splitting"""
        
        boundaries = []
        
        # Look for paragraph breaks
        for match in re.finditer(r'\n\s*\n', text):
            boundaries.append(match.end())
        
        # Look for list items or numbered sections
        for match in re.finditer(r'\n\s*(?:\d+\.|[a-z]\)|\*|\-)\s+', text):
            boundaries.append(match.start())
        
        return sorted(list(set(boundaries)))
    
    def _validate_and_fix_chunk_quality(self, chunks: List[Dict]) -> List[Dict]:
        """Validate and fix chunk quality issues"""
        
        validated_chunks = []
        
        for chunk in chunks:
            content = chunk.get("content", "")
            
            # Skip empty chunks
            if not content.strip():
                continue
            
            # Clean up content
            cleaned_content = self._clean_chunk_content(content)
            
            # Validate minimum quality
            if self._meets_quality_standards(cleaned_content):
                updated_chunk = dict(chunk)
                updated_chunk["content"] = cleaned_content
                updated_chunk["char_count"] = len(cleaned_content)
                updated_chunk["token_count"] = self._estimate_tokens(cleaned_content)
                validated_chunks.append(updated_chunk)
        
        return validated_chunks
    
    def _clean_chunk_content(self, content: str) -> str:
        """Clean and normalize chunk content"""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Fix common formatting issues
        content = re.sub(r'([.!?])\s*\n\s*([A-Z])', r'\1 \2', content)  # Join broken sentences
        content = re.sub(r'\n\s*([a-z])', r' \1', content)  # Join broken words
        
        # Ensure proper sentence spacing
        content = re.sub(r'([.!?])([A-Z])', r'\1 \2', content)
        
        return content.strip()
    
    def _meets_quality_standards(self, content: str) -> bool:
        """Check if content meets minimum quality standards"""
        
        # Minimum length check
        if len(content.strip()) < 50:
            return False
        
        # Check for reasonable sentence structure
        sentences = re.split(r'[.!?]+', content)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(valid_sentences) == 0:
            return False
        
        # Check for reasonable word count
        words = content.split()
        if len(words) < 10:
            return False
        
        return True
    
    def _final_cleanup(self, chunks: List[Dict]) -> List[Dict]:
        """Final cleanup and renumbering of chunks"""
        
        # Renumber chunks sequentially
        for i, chunk in enumerate(chunks):
            chunk["chunk_number"] = i + 1
            
            # Update chunk_id to ensure uniqueness
            base_id = chunk.get("chunk_id", "").split("_chunk_")[0]
            chunk["chunk_id"] = f"{base_id}_chunk_{i+1:02d}"
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        words = len(text.split())
        return int(words / 0.75)  # Rough estimation
    
    def calculate_optimal_chunk_size(self, section_type: str, content_length: int) -> int:
        """Calculate optimal chunk size based on section characteristics"""
        
        base_size = self.config["target_chunk_size"]
        
        # Adjust based on section type
        if section_type in ["introduction", "assumptions", "exclusions"]:
            return min(base_size, content_length // 2)  # Prefer smaller chunks
        elif section_type in ["scope_of_work", "technical_requirements"]:
            return min(int(base_size * 1.2), self.config["max_chunk_size"])  # Allow larger chunks
        elif section_type == "pricing":
            return min(base_size, content_length)  # Preserve table structure
        else:
            return base_size
    
    def get_optimization_statistics(self, original_chunks: List[Dict], optimized_chunks: List[Dict]) -> Dict:
        """Generate statistics about the optimization process"""
        
        original_count = len(original_chunks)
        optimized_count = len(optimized_chunks)
        
        # Size statistics
        original_sizes = [chunk.get("token_count", 0) for chunk in original_chunks]
        optimized_sizes = [chunk.get("token_count", 0) for chunk in optimized_chunks]
        
        stats = {
            "chunk_count_change": optimized_count - original_count,
            "size_statistics": {
                "original": {
                    "avg": sum(original_sizes) / len(original_sizes) if original_sizes else 0,
                    "min": min(original_sizes) if original_sizes else 0,
                    "max": max(original_sizes) if original_sizes else 0
                },
                "optimized": {
                    "avg": sum(optimized_sizes) / len(optimized_sizes) if optimized_sizes else 0,
                    "min": min(optimized_sizes) if optimized_sizes else 0,
                    "max": max(optimized_sizes) if optimized_sizes else 0
                }
            },
            "quality_improvements": {
                "merged_small_chunks": max(0, original_count - optimized_count),
                "split_large_chunks": max(0, optimized_count - original_count),
                "boundary_optimizations": optimized_count
            }
        }
        
        return stats