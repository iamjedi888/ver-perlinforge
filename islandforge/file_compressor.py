"""
file_compressor.py — Universal file compression for TriptokForge
Auto-compresses images, audio, and other assets before saving to disk/OCI.
Keeps the platform lean and fast.
"""
import os
import subprocess
import tempfile
from PIL import Image, ImageOps
import shutil

def compress_image(input_path, output_path=None, max_size=(1024, 1024), quality=75, format_hint=None):
    """
    Compress any image to WebP or optimized format.
    
    Args:
        input_path: Source image file
        output_path: Target file (auto-generated if None)  
        max_size: Max dimensions (width, height)
        quality: WebP quality 1-100
        format_hint: Force format ('webp', 'png', 'jpeg') or auto-detect
    
    Returns:
        (output_path, original_size_kb, compressed_size_kb)
    """
    if not os.path.exists(input_path):
        return None, 0, 0
        
    original_size = os.path.getsize(input_path) / 1024  # KB
    
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compressed.webp"
    
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if needed (for WebP compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                if format_hint == 'jpeg':
                    # JPEG doesn't support transparency - add white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif format_hint in ('webp', None):
                    # Keep transparency for WebP
                    pass
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            # Auto-detect format if not specified
            if format_hint is None:
                if original_size < 50:  # Small files stay as PNG
                    format_hint = 'png'
                    quality = 90
                else:
                    format_hint = 'webp'
            
            # Save compressed
            save_kwargs = {}
            if format_hint == 'webp':
                save_kwargs = {'format': 'WebP', 'quality': quality, 'optimize': True}
                if not output_path.endswith('.webp'):
                    output_path = os.path.splitext(output_path)[0] + '.webp'
            elif format_hint == 'png':
                save_kwargs = {'format': 'PNG', 'optimize': True}
                if not output_path.endswith('.png'):
                    output_path = os.path.splitext(output_path)[0] + '.png'
            elif format_hint == 'jpeg':
                save_kwargs = {'format': 'JPEG', 'quality': quality, 'optimize': True}
                if not output_path.endswith(('.jpg', '.jpeg')):
                    output_path = os.path.splitext(output_path)[0] + '.jpg'
            
            img.save(output_path, **save_kwargs)
            
    except Exception as e:
        print(f"[compress_image] Error: {e}")
        # Fallback: copy original
        shutil.copy2(input_path, output_path)
    
    compressed_size = os.path.getsize(output_path) / 1024 if os.path.exists(output_path) else 0
    return output_path, original_size, compressed_size

def compress_audio(input_path, output_path=None, bitrate='128k', format_hint=None):
    """
    Compress audio using ffmpeg.
    
    Args:
        input_path: Source audio file
        output_path: Target file (auto-generated if None)
        bitrate: Audio bitrate ('128k', '96k', '64k')
        format_hint: Force format ('mp3', 'ogg', 'aac') or auto-detect
    
    Returns:
        (output_path, original_size_kb, compressed_size_kb)
    """
    if not os.path.exists(input_path):
        return None, 0, 0
        
    original_size = os.path.getsize(input_path) / 1024  # KB
    
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compressed.mp3"
    
    # Auto-detect format
    if format_hint is None:
        format_hint = 'mp3'  # Most compatible
    
    # Ensure correct extension
    format_exts = {'mp3': '.mp3', 'ogg': '.ogg', 'aac': '.aac', 'm4a': '.m4a'}
    if format_hint in format_exts:
        correct_ext = format_exts[format_hint]
        if not output_path.endswith(correct_ext):
            output_path = os.path.splitext(output_path)[0] + correct_ext
    
    try:
        # FFmpeg compression command
        cmd = [
            'ffmpeg', '-y',  # Overwrite output
            '-i', input_path,
            '-b:a', bitrate,
            '-movflags', '+faststart',  # Web optimization
        ]
        
        # Format-specific options
        if format_hint == 'mp3':
            cmd.extend(['-codec:a', 'libmp3lame'])
        elif format_hint == 'ogg':
            cmd.extend(['-codec:a', 'libvorbis'])
        elif format_hint == 'aac':
            cmd.extend(['-codec:a', 'aac'])
        
        cmd.append(output_path)
        
        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"[compress_audio] ffmpeg error: {result.stderr}")
            # Fallback: copy original
            shutil.copy2(input_path, output_path)
            
    except FileNotFoundError:
        print(f"[compress_audio] ffmpeg not found, copying original")
        shutil.copy2(input_path, output_path)
    except subprocess.TimeoutExpired:
        print(f"[compress_audio] ffmpeg timeout, copying original")
        shutil.copy2(input_path, output_path)
    except Exception as e:
        print(f"[compress_audio] Error: {e}")
        shutil.copy2(input_path, output_path)
    
    compressed_size = os.path.getsize(output_path) / 1024 if os.path.exists(output_path) else 0
    return output_path, original_size, compressed_size

