"""
IntelliDesk AI — WSGI Entry Point
Production entry point for Gunicorn.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
