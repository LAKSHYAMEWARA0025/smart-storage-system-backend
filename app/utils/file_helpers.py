import os

# Define your file type categories
FILE_TYPE_MAP = {
    # Images
    '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.bmp': 'image', '.svg': 'image', '.webp': 'image',
    # Videos
    '.mp4': 'video', '.avi': 'video', '.mov': 'video', '.mkv': 'video', '.webm': 'video',
    # Audio
    '.mp3': 'audio', '.wav': 'audio', '.ogg': 'audio', '.m4a': 'audio',
    # Documents
    '.txt': 'text', '.pdf': 'document', '.doc': 'document', '.docx': 'document', '.xls': 'document', '.xlsx': 'document', '.ppt': 'document', '.pptx': 'document',
    # Code/Text
    '.json': 'text', '.csv': 'text', '.html': 'text', '.css': 'text', '.js': 'text', '.py': 'text',
}

def get_file_details(filename: str):
    """
    Extracts the file extension and determines the general file type.
    """
    # Get the file extension (e.g., '.png')
    name, extension = os.path.splitext(filename)
    extension = extension.lower()
    
    # Determine the file type from our map, default to 'other'
    file_type = FILE_TYPE_MAP.get(extension, 'other')
    
    return {
        "extension": extension,
        "file_type": file_type
    }