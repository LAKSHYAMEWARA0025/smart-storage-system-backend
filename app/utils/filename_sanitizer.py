"""
Filename sanitization utilities for safe storage
"""

import re
import unicodedata
from pathlib import Path


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for safe storage in Supabase Storage
    
    Args:
        filename: Original filename
        max_length: Maximum filename length (default 200)
        
    Returns:
        Sanitized filename safe for storage
        
    Examples:
        "My File (2024).pdf" -> "My_File_2024.pdf"
        "Español ñ.txt" -> "Espanol_n.txt"
        "コンドル.mp4" -> "kondoru.mp4"
    """
    # Get file extension
    path = Path(filename)
    name = path.stem
    extension = path.suffix
    
    # Normalize unicode characters (convert accented chars to ASCII equivalents)
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters with underscores
    # Keep only alphanumeric, hyphens, and underscores
    name = re.sub(r'[^\w\-]', '_', name)
    
    # Replace multiple underscores with single underscore
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # If name is empty after sanitization, use a default
    if not name:
        name = "file"
    
    # Truncate if too long (leave room for extension)
    max_name_length = max_length - len(extension)
    if len(name) > max_name_length:
        name = name[:max_name_length]
    
    # Reconstruct filename
    sanitized = f"{name}{extension}"
    
    return sanitized


def generate_unique_filename(original_filename: str, file_hash: str = None) -> str:
    """
    Generate a unique filename using hash or timestamp
    
    Args:
        original_filename: Original filename
        file_hash: Optional file hash for uniqueness
        
    Returns:
        Unique sanitized filename
    """
    import time
    
    # Sanitize the original filename
    sanitized = sanitize_filename(original_filename)
    
    # Get parts
    path = Path(sanitized)
    name = path.stem
    extension = path.suffix
    
    # Add uniqueness
    if file_hash:
        # Use first 8 chars of hash
        unique_id = file_hash[:8]
    else:
        # Use timestamp
        unique_id = str(int(time.time() * 1000))[-8:]
    
    # Combine
    unique_filename = f"{name}_{unique_id}{extension}"
    
    return unique_filename
