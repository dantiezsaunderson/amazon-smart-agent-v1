"""
Web dashboard module initialization file
Makes web dashboard components available for import
"""

from .dashboard_app import app, run

__all__ = [
    'app',
    'run'
]