def compress_island_outputs(preview_path, heightmap_path, layout_path=None):
    """
    Compress Island Forge outputs specifically.
    
    Args:
        preview_path: Island preview PNG
        heightmap_path: Heightmap PNG  
        layout_path: Layout JSON (optional)
    
    Returns:
        dict with compressed paths and savings
    """
    results = {}
    
    # Compress preview to WebP (high quality for display)
    if preview_path and os.path.exists(preview_path):
        out_path, orig_kb, comp_kb = compress_image(
            preview_path, 
            max_size=(512, 512), 
            quality=85, 
            format_hint='webp'
        )
        results['preview'] = {
            'path': out_path,
            'original_kb': orig_kb,
            'compressed_kb': comp_kb,
            'savings_pct': round((orig_kb - comp_kb) / orig_kb * 100, 1) if orig_kb > 0 else 0
        }
    
    # Compress heightmap to PNG (lossless for UEFN compatibility)
    if heightmap_path and os.path.exists(heightmap_path):
        out_path, orig_kb, comp_kb = compress_image(
            heightmap_path,
            max_size=(512, 512),
            quality=90,
            format_hint='png'
        )
        results['heightmap'] = {
            'path': out_path,
            'original_kb': orig_kb,
            'compressed_kb': comp_kb,
            'savings_pct': round((orig_kb - comp_kb) / orig_kb * 100, 1) if orig_kb > 0 else 0
        }
    
    # Layout JSON (optional compression)
    if layout_path and os.path.exists(layout_path):
        # JSON is already small, just copy
        results['layout'] = {
            'path': layout_path,
            'original_kb': os.path.getsize(layout_path) / 1024,
            'compressed_kb': os.path.getsize(layout_path) / 1024,
            'savings_pct': 0
        }
    
    return results

def auto_compress_file(file_path, aggressive=False):
    """
    Auto-detect file type and compress appropriately.
    
    Args:
        file_path: Path to any file
        aggressive: Use higher compression (smaller files, lower quality)
    
    Returns:
        (compressed_path, original_kb, compressed_kb, savings_pct)
    """
    if not os.path.exists(file_path):
        return None, 0, 0, 0
    
    _, ext = os.path.splitext(file_path.lower())
    
    # Image files
    if ext in {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff'}:
        quality = 65 if aggressive else 75
        max_size = (800, 800) if aggressive else (1024, 1024)
        out_path, orig_kb, comp_kb = compress_image(file_path, quality=quality, max_size=max_size)
        savings_pct = round((orig_kb - comp_kb) / orig_kb * 100, 1) if orig_kb > 0 else 0
        return out_path, orig_kb, comp_kb, savings_pct
    
    # Audio files
    elif ext in {'.wav', '.flac', '.aiff', '.mp3', '.ogg', '.aac', '.m4a'}:
        bitrate = '96k' if aggressive else '128k'
        out_path, orig_kb, comp_kb = compress_audio(file_path, bitrate=bitrate)
        savings_pct = round((orig_kb - comp_kb) / orig_kb * 100, 1) if orig_kb > 0 else 0
        return out_path, orig_kb, comp_kb, savings_pct
    
    # Other files (no compression)
    else:
        size_kb = os.path.getsize(file_path) / 1024
        return file_path, size_kb, size_kb, 0

def cleanup_temp_files(*file_paths):
    """Remove temporary files safely."""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

# ── Quick integration functions for server.py ──

def compress_uploaded_audio(audio_path):
    """Compress uploaded audio and return new path."""
    if not audio_path or not os.path.exists(audio_path):
        return audio_path
    
    compressed_path, orig_kb, comp_kb = compress_audio(audio_path, bitrate='128k')
    
    if compressed_path != audio_path and os.path.exists(compressed_path):
        # Replace original with compressed
        shutil.move(compressed_path, audio_path)
        print(f"[compress] Audio: {orig_kb:.1f}KB → {comp_kb:.1f}KB ({(orig_kb-comp_kb)/orig_kb*100:.1f}% saved)")
    
    return audio_path

def compress_island_preview(preview_path):
    """Compress island preview and return new path.""" 
    if not preview_path or not os.path.exists(preview_path):
        return preview_path
        
    compressed_path, orig_kb, comp_kb = compress_image(
        preview_path, 
        max_size=(512, 512), 
        quality=85, 
        format_hint='webp'
    )
    
    if compressed_path != preview_path and os.path.exists(compressed_path):
        # Replace original with compressed
        shutil.move(compressed_path, preview_path)
        print(f"[compress] Preview: {orig_kb:.1f}KB → {comp_kb:.1f}KB ({(orig_kb-comp_kb)/orig_kb*100:.1f}% saved)")
    
    return preview_path
