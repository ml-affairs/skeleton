"""Shared test helper utilities for trace-role fixture scenarios."""

from app.service import Service


def build_service(name: str) -> Service:
    """Build the service used by a scenario."""
    return Service(name)
