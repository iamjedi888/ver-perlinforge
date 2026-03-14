"""
TriptokForge VR Spectator Arena
A-Frame WebXR stadium for watching esports
"""
from flask import Blueprint, render_template

arena_bp = Blueprint('arena', __name__)

@arena_bp.route('/arena')
def arena_page():
    """VR spectator arena"""
    return render_template('arena.html')
