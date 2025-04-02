"""
Main entry point for web dashboard module
Allows running the web dashboard as a module
"""

from .dashboard_app import app, run

if __name__ == "__main__":
    run()
