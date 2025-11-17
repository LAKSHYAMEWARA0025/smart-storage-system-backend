"""
Media Metadata Extraction Utilities
Extracts metadata from images, videos, and other media files
"""

import hashlib
from typing import Dict, Any, Optional
from io import BytesIO
from PIL import Image
import ffmpeg


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA-256 hash of file content for deduplication
    
    Args:
        file_content: File bytes
        
    Returns:
        Hex string of SHA-256 hash
    """
    return hashlib.sha256(file_content).hexdigest()


def extract_image_metadata(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract metadata from image files
    
    Args:
        file_content: Image file bytes
        filename: Original filename
        
    Returns:
        Dictionary with image metadata
    """
    metadata = {}
    
    try:
        image = Image.open(BytesIO(file_content))
        
        metadata['dimensions'] = {
            'width': image.width,
            'height': image.height,
            'aspect_ratio': round(image.width / image.height, 2) if image.height > 0 else None
        }
        
        metadata['format'] = image.format
        metadata['mode'] = image.mode  # RGB, RGBA, L, etc.
        
        # Extract EXIF data if available
        if hasattr(image, '_getexif') and image._getexif():
            exif_data = image._getexif()
            if exif_data:
                metadata['exif'] = {
                    'orientation': exif_data.get(274),  # Orientation tag
                    'datetime': exif_data.get(306),     # DateTime tag
                    'make': exif_data.get(271),         # Camera make
                    'model': exif_data.get(272),        # Camera model
                }
        
        print(f"✅ Extracted image metadata: {metadata['dimensions']}")
        
    except Exception as e:
        print(f"⚠️ Could not extract image metadata: {e}")
        metadata['error'] = str(e)
    
    return metadata


def extract_video_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from video files using ffmpeg
    
    Args:
        file_path: Path to video file (temporary)
        
    Returns:
        Dictionary with video metadata
    """
    metadata = {}
    
    try:
        probe = ffmpeg.probe(file_path)
        
        # Get video stream info
        video_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
            None
        )
        
        if video_stream:
            metadata['duration'] = float(probe['format'].get('duration', 0))
            metadata['dimensions'] = {
                'width': video_stream.get('width'),
                'height': video_stream.get('height'),
                'aspect_ratio': video_stream.get('display_aspect_ratio')
            }
            metadata['codec'] = video_stream.get('codec_name')
            metadata['frame_rate'] = eval(video_stream.get('r_frame_rate', '0/1'))
            metadata['bitrate'] = int(probe['format'].get('bit_rate', 0))
        
        # Get audio stream info
        audio_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
            None
        )
        
        if audio_stream:
            metadata['audio'] = {
                'codec': audio_stream.get('codec_name'),
                'sample_rate': audio_stream.get('sample_rate'),
                'channels': audio_stream.get('channels')
            }
        
        print(f"✅ Extracted video metadata: duration={metadata.get('duration')}s")
        
    except Exception as e:
        print(f"⚠️ Could not extract video metadata: {e}")
        metadata['error'] = str(e)
    
    return metadata


def get_file_category(extension: str) -> str:
    """
    Categorize file by extension
    
    Args:
        extension: File extension (e.g., '.jpg')
        
    Returns:
        Category name
    """
    extension = extension.lower()
    
    categories = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico', '.tiff'],
        'videos': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
        'spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
        'presentations': ['.ppt', '.pptx', '.odp'],
        'audio': ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.json', '.xml'],
    }
    
    for category, extensions in categories.items():
        if extension in extensions:
            return category
    
    return 'other'


def build_enhanced_metadata(
    file_content: bytes,
    filename: str,
    extension: str,
    tags: Optional[list] = None,
    description: Optional[str] = None,
    temp_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build complete metadata object for a file
    
    Args:
        file_content: File bytes
        filename: Original filename
        extension: File extension
        tags: Optional list of tags
        description: Optional description
        temp_file_path: Temporary file path (for video processing)
        
    Returns:
        Complete metadata dictionary
    """
    metadata = {
        'original_filename': filename,
        'file_hash': calculate_file_hash(file_content),
        'file_size': len(file_content),
        'category': get_file_category(extension),
        'tags': tags or [],
        'description': description or ''
    }
    
    # Extract type-specific metadata
    category = metadata['category']
    
    if category == 'images':
        image_meta = extract_image_metadata(file_content, filename)
        metadata.update(image_meta)
    
    elif category == 'videos' and temp_file_path:
        video_meta = extract_video_metadata(temp_file_path)
        metadata.update(video_meta)
    
    return metadata
