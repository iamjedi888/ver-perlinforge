"""
TriptokForge - Verse Package Download Routes
Add these routes to your forge blueprint (forge.py)
"""

from flask import jsonify, send_file, request
import io
from compression_utils import create_verse_package_zip, decompress_verse_package

# Add this to your forge blueprint


@forge_bp.route('/api/forge/download-verse', methods=['POST'])
def download_verse_package():
    """
    Download a Verse package as a zip file.
    
    Request JSON:
        {
            "verse_package": {...},  # Dictionary of filename: content
            "island_seed": 12345
        }
    
    Returns:
        Zip file download
    """
    try:
        data = request.get_json()
        verse_package = data.get('verse_package')
        island_seed = data.get('island_seed', 0)
        
        if not verse_package:
            return jsonify({'error': 'No verse_package provided'}), 400
        
        # Create zip file
        zip_bytes = create_verse_package_zip(verse_package, island_seed)
        
        # Send as downloadable file
        return send_file(
            io.BytesIO(zip_bytes),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'island_{island_seed}_verse_package.zip'
        )
        
    except Exception as e:
        print(f"[verse_download] Error: {e}")
        return jsonify({'error': str(e)}), 500


@forge_bp.route('/api/forge/get-saved-verse/<int:save_id>', methods=['GET'])
def get_saved_verse_package(save_id):
    """
    Retrieve a previously saved Verse package from Oracle.
    
    Args:
        save_id: Island save ID from Oracle
        
    Returns:
        JSON with verse_package data or zip download
    """
    try:
        # Query Oracle for the save
        import oracle_db
        
        query = """
            SELECT verse_data, seed, display_name 
            FROM island_saves 
            WHERE id = :save_id
        """
        
        result = oracle_db.execute_query(query, {'save_id': save_id})
        
        if not result:
            return jsonify({'error': 'Save not found'}), 404
        
        row = result[0]
        compressed_verse = row[0]  # verse_data column
        seed = row[1]
        display_name = row[2]
        
        if not compressed_verse:
            return jsonify({'error': 'No Verse data saved for this island'}), 404
        
        # Decompress the verse package
        verse_package = decompress_verse_package(compressed_verse)
        
        # Check if user wants JSON or zip
        download_zip = request.args.get('zip', 'false').lower() == 'true'
        
        if download_zip:
            # Return as zip file
            zip_bytes = create_verse_package_zip(verse_package, seed)
            filename = f"{display_name or f'island_{seed}'}_verse_package.zip"
            
            return send_file(
                io.BytesIO(zip_bytes),
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )
        else:
            # Return as JSON
            return jsonify({
                'verse_package': verse_package,
                'seed': seed,
                'display_name': display_name
            })
        
    except Exception as e:
        print(f"[get_saved_verse] Error: {e}")
        return jsonify({'error': str(e)}), 500
