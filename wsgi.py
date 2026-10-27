"""Entry point for Gunicorn (production) and `flask run` (development)."""

from app import create_app

app = create_app()
