"""Local conftest for wastage tests.

These tests do not use the FastAPI test client and must not import the
top-level tests/conftest.py (which loads FastAPI and causes a pydantic-core
version conflict on some developer machines).
"""
