"""Shared exceptions for GVIM materials services."""

from __future__ import annotations


class FormulaError(ValueError):
    """Raised when a material formula cannot be parsed or balanced."""


class MaterialsDependencyError(RuntimeError):
    """Raised when a required materials-science dependency is unavailable."""
