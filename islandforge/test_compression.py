#!/usr/bin/env python3
"""
Test script for TriptokForge compression utilities
Run this to verify compression is working correctly
"""

import sys
import json
from compression_utils import (
    compress_json,
    decompress_json,
    compress_text,
    decompress_text,
    compress_verse_package,
    decompress_verse_package,
    create_verse_package_zip,
    estimate_compression_ratio
)


def test_json_compression():
    """Test JSON compression/decompression"""
    print("=" * 60)
    print("TEST 1: JSON Compression")
    print("=" * 60)
    
    # Sample data similar to island config
    test_data = {
        "seed": 12345,
        "size": 505,
        "theme": "chapter2",
        "plots": [
            {"index": i, "x": i * 10, "z": i * 15, "biome": "forest"}
            for i in range(100)
        ],
        "heightmap": [[0.1 * i] * 10 for i in range(10)]
    }
    
    # Compress
    compressed = compress_json(test_data)
    
    # Decompress
    decompressed = decompress_json(compressed)
    
    # Verify
    assert test_data == decompressed, "Decompression failed!"
    
    # Stats
    stats = estimate_compression_ratio(test_data)
    
    print(f"✓ JSON compression/decompression works!")
    print(f"  Original size: {stats['original_bytes']:,} bytes")
    print(f"  Compressed size: {stats['compressed_bytes']:,} bytes")
    print(f"  Compression ratio: {stats['compression_ratio']}")
    print(f"  Savings: {stats['savings_kb']:.2f} KB")
    print()


def test_text_compression():
    """Test plain text compression"""
    print("=" * 60)
    print("TEST 2: Text Compression")
    print("=" * 60)
    
    # Sample Verse code
    verse_code = """
using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

foliage_spawner_device := class(creative_device):
    
    @editable
    SpawnRadius<public>:float = 5000.0
    
    @editable
    DensityMultiplier<public>:float = 1.0
    
    OnBegin<override>()<suspends>:void =
        Print("Foliage spawner initialized")
        SpawnVegetation()
    """ * 10  # Repeat to make it bigger
    
    # Compress
    compressed = compress_text(verse_code)
    
    # Decompress
    decompressed = decompress_text(compressed)
    
    # Verify
    assert verse_code == decompressed, "Text decompression failed!"
    
    # Stats
    stats = estimate_compression_ratio(verse_code)
    
    print(f"✓ Text compression/decompression works!")
    print(f"  Original size: {stats['original_bytes']:,} bytes")
    print(f"  Compressed size: {stats['compressed_bytes']:,} bytes")
    print(f"  Compression ratio: {stats['compression_ratio']}")
    print(f"  Savings: {stats['savings_kb']:.2f} KB")
    print()


def test_verse_package_compression():
    """Test complete Verse package compression"""
    print("=" * 60)
    print("TEST 3: Verse Package Compression")
    print("=" * 60)
    
    # Sample Verse package
    verse_package = {
        "plot_registry.verse": "using { /Fortnite.com/Devices }\n" * 100,
        "biome_manifest.verse": "using { /Verse.org/Simulation }\n" * 100,
        "foliage_spawner.verse": "class foliage_spawner_device\n" * 50,
        "poi_placer.verse": "class poi_placer_device\n" * 50,
        "landscape_config.json": json.dumps({"materials": ["grass"] * 20}),
        "asset_manifest.json": json.dumps({"assets": ["tree"] * 30}),
        "README.md": "# Island Deploy Guide\n" + "Step 1\n" * 50
    }
    
    # Compress
    compressed = compress_verse_package(verse_package)
    
    # Decompress
    decompressed = decompress_verse_package(compressed)
    
    # Verify
    assert verse_package == decompressed, "Verse package decompression failed!"
    
    # Stats
    total_original = sum(len(content) for content in verse_package.values())
    compressed_size = len(compressed)
    ratio = (1 - compressed_size / total_original) * 100
    
    print(f"✓ Verse package compression works!")
    print(f"  Files: {len(verse_package)}")
    print(f"  Original total: {total_original:,} bytes")
    print(f"  Compressed size: {compressed_size:,} bytes")
    print(f"  Compression ratio: {ratio:.1f}%")
    print(f"  Savings: {(total_original - compressed_size) / 1024:.2f} KB")
    print()


def test_zip_creation():
    """Test zip file creation"""
    print("=" * 60)
    print("TEST 4: Zip File Creation")
    print("=" * 60)
    
    verse_package = {
        "plot_registry.verse": "Plot data here",
        "biome_manifest.verse": "Biome data here",
        "README.md": "# Deploy Guide"
    }
    
    # Create zip
    zip_bytes = create_verse_package_zip(verse_package, island_seed=999)
    
    print(f"✓ Zip creation works!")
    print(f"  Files: {len(verse_package)}")
    print(f"  Zip size: {len(zip_bytes):,} bytes")
    print(f"  Would download as: island_999_verse_package.zip")
    print()


def main():
    """Run all tests"""
    print("\n🚀 TriptokForge Compression Test Suite\n")
    
    try:
        test_json_compression()
        test_text_compression()
        test_verse_package_compression()
        test_zip_creation()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nCompression system is working correctly.")
        print("Ready to integrate into TriptokForge.\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
