"""
WSGI entry point for Gunicorn
Exposes the Flask app for Gunicorn to use
"""

from src.web_dashboard.dashboard_app import app

# This file is used by Gunicorn to serve the application
# Command: gunicorn wsgi:app
