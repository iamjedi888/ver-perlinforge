"""
wsgi.py — gunicorn entry point for TriptokForge
Usage: gunicorn -w 2 -b 0.0.0.0:5000 wsgi:application
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app as application

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=False)
