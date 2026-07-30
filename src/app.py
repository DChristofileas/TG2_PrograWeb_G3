"""Vercel entrypoint that reexports the existing FastAPI application."""

from planificahoy.main import app

__all__ = ["app"]
