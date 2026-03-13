"""
TriptokForge Compression Utilities
Compress/decompress data for Oracle CLOB storage and zip file generation
"""

import gzip
import base64
import json
import io
import zipfile
from typing import Dict, Any, Union


def compress_json(data: Dict[str, Any]) -> str:
    """
    Compress JSON data using gzip, return base64-encoded string.
    Reduces Oracle CLOB storage size by ~70-90%.
    
    Args:
        data: Dictionary to compress
        
    Returns:
        Base64-encoded gzip compressed string
    """
    json_str = json.dumps(data, separators=(',', ':'))  # Compact JSON
    compressed = gzip.compress(json_str.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')


def decompress_json(compressed_str: str) -> Dict[str, Any]:
    """
    Decompress base64-encoded gzip JSON data.
    
    Args:
        compressed_str: Base64-encoded gzip string
        
    Returns:
        Original dictionary
    """
    compressed = base64.b64decode(compressed_str.encode('ascii'))
    json_str = gzip.decompress(compressed).decode('utf-8')
    return json.loads(json_str)


def compress_text(text: str) -> str:
    """
    Compress plain text using gzip, return base64-encoded string.
    
    Args:
        text: Plain text string
        
    Returns:
        Base64-encoded gzip compressed string
    """
    compressed = gzip.compress(text.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')


def decompress_text(compressed_str: str) -> str:
    """
    Decompress base64-encoded gzip text.
    
    Args:
        compressed_str: Base64-encoded gzip string
        
    Returns:
        Original text string
    """
    compressed = base64.b64decode(compressed_str.encode('ascii'))
    return gzip.decompress(compressed).decode('utf-8')


def create_verse_package_zip(verse_files: Dict[str, str], island_seed: int) -> bytes:
    """
    Create a zip file containing all Verse package files.
    
    Args:
        verse_files: Dictionary of {filename: content}
        island_seed: Island seed number for naming
        
    Returns:
        Zip file as bytes
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in verse_files.items():
            # Add each file to the zip
            zip_file.writestr(f"island_{island_seed}_verse/{filename}", content)
    
    zip_buffer.seek(0)
    return zip_buffer.read()


def compress_verse_package(verse_files: Dict[str, str]) -> str:
    """
    Compress entire Verse package for Oracle storage.
    
    Args:
        verse_files: Dictionary of {filename: content}
        
    Returns:
        Base64-encoded gzip compressed JSON
    """
    return compress_json(verse_files)


def decompress_verse_package(compressed_str: str) -> Dict[str, str]:
    """
    Decompress Verse package from Oracle storage.
    
    Args:
        compressed_str: Base64-encoded gzip JSON
        
    Returns:
        Dictionary of {filename: content}
    """
    return decompress_json(compressed_str)


def estimate_compression_ratio(original_data: Union[str, Dict]) -> Dict[str, Any]:
    """
    Calculate compression statistics for debugging/optimization.
    
    Args:
        original_data: String or dictionary to test
        
    Returns:
        Dictionary with size stats
    """
    if isinstance(original_data, dict):
        original_str = json.dumps(original_data, separators=(',', ':'))
        compressed = compress_json(original_data)
    else:
        original_str = original_data
        compressed = compress_text(original_data)
    
    original_size = len(original_str.encode('utf-8'))
    compressed_size = len(compressed.encode('ascii'))
    ratio = (1 - compressed_size / original_size) * 100
    
    return {
        'original_bytes': original_size,
        'compressed_bytes': compressed_size,
        'compression_ratio': f"{ratio:.1f}%",
        'savings_kb': (original_size - compressed_size) / 1024
    }
