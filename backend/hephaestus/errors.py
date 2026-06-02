from __future__ import annotations


class HephaestusError(RuntimeError):
    """Base error for Hephaestus orchestration services."""


class NotFoundError(HephaestusError):
    pass


class InvalidTransitionError(HephaestusError):
    pass


class ConflictError(HephaestusError):
    pass


class ExecutionFailureError(HephaestusError):
    pass
