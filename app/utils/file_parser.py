"""
JSON File Parser Utilities
Provides streaming JSON parsing for memory-efficient processing of large files
"""

import json
import ijson
from typing import Iterator, List, Dict, Any, Tuple
from io import BytesIO
from fastapi import UploadFile


class FileParser:
    """
    Handles JSON file parsing with streaming support
    """
    
    @staticmethod
    async def detect_json_structure(file: UploadFile) -> str:
        """
        Detect if JSON file contains a single object or array of objects
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            "single_object" or "array_of_objects"
        """
        # Read first few bytes to detect structure
        content = await file.read(1024)
        await file.seek(0)  # Reset file pointer
        
        # Decode and strip whitespace
        text = content.decode('utf-8').strip()
        
        if text.startswith('['):
            return "array_of_objects"
        elif text.startswith('{'):
            return "single_object"
        else:
            raise ValueError("Invalid JSON structure: must start with '[' or '{'")
    
    @staticmethod
    async def stream_parse_json(file: UploadFile) -> Iterator[Dict[str, Any]]:
        """
        Stream parse JSON file to yield objects one at a time
        Memory efficient for large files
        
        Args:
            file: FastAPI UploadFile object
            
        Yields:
            Dictionary objects from the JSON file
        """
        # Read file content
        content = await file.read()
        
        # Create BytesIO object for ijson
        file_obj = BytesIO(content)
        
        try:
            # Detect structure
            await file.seek(0)
            structure = await FileParser.detect_json_structure(file)
            await file.seek(0)
            
            if structure == "array_of_objects":
                # Parse array of objects
                parser = ijson.items(file_obj, 'item')
                for obj in parser:
                    if isinstance(obj, dict):
                        yield obj
            else:
                # Parse single object
                content_str = content.decode('utf-8')
                obj = json.loads(content_str)
                if isinstance(obj, dict):
                    yield obj
                    
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing JSON: {str(e)}")
    
    @staticmethod
    async def parse_json_to_list(file: UploadFile) -> List[Dict[str, Any]]:
        """
        Parse entire JSON file into a list of objects
        Use for smaller files or when all data is needed at once
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            List of dictionary objects
        """
        objects = []
        async for obj in FileParser.stream_parse_json(file):
            objects.append(obj)
        return objects
    
    @staticmethod
    async def parse_in_chunks(
        file: UploadFile,
        chunk_size: int = 1000
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Parse JSON file in chunks for batch processing
        
        Args:
            file: FastAPI UploadFile object
            chunk_size: Number of objects per chunk
            
        Yields:
            Lists of dictionary objects (chunks)
        """
        chunk = []
        async for obj in FileParser.stream_parse_json(file):
            chunk.append(obj)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        # Yield remaining objects
        if chunk:
            yield chunk
    
    @staticmethod
    async def count_objects(file: UploadFile) -> int:
        """
        Count total number of objects in JSON file
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Total count of objects
        """
        count = 0
        async for _ in FileParser.stream_parse_json(file):
            count += 1
        
        # Reset file pointer
        await file.seek(0)
        return count
    
    @staticmethod
    def validate_json_content(content: bytes) -> Tuple[bool, str]:
        """
        Validate if content is valid JSON
        
        Args:
            content: Raw bytes content
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            json.loads(content.decode('utf-8'))
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, f"Error validating JSON: {str(e)}"
    
    @staticmethod
    async def parse_multiple_files(
        files: List[UploadFile]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse multiple JSON files
        
        Args:
            files: List of FastAPI UploadFile objects
            
        Returns:
            Dictionary mapping filename to list of objects
        """
        results = {}
        for file in files:
            objects = await FileParser.parse_json_to_list(file)
            results[file.filename] = objects
            # Reset file pointer for potential reuse
            await file.seek(0)
        
        return results
    
    @staticmethod
    def extract_sample(objects: List[Dict[str, Any]], sample_size: int = 100) -> List[Dict[str, Any]]:
        """
        Extract a random sample from objects for analysis
        
        Args:
            objects: List of dictionary objects
            sample_size: Number of objects to sample
            
        Returns:
            Sampled list of objects
        """
        import random
        
        if len(objects) <= sample_size:
            return objects
        
        return random.sample(objects, sample_size)
