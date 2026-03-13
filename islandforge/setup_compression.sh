#!/bin/bash
# setup_compression.sh — Install compression dependencies on the VM

echo "Installing compression dependencies..."

# Update package list
sudo apt update -y

# Install ffmpeg for audio compression
echo "Installing ffmpeg..."
sudo apt install -y ffmpeg

# Install additional image optimization tools
echo "Installing image optimization tools..."
sudo apt install -y jpegoptim optipng pngquant

# Verify installations
echo ""
echo "Verifying installations:"
ffmpeg -version 2>/dev/null && echo "✅ ffmpeg installed" || echo "❌ ffmpeg failed"
jpegoptim --version 2>/dev/null && echo "✅ jpegoptim installed" || echo "❌ jpegoptim failed"
optipng -v 2>/dev/null | head -1 && echo "✅ optipng installed" || echo "❌ optipng failed"
pngquant --version 2>/dev/null && echo "✅ pngquant installed" || echo "❌ pngquant failed"

echo ""
echo "Compression setup complete!"
echo "Audio files will be compressed to 128k MP3"
echo "Images will be compressed to WebP/optimized PNG"
