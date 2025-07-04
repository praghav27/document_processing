import re
import json
from typing import List
from config import MAX_CHUNK_SIZE, CHUNK_OVERLAP

def semantic_chunking(text: str, max_chunk_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Create semantic text chunks with overlap"""
    if not text or len(text.strip()) == 0:
        return []
    
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return []
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If paragraph is too long, split by sentences
        if len(paragraph) > max_chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if adding this sentence would exceed the limit
                test_chunk = current_chunk + " " + sentence if current_chunk else sentence
                
                if len(test_chunk) > max_chunk_size and current_chunk:
                    # Save current chunk and start new one
                    chunks.append(current_chunk.strip())
                    # Add overlap from previous chunk
                    if overlap > 0 and len(current_chunk) > overlap:
                        current_chunk = current_chunk[-overlap:] + " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    current_chunk = test_chunk
        else:
            # Check if adding this paragraph would exceed the limit
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(test_chunk) > max_chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk.strip())
                # Add overlap from previous chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk = test_chunk
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Filter out very small chunks (less than 50 characters)
    chunks = [chunk for chunk in chunks if len(chunk.strip()) >= 50]
    
    return chunks

def load_text_chunks(json_path: str) -> List[str]:
    """Load text chunks from JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [chunk["content"] for chunk in data.get("chunks", [])]
    except Exception as e:
        print(f"Error loading text chunks: {e}")
        return []

def save_text_to_file(text: str, filepath: str) -> bool:
    """Save text content to file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"Error saving text to file: {e}")
        return False

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive newlines but preserve paragraph breaks
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Clean up quotes and dashes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('–', '-').replace('—', '-')
    
    return text.strip()