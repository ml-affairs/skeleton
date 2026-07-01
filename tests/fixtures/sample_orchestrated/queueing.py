"""Queue-stage helpers for the orchestrated workflow fixture."""

from __future__ import annotations


def stage_one(plan: list[str]) -> str:
    """Stage one marker."""
    return plan[0].split(":", maxsplit=1)[-1]


def stage_two(plan: list[str]) -> str:
    """Stage two marker."""
    return plan[1].split(":", maxsplit=1)[-1]


def stage_three(plan: list[str]) -> str:
    """Stage three marker."""
    return plan[2].split(":", maxsplit=1)[-1]
