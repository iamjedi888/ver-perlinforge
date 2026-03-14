"""
TriptokForge - Complete Forge Routes
Drop this into: islandforge/routes/forge_routes.py
Then in server.py: from routes.forge_routes import forge_downloads_bp
                    app.register_blueprint(forge_downloads_bp)
"""

from flask import Blueprint, request, jsonify, send_file
import io
from compression_utils import (
    compress_verse_package,
    decompress_verse_package, 
    create_verse_package_zip
)

forge_downloads_bp = Blueprint('forge_downloads', __name__)


@forge_downloads_bp.route('/api/forge/download-verse', methods=['POST'])
def download_verse_package():
    """Download Verse package as zip file"""
    try:
        data = request.get_json()
        verse_package = data.get('verse_package')
        island_seed = data.get('island_seed', 0)
        
        if not verse_package:
            return jsonify({'error': 'No verse_package provided'}), 400
        
        zip_bytes = create_verse_package_zip(verse_package, island_seed)
        
        return send_file(
            io.BytesIO(zip_bytes),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'island_{island_seed}_verse_package.zip'
        )
        
    except Exception as e:
        print(f"[verse_download] Error: {e}")
        return jsonify({'error': str(e)}), 500


@forge_downloads_bp.route('/api/forge/get-saved-verse/<int:save_id>', methods=['GET'])
def get_saved_verse_package(save_id):
    """Retrieve saved Verse package from Oracle"""
    try:
        import oracle_db
        
        result = oracle_db.execute_query(
            "SELECT verse_data, seed, display_name FROM island_saves WHERE id = :save_id",
            {'save_id': save_id}
        )
        
        if not result:
            return jsonify({'error': 'Save not found'}), 404
        
        compressed_verse, seed, display_name = result[0]
        
        if not compressed_verse:
            return jsonify({'error': 'No Verse data'}), 404
        
        verse_package = decompress_verse_package(compressed_verse)
        
        # Return as zip or JSON based on ?zip=true param
        if request.args.get('zip', 'false').lower() == 'true':
            zip_bytes = create_verse_package_zip(verse_package, seed)
            filename = f"{display_name or f'island_{seed}'}_verse.zip"
            
            return send_file(
                io.BytesIO(zip_bytes),
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )
        
        return jsonify({
            'verse_package': verse_package,
            'seed': seed,
            'display_name': display_name
        })
        
    except Exception as e:
        print(f"[get_saved_verse] Error: {e}")
        return jsonify({'error': str(e)}), 500
